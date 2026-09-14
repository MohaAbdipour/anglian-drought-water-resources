"""Relate Q90 river-flow droughts to antecedent rainfall and groundwater state."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "docs" / "figures"
REFERENCE_START = 1991
REFERENCE_END = 2020
ANALYSIS_END = date(2023, 12, 31)
ACCEPTED_QUALITIES = {"Good", "Estimated"}


def percentile_rank(value: float, reference: list[float]) -> float:
    """Return a mid-rank percentile from 0 to 100."""
    if not reference:
        raise ValueError("A percentile requires at least one reference value")
    lower = sum(item < value for item in reference)
    equal = sum(item == value for item in reference)
    return 100.0 * (lower + 0.5 * equal) / len(reference)


def parse_hadseep(path: Path) -> dict[date, float]:
    rainfall: dict[date, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[0][:4].isdigit():
            continue
        day = date.fromisoformat(parts[0])
        if day <= ANALYSIS_END:
            rainfall[day] = float(parts[1])
    return rainfall


def antecedent_total(rainfall: dict[date, float], anchor: date, days: int) -> float:
    """Sum the complete window immediately before an anchor date."""
    window = [anchor - timedelta(days=offset) for offset in range(1, days + 1)]
    missing = [day for day in window if day not in rainfall]
    if missing:
        raise ValueError(f"Rainfall window contains {len(missing)} missing day(s)")
    return sum(rainfall[day] for day in window)


def reference_anchor(year: int, month: int, day: int) -> date:
    """Map an event calendar date into a reference year, including 29 February."""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, 2, 28)


def seasonal_rainfall_percentile(
    rainfall: dict[date, float], anchor: date, days: int
) -> tuple[float, float, int]:
    observed = antecedent_total(rainfall, anchor, days)
    reference = [
        antecedent_total(rainfall, reference_anchor(year, anchor.month, anchor.day), days)
        for year in range(REFERENCE_START, REFERENCE_END + 1)
    ]
    return observed, percentile_rank(observed, reference), len(reference)


def load_groundwater(path: Path) -> list[dict[str, object]]:
    items = json.loads(path.read_text(encoding="utf-8"))["items"]
    accepted = []
    for item in items:
        day = date.fromisoformat(item["date"])
        if (
            item.get("quality") in ACCEPTED_QUALITIES
            and item.get("value") is not None
            and day <= ANALYSIS_END
        ):
            accepted.append(
                {"date": day, "value": float(item["value"]), "quality": item["quality"]}
            )
    return sorted(accepted, key=lambda item: item["date"])


def nearest_groundwater(
    readings: list[dict[str, object]], anchor: date, maximum_offset_days: int = 45
) -> dict[str, object] | None:
    if not readings:
        return None
    nearest = min(readings, key=lambda item: abs((item["date"] - anchor).days))
    offset = (nearest["date"] - anchor).days
    if abs(offset) > maximum_offset_days:
        return None
    return {**nearest, "offset_days": offset}


def groundwater_month_percentile(
    value: float, month: int, readings: list[dict[str, object]]
) -> tuple[float, int]:
    reference = [
        float(item["value"])
        for item in readings
        if REFERENCE_START <= item["date"].year <= REFERENCE_END
        and item["date"].month == month
    ]
    if len(reference) < 10:
        raise ValueError(f"Only {len(reference)} reference groundwater readings for month {month}")
    return percentile_rank(value, reference), len(reference)


def load_events(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row["left_censored"] == "False" and row["right_censored"] == "False"]


def analyse_events(
    events: list[dict[str, str]],
    rainfall: dict[date, float],
    groundwater: list[dict[str, object]],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for event in events:
        start = date.fromisoformat(event["start_date"])
        rain180, rain180_pct, rain180_n = seasonal_rainfall_percentile(rainfall, start, 180)
        rain365, rain365_pct, rain365_n = seasonal_rainfall_percentile(rainfall, start, 365)
        nearest = nearest_groundwater(groundwater, start)
        result: dict[str, object] = {
            "event_id": int(event["event_id"]),
            "start_date": event["start_date"],
            "end_date": event["end_date"],
            "duration_days": int(event["duration_days"]),
            "deficit_volume_m3": float(event["deficit_volume_m3"]),
            "rainfall_180d_mm": rain180,
            "rainfall_180d_seasonal_percentile": rain180_pct,
            "rainfall_180d_reference_n": rain180_n,
            "rainfall_365d_mm": rain365,
            "rainfall_365d_seasonal_percentile": rain365_pct,
            "rainfall_365d_reference_n": rain365_n,
            "groundwater_date": "",
            "groundwater_offset_days": "",
            "groundwater_level_mAOD": "",
            "groundwater_quality": "",
            "groundwater_seasonal_percentile": "",
            "groundwater_reference_n": "",
        }
        if nearest is not None:
            gw_pct, gw_n = groundwater_month_percentile(
                float(nearest["value"]), nearest["date"].month, groundwater
            )
            result.update(
                {
                    "groundwater_date": nearest["date"].isoformat(),
                    "groundwater_offset_days": nearest["offset_days"],
                    "groundwater_level_mAOD": nearest["value"],
                    "groundwater_quality": nearest["quality"],
                    "groundwater_seasonal_percentile": gw_pct,
                    "groundwater_reference_n": gw_n,
                }
            )
        results.append(result)
    return results


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(rows: list[dict[str, object]], path: Path) -> None:
    selected = sorted(rows, key=lambda row: float(row["deficit_volume_m3"]), reverse=True)[:12]
    selected.reverse()
    labels = [f"{row['start_date'][:4]}  ({row['duration_days']} d)" for row in selected]
    positions = list(range(len(selected)))

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 7.2), sharey=True, gridspec_kw={"width_ratios": [1.2, 1, 1]})
    deficits = [float(row["deficit_volume_m3"]) / 1_000_000 for row in selected]
    axes[0].barh(positions, deficits, color="#28666e", alpha=0.9)
    axes[0].set_xlabel("Q90 deficit volume (Mm³)")
    axes[0].set_yticks(positions, labels)
    axes[0].grid(axis="x", alpha=0.25)

    rainfall_pct = [float(row["rainfall_180d_seasonal_percentile"]) for row in selected]
    axes[1].scatter(rainfall_pct, positions, s=55, color="#3274a1", edgecolor="white", linewidth=0.6, zorder=3)
    axes[1].set_xlabel("Antecedent 180-day rainfall\nseasonal percentile")

    gw_positions = []
    gw_pct = []
    for position, row in zip(positions, selected):
        if row["groundwater_seasonal_percentile"] != "":
            gw_positions.append(position)
            gw_pct.append(float(row["groundwater_seasonal_percentile"]))
    axes[2].scatter(gw_pct, gw_positions, s=55, color="#9c5b34", edgecolor="white", linewidth=0.6, zorder=3)
    axes[2].set_xlabel("Nearby Chalk groundwater\nseasonal percentile")

    for axis in axes[1:]:
        axis.axvspan(0, 20, color="#c44536", alpha=0.10)
        axis.axvline(20, color="#c44536", linestyle="--", linewidth=1)
        axis.set_xlim(0, 100)
        axis.set_xticks([0, 20, 40, 60, 80, 100])
        axis.grid(axis="x", alpha=0.25)
    fig.suptitle("Hydroclimatic setting of the twelve largest uncensored Q90 events", fontsize=14, fontweight="bold")
    fig.text(0.5, 0.015, "Percentiles use 1991–2020 seasonal reference conditions; lower values indicate drier or lower conditions.\nRainfall is the HadSEEP regional series, not catchment-average precipitation. Groundwater is not interpolated; blank values have no accepted reading within ±45 days.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.075, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def summarise(rows: list[dict[str, object]], groundwater: list[dict[str, object]]) -> dict[str, object]:
    rain_dry = [row for row in rows if float(row["rainfall_180d_seasonal_percentile"]) < 20]
    gw_available = [row for row in rows if row["groundwater_seasonal_percentile"] != ""]
    gw_low = [row for row in gw_available if float(row["groundwater_seasonal_percentile"]) < 20]
    top = sorted(rows, key=lambda row: float(row["deficit_volume_m3"]), reverse=True)[:12]
    gaps = [(later["date"] - earlier["date"]).days for earlier, later in zip(groundwater, groundwater[1:])]
    return {
        "analysis_end": ANALYSIS_END.isoformat(),
        "reference_period": f"{REFERENCE_START}-{REFERENCE_END}",
        "uncensored_q90_event_count": len(rows),
        "events_with_180d_rainfall_below_20th_percentile": len(rain_dry),
        "events_with_180d_rainfall_below_20th_percentile_percent": 100 * len(rain_dry) / len(rows),
        "events_with_groundwater_within_45_days": len(gw_available),
        "events_with_groundwater_within_45_days_percent": 100 * len(gw_available) / len(rows),
        "available_events_with_groundwater_below_20th_percentile": len(gw_low),
        "available_events_with_groundwater_below_20th_percentile_percent": 100 * len(gw_low) / len(gw_available),
        "groundwater_accepted_reading_count": len(groundwater),
        "groundwater_median_sampling_gap_days": sorted(gaps)[len(gaps) // 2],
        "largest_events": [
            {
                "start_date": row["start_date"],
                "duration_days": row["duration_days"],
                "deficit_volume_Mm3": float(row["deficit_volume_m3"]) / 1_000_000,
                "rainfall_180d_percentile": row["rainfall_180d_seasonal_percentile"],
                "groundwater_percentile": row["groundwater_seasonal_percentile"],
            }
            for row in top
        ],
        "interpretation_limits": [
            "HadSEEP is a South East England regional precipitation series, not catchment-average rainfall.",
            "Groundwater observations are irregular and are not interpolated; only readings within 45 days of event onset are used.",
            "One nearby Chalk borehole does not represent the full catchment groundwater system.",
            "Associations provide hydroclimatic context and do not establish climatic attribution or remove abstraction effects.",
        ],
    }


def main() -> None:
    rainfall = parse_hadseep(RAW / "hadseep_daily.txt")
    groundwater = load_groundwater(RAW / "great_ryburg_readings.json")
    events = load_events(OUTPUTS / "q90_drought_events.csv")
    rows = analyse_events(events, rainfall, groundwater)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUTS / "q90_event_hydroclimate_context.csv", rows)
    summary = summarise(rows, groundwater)
    (OUTPUTS / "hydroclimate_context_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    make_figure(rows, FIGURES / "hydroclimate_event_context.png")
    print(
        f"Context calculated for {len(rows)} uncensored Q90 events; "
        f"groundwater available for {summary['events_with_groundwater_within_45_days']}."
    )


if __name__ == "__main__":
    main()
