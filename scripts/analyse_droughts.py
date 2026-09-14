"""Calculate threshold-based low-flow drought statistics and figures."""

from __future__ import annotations

import csv
import calendar
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "fakenham_readings.json"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = ROOT / "docs" / "figures"
REFERENCE_START = date(1991, 1, 1)
REFERENCE_END = date(2020, 12, 31)
ANALYSIS_END = date(2023, 12, 31)
SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class Observation:
    day: date
    flow: float | None
    accepted: bool
    good_only: bool
    quality: str
    completeness: str


def percentile(values: list[float], probability: float) -> float:
    """Return a linearly interpolated sample percentile (Hyndman-Fan type 7)."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile from an empty sample")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def load_observations() -> list[Observation]:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    observations = []
    for row in payload.get("items", []):
        day = date.fromisoformat(row["date"])
        if day > ANALYSIS_END:
            continue
        value = row.get("value")
        flow = float(value) if isinstance(value, (int, float)) else None
        complete = row.get("completeness") == "Complete"
        quality = row.get("quality", "Not supplied")
        observations.append(
            Observation(
                day=day,
                flow=flow,
                accepted=flow is not None and complete and quality in {"Good", "Estimated"},
                good_only=flow is not None and complete and quality == "Good",
                quality=quality,
                completeness=row.get("completeness", "Not supplied"),
            )
        )
    observations.sort(key=lambda item: item.day)
    return observations


def thresholds(observations: list[Observation], screen: str) -> dict[str, float]:
    values = [
        item.flow
        for item in observations
        if REFERENCE_START <= item.day <= REFERENCE_END
        and getattr(item, screen)
        and item.flow is not None
    ]
    return {
        "Q80": percentile(values, 0.20),
        "Q90": percentile(values, 0.10),
        "Q95": percentile(values, 0.05),
    }


def identify_events(
    observations: list[Observation], threshold: float, screen: str
) -> list[dict]:
    by_day = {item.day: item for item in observations}
    below = [
        item
        for item in observations
        if getattr(item, screen) and item.flow is not None and item.flow < threshold
    ]
    events: list[list[Observation]] = []
    current: list[Observation] = []
    for item in below:
        if current and item.day != current[-1].day + timedelta(days=1):
            events.append(current)
            current = []
        current.append(item)
    if current:
        events.append(current)

    result = []
    first_day, last_day = observations[0].day, observations[-1].day
    for number, event in enumerate(events, start=1):
        start, end = event[0].day, event[-1].day
        previous = by_day.get(start - timedelta(days=1))
        following = by_day.get(end + timedelta(days=1))
        left_censored = start == first_day or previous is None or not getattr(previous, screen)
        right_censored = end == last_day or following is None or not getattr(following, screen)
        deficits = [(threshold - item.flow) * SECONDS_PER_DAY for item in event]
        result.append(
            {
                "event_id": number,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "duration_days": len(event),
                "minimum_flow_m3s": min(item.flow for item in event),
                "deficit_volume_m3": sum(deficits),
                "mean_daily_deficit_m3s": sum(threshold - item.flow for item in event) / len(event),
                "left_censored": left_censored,
                "right_censored": right_censored,
            }
        )
    return result


def pool_events(events: list[dict], observations: list[Observation], screen: str) -> list[dict]:
    """Merge events separated by no more than five valid, above-threshold days."""
    if not events:
        return []
    by_day = {item.day: item for item in observations}
    pooled = [dict(events[0])]
    for event in events[1:]:
        previous = pooled[-1]
        previous_end = date.fromisoformat(previous["end_date"])
        next_start = date.fromisoformat(event["start_date"])
        gap_days = list(days_between(previous_end, next_start))
        mergeable = len(gap_days) <= 5 and all(
            day in by_day and getattr(by_day[day], screen) for day in gap_days
        )
        if not mergeable:
            pooled.append(dict(event))
            continue
        previous["end_date"] = event["end_date"]
        previous["duration_days"] = (next_start - date.fromisoformat(previous["start_date"])).days + int(
            event["duration_days"]
        )
        previous["minimum_flow_m3s"] = min(
            float(previous["minimum_flow_m3s"]), float(event["minimum_flow_m3s"])
        )
        previous["deficit_volume_m3"] = float(previous["deficit_volume_m3"]) + float(
            event["deficit_volume_m3"]
        )
        previous["right_censored"] = event["right_censored"]
        previous["mean_daily_deficit_m3s"] = (
            float(previous["deficit_volume_m3"])
            / (float(previous["duration_days"]) * SECONDS_PER_DAY)
        )
    for number, event in enumerate(pooled, start=1):
        event["event_id"] = number
    return pooled


def days_between(end: date, start: date):
    current = end + timedelta(days=1)
    while current < start:
        yield current
        current += timedelta(days=1)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def event_summary(events: list[dict]) -> dict:
    uncensored = [
        event for event in events if not event["left_censored"] and not event["right_censored"]
    ]
    return {
        "event_count": len(events),
        "uncensored_event_count": len(uncensored),
        "maximum_uncensored_duration_days": max(
            (int(event["duration_days"]) for event in uncensored), default=0
        ),
        "maximum_uncensored_deficit_m3": max(
            (float(event["deficit_volume_m3"]) for event in uncensored), default=0.0
        ),
        "total_uncensored_deficit_m3": sum(
            float(event["deficit_volume_m3"]) for event in uncensored
        ),
    }


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 160,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
        }
    )


def plot_flow_duration(reference: list[float], limits: dict[str, float]) -> None:
    ordered = sorted(reference, reverse=True)
    exceedance = [100 * (rank + 1) / (len(ordered) + 1) for rank in range(len(ordered))]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(exceedance, ordered, color="#155e75", linewidth=1.5)
    colours = {"Q80": "#ca8a04", "Q90": "#ea580c", "Q95": "#b91c1c"}
    for name in ("Q80", "Q90", "Q95"):
        probability = int(name[1:])
        value = limits[name]
        ax.scatter([probability], [value], color=colours[name], s=35, zorder=3)
        ax.annotate(
            f"{name} = {value:.3f} m³/s",
            (probability, value),
            xytext=(-5, 10 if name != "Q90" else -16),
            textcoords="offset points",
            ha="right",
            color=colours[name],
        )
    ax.set_yscale("log")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Percentage of days flow is equalled or exceeded")
    ax.set_ylabel("Daily mean flow (m³/s, logarithmic scale)")
    ax.set_title("Flow-duration curve at Fakenham, 1991–2020")
    ax.grid(True, which="both", color="#d1d5db", linewidth=0.6, alpha=0.7)
    fig.text(0.01, 0.01, "Environment Agency qualified daily mean flow; Good and Estimated values.", fontsize=8)
    fig.savefig(FIGURE_DIR / "flow_duration_curve.png")
    plt.close(fig)


def annual_low_flow_metrics(
    observations: list[Observation], threshold: float, screen: str
) -> list[dict]:
    annual = defaultdict(lambda: {"days": 0, "deficit": 0.0})
    accepted_counts = defaultdict(int)
    for item in observations:
        if item.day.year < 1967:
            continue
        if getattr(item, screen):
            accepted_counts[item.day.year] += 1
        if not getattr(item, screen) or item.flow is None:
            continue
        if item.flow < threshold:
            annual[item.day.year]["days"] += 1
            annual[item.day.year]["deficit"] += (threshold - item.flow) * SECONDS_PER_DAY
    years = list(range(1967, ANALYSIS_END.year + 1))
    return [
        {
            "year": year,
            "expected_days": 366 if calendar.isleap(year) else 365,
            "accepted_days": accepted_counts[year],
            "accepted_coverage_pct": round(
                100 * accepted_counts[year] / (366 if calendar.isleap(year) else 365), 3
            ),
            "days_below_q90": annual[year]["days"],
            "deficit_volume_m3": annual[year]["deficit"],
        }
        for year in years
    ]


def plot_annual_deficits(rows: list[dict]) -> None:
    years = [int(row["year"]) for row in rows]
    deficits = [float(row["deficit_volume_m3"]) / 1_000_000 for row in rows]
    low_days = [int(row["days_below_q90"]) for row in rows]

    fig, ax1 = plt.subplots(figsize=(10.5, 5.4))
    for row in rows:
        year = int(row["year"])
        if float(row["accepted_coverage_pct"]) < 95:
            ax1.axvspan(year - 0.5, year + 0.5, color="#9ca3af", alpha=0.16, zorder=0)
    ax1.bar(years, deficits, color="#0f766e", width=0.85, alpha=0.85, zorder=2)
    ax1.set_xlabel("Calendar year")
    ax1.set_ylabel("Cumulative Q90 deficit (million m³)", color="#0f766e")
    ax1.tick_params(axis="y", labelcolor="#0f766e")
    ax1.grid(axis="y", color="#d1d5db", linewidth=0.6, alpha=0.7)
    ax2 = ax1.twinx()
    ax2.plot(years, low_days, color="#9a3412", linewidth=1.2, marker="o", markersize=2.5)
    ax2.set_ylabel("Days below Q90", color="#9a3412")
    ax2.tick_params(axis="y", labelcolor="#9a3412")
    ax2.spines["top"].set_visible(False)
    ax1.set_title("Annual low-flow exposure and accumulated deficit")
    ax1.legend(
        handles=[Patch(facecolor="#9ca3af", alpha=0.25, label="<95% accepted daily coverage")],
        loc="upper right",
        frameon=False,
        fontsize=8,
    )
    fig.text(
        0.01,
        0.01,
        "Fixed 1991–2020 Q90 threshold; Good and Estimated complete observations; shaded years require caution.",
        fontsize=8,
    )
    fig.savefig(FIGURE_DIR / "annual_q90_deficit.png")
    plt.close(fig)


def plot_event_severity(events: list[dict]) -> None:
    usable = [
        event for event in events if not event["left_censored"] and not event["right_censored"]
    ]
    years = [date.fromisoformat(event["start_date"]).year for event in usable]
    durations = [event["duration_days"] for event in usable]
    deficits = [event["deficit_volume_m3"] / 1_000_000 for event in usable]
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    scatter = ax.scatter(
        durations,
        deficits,
        c=years,
        cmap="viridis",
        s=35,
        alpha=0.78,
        edgecolors="white",
        linewidths=0.35,
    )
    ax.set_xlabel("Event duration (days)")
    ax.set_ylabel("Accumulated flow deficit (million m³)")
    ax.set_title("Duration and severity of Q90 low-flow events")
    ax.grid(True, color="#d1d5db", linewidth=0.6, alpha=0.7)
    colourbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    colourbar.set_label("Event start year")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    fig.text(
        0.01,
        0.01,
        "Consecutive below-threshold days; censored events excluded; no inter-event pooling.",
        fontsize=8,
    )
    fig.savefig(FIGURE_DIR / "q90_event_severity_duration.png")
    plt.close(fig)


def main() -> None:
    observations = load_observations()
    accepted_thresholds = thresholds(observations, "accepted")
    good_thresholds = thresholds(observations, "good_only")
    if not accepted_thresholds["Q80"] > accepted_thresholds["Q90"] > accepted_thresholds["Q95"]:
        raise RuntimeError("Flow-duration thresholds are not in the expected order")

    threshold_rows = []
    summary_rows = []
    q90_events: list[dict] = []
    for screen, limits in (("accepted", accepted_thresholds), ("good_only", good_thresholds)):
        for name, value in limits.items():
            threshold_rows.append(
                {
                    "quality_screen": screen,
                    "reference_period": "1991-01-01/2020-12-31",
                    "threshold": name,
                    "flow_m3s": round(value, 6),
                }
            )
            events = identify_events(observations, value, screen)
            pooled = pool_events(events, observations, screen)
            if screen == "accepted" and name == "Q90":
                q90_events = events
            for pooling, selected in (("none", events), ("merge_gaps_up_to_5_days", pooled)):
                summary_rows.append(
                    {
                        "quality_screen": screen,
                        "threshold": name,
                        "pooling": pooling,
                        **event_summary(selected),
                    }
                )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "flow_thresholds.csv", threshold_rows)
    write_csv(OUTPUT_DIR / "drought_event_sensitivity.csv", summary_rows)
    write_csv(OUTPUT_DIR / "q90_drought_events.csv", q90_events)
    annual_rows = annual_low_flow_metrics(
        observations, accepted_thresholds["Q90"], "accepted"
    )
    write_csv(OUTPUT_DIR / "annual_q90_metrics.csv", annual_rows)

    reference_values = [
        item.flow
        for item in observations
        if REFERENCE_START <= item.day <= REFERENCE_END and item.accepted and item.flow is not None
    ]
    set_plot_style()
    plot_flow_duration(reference_values, accepted_thresholds)
    plot_annual_deficits(annual_rows)
    plot_event_severity(q90_events)

    q90_summary = event_summary(q90_events)
    print(
        f"Q90 = {accepted_thresholds['Q90']:.3f} m3/s; "
        f"identified {q90_summary['uncensored_event_count']} uncensored events "
        f"through {ANALYSIS_END}."
    )


if __name__ == "__main__":
    main()
