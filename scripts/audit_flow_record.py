"""Audit temporal coverage and quality flags in the downloaded daily-flow record."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "fakenham_readings.json"
OUTPUT_DIR = ROOT / "outputs"


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def water_year(day: date) -> int:
    """Return the ending year for a UK October-to-September water year."""
    return day.year + 1 if day.month >= 10 else day.year


def expected_bounds(period_type: str, year: int) -> tuple[date, date]:
    if period_type == "calendar_year":
        return date(year, 1, 1), date(year, 12, 31)
    return date(year - 1, 10, 1), date(year, 9, 30)


def longest_missing_run(observed_dates: set[date], start: date, end: date) -> int:
    longest = current = 0
    for day in date_range(start, end):
        if day in observed_dates:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def summarise_periods(records: list[dict], period_type: str) -> list[dict]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        day = record["parsed_date"]
        key = day.year if period_type == "calendar_year" else water_year(day)
        grouped[key].append(record)

    rows = []
    for year in range(min(grouped), max(grouped) + 1):
        start, end = expected_bounds(period_type, year)
        period_records = grouped.get(year, [])
        observed_dates = {record["parsed_date"] for record in period_records}
        expected_days = (end - start).days + 1
        numeric = [record for record in period_records if isinstance(record.get("value"), (int, float))]
        accepted = [
            record
            for record in numeric
            if record.get("completeness") == "Complete"
            and record.get("quality") in {"Good", "Estimated"}
        ]
        good_only = [
            record
            for record in numeric
            if record.get("completeness") == "Complete" and record.get("quality") == "Good"
        ]
        rows.append(
            {
                "period_type": period_type,
                "year": year,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "expected_days": expected_days,
                "observed_rows": len(period_records),
                "numeric_days": len(numeric),
                "accepted_days": len(accepted),
                "good_only_days": len(good_only),
                "missing_dates": expected_days - len(observed_dates),
                "longest_missing_run_days": longest_missing_run(observed_dates, start, end),
                "numeric_coverage_pct": round(100 * len(numeric) / expected_days, 3),
                "accepted_coverage_pct": round(100 * len(accepted) / expected_days, 3),
                "good_only_coverage_pct": round(100 * len(good_only) / expected_days, 3),
                "boundary_period": start < records[0]["parsed_date"] or end > records[-1]["parsed_date"],
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError("Run scripts/download_ea_flow.py before auditing the record")
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    records = payload.get("items", [])
    if not records:
        raise RuntimeError("No readings were found in the downloaded response")

    parsed = []
    for record in records:
        item = dict(record)
        item["parsed_date"] = date.fromisoformat(record["date"])
        parsed.append(item)
    parsed.sort(key=lambda item: item["parsed_date"])

    date_counts = Counter(record["parsed_date"] for record in parsed)
    duplicate_dates = sorted(day.isoformat() for day, count in date_counts.items() if count > 1)
    values = [record["value"] for record in parsed if isinstance(record.get("value"), (int, float))]
    observed_dates = set(date_counts)
    record_start = parsed[0]["parsed_date"]
    record_end = parsed[-1]["parsed_date"]
    expected_span_days = (record_end - record_start).days + 1

    reference_start = date(1991, 1, 1)
    reference_end = date(2020, 12, 31)
    reference = [
        record
        for record in parsed
        if reference_start <= record["parsed_date"] <= reference_end
    ]
    reference_expected = (reference_end - reference_start).days + 1
    reference_accepted = [
        record
        for record in reference
        if isinstance(record.get("value"), (int, float))
        and record.get("completeness") == "Complete"
        and record.get("quality") in {"Good", "Estimated"}
    ]
    reference_good_only = [
        record
        for record in reference
        if isinstance(record.get("value"), (int, float))
        and record.get("completeness") == "Complete"
        and record.get("quality") == "Good"
    ]

    summary = {
        "station": "River Wensum at Fakenham",
        "nrfa_station_id": "34011",
        "series": "Environment Agency qualified daily mean flow",
        "unit": "m3/s",
        "record_start": record_start.isoformat(),
        "record_end": record_end.isoformat(),
        "rows": len(parsed),
        "unique_dates": len(observed_dates),
        "duplicate_dates": duplicate_dates,
        "missing_dates_within_observed_span": expected_span_days - len(observed_dates),
        "longest_missing_run_within_observed_span_days": longest_missing_run(
            observed_dates, record_start, record_end
        ),
        "numeric_rows": len(values),
        "minimum_numeric_flow_m3s": min(values),
        "maximum_numeric_flow_m3s": max(values),
        "quality_counts": dict(sorted(Counter(record.get("quality", "Not supplied") for record in parsed).items())),
        "completeness_counts": dict(
            sorted(Counter(record.get("completeness", "Not supplied") for record in parsed).items())
        ),
        "reference_period_1991_2020": {
            "expected_days": reference_expected,
            "observed_rows": len(reference),
            "numeric_days": sum(
                isinstance(record.get("value"), (int, float)) for record in reference
            ),
            "accepted_days": len(reference_accepted),
            "accepted_coverage_pct": round(100 * len(reference_accepted) / reference_expected, 3),
            "good_only_days": len(reference_good_only),
            "good_only_coverage_pct": round(
                100 * len(reference_good_only) / reference_expected, 3
            ),
        },
        "interpretation_note": (
            "Coverage and API quality flags are screened here; hydrometric suitability and "
            "artificial influences require separate interpretation."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "flow_record_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(
        OUTPUT_DIR / "calendar_year_completeness.csv",
        summarise_periods(parsed, "calendar_year"),
    )
    write_csv(
        OUTPUT_DIR / "water_year_completeness.csv",
        summarise_periods(parsed, "water_year"),
    )

    if duplicate_dates:
        raise RuntimeError(f"Duplicate dates require review: {duplicate_dates[:5]}")
    print(
        f"Audited {len(parsed):,} rows from {record_start} to {record_end}; "
        f"1991–2020 accepted coverage is "
        f"{summary['reference_period_1991_2020']['accepted_coverage_pct']:.3f}%."
    )


if __name__ == "__main__":
    main()
