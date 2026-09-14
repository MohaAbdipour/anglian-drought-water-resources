"""Create comparative scientific figures from the checked drought outputs."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from analyse_droughts import load_observations


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "docs" / "figures"
Q90 = 0.274
FOCUS_STARTS = ["1976-06-08", "1991-06-29", "1996-05-31", "2011-09-02", "2022-07-14"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def moving_mean(values: list[float | None], window: int) -> list[float | None]:
    """Centred moving mean; return no value where less than 70% is observed."""
    radius = window // 2
    result: list[float | None] = []
    for index in range(len(values)):
        subset = values[max(0, index - radius) : min(len(values), index + radius + 1)]
        accepted = [value for value in subset if value is not None]
        required = max(1, int(0.7 * len(subset)))
        result.append(sum(accepted) / len(accepted) if len(accepted) >= required else None)
    return result


def make_state_space(rows: list[dict[str, str]], path: Path) -> None:
    available = [row for row in rows if row["groundwater_seasonal_percentile"]]
    rainfall = [float(row["rainfall_180d_seasonal_percentile"]) for row in available]
    groundwater = [float(row["groundwater_seasonal_percentile"]) for row in available]
    durations = [float(row["duration_days"]) for row in available]
    deficits = [float(row["deficit_volume_m3"]) / 1_000_000 for row in available]
    sizes = [25 + 190 * (value / max(deficits)) ** 0.5 for value in deficits]

    fig, axis = plt.subplots(figsize=(9.4, 7.2))
    axis.axvspan(0, 20, color="#3f88c5", alpha=0.09)
    axis.axhspan(0, 20, color="#a23b72", alpha=0.08)
    scatter = axis.scatter(
        rainfall,
        groundwater,
        s=sizes,
        c=durations,
        cmap="viridis",
        alpha=0.78,
        edgecolor="white",
        linewidth=0.7,
    )
    axis.axvline(20, color="#3f88c5", linestyle="--", linewidth=1)
    axis.axhline(20, color="#a23b72", linestyle="--", linewidth=1)

    ranked = sorted(available, key=lambda row: float(row["deficit_volume_m3"]), reverse=True)[:8]
    offsets = [(7, 7), (7, -15), (7, 7), (7, -15), (7, 7), (7, -15), (7, 7), (7, 7)]
    for row, offset in zip(ranked, offsets):
        axis.annotate(
            row["start_date"],
            (
                float(row["rainfall_180d_seasonal_percentile"]),
                float(row["groundwater_seasonal_percentile"]),
            ),
            xytext=offset,
            textcoords="offset points",
            fontsize=8.5,
        )

    colourbar = fig.colorbar(scatter, ax=axis, pad=0.02)
    colourbar.set_label("Event duration (days)")
    for volume, label in [(0.05, "0.05"), (0.25, "0.25"), (1.0, "1.00")]:
        size = 25 + 190 * (volume / max(deficits)) ** 0.5
        axis.scatter([], [], s=size, facecolor="#777777", alpha=0.55, edgecolor="white", label=label)
    axis.legend(title="Deficit volume (Mm³)", loc="upper right", frameon=True)
    axis.set(
        xlim=(-2, 102),
        ylim=(-2, 102),
        xlabel="Antecedent 180-day rainfall seasonal percentile",
        ylabel="Nearby Chalk groundwater seasonal percentile",
        title="Hydroclimatic state at the onset of Q90 low-flow events",
    )
    axis.grid(alpha=0.22)
    axis.text(2, 98, "Dry regional rainfall", color="#2f6f9f", va="top", fontsize=9)
    axis.text(98, 3, "Low groundwater", color="#81305a", ha="right", va="bottom", fontsize=9)
    fig.text(
        0.5,
        0.015,
        f"{len(available)} uncensored events with an accepted groundwater reading within ±45 days. "
        "Percentiles use the 1991–2020 seasonal reference.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def make_event_hydrographs(events: list[dict[str, str]], path: Path) -> None:
    event_by_start = {row["start_date"]: row for row in events}
    observations = load_observations()
    flow_by_day = {
        observation.day: observation.flow if observation.accepted else None
        for observation in observations
    }

    fig, axes = plt.subplots(len(FOCUS_STARTS), 1, figsize=(12.2, 11.2), sharex=False)
    for axis, start_text in zip(axes, FOCUS_STARTS):
        event = event_by_start[start_text]
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(event["end_date"])
        view_start = start - timedelta(days=150)
        view_end = end + timedelta(days=75)
        days = []
        day = view_start
        while day <= view_end:
            days.append(day)
            day += timedelta(days=1)
        flows = [flow_by_day.get(day) for day in days]
        smoothed = moving_mean(flows, 15)

        axis.plot(days, flows, color="#9fb8c8", linewidth=0.7, alpha=0.65)
        axis.plot(days, smoothed, color="#174a6e", linewidth=1.8)
        axis.axhline(Q90, color="#b33c2e", linestyle="--", linewidth=1.2)
        axis.axvspan(start, end, color="#d98742", alpha=0.18)
        axis.set_ylim(bottom=0)
        axis.grid(axis="y", alpha=0.22)
        axis.set_ylabel("Flow\n(m³/s)")
        axis.set_title(
            f"{start.year}: {event['duration_days']} days below Q90; "
            f"deficit {float(event['deficit_volume_m3']) / 1_000_000:.3f} Mm³",
            loc="left",
            fontsize=10.5,
        )

    axes[-1].set_xlabel("Date")
    legend = [
        Line2D([0], [0], color="#9fb8c8", lw=1, label="Accepted daily mean flow"),
        Line2D([0], [0], color="#174a6e", lw=2, label="15-day moving mean"),
        Line2D([0], [0], color="#b33c2e", lw=1.2, ls="--", label="Q90 = 0.274 m³/s"),
        Line2D([0], [0], color="#d98742", lw=7, alpha=0.35, label="Identified event"),
    ]
    fig.legend(handles=legend, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 0.965), frameon=False)
    fig.suptitle("Flow evolution around five material low-flow episodes", fontsize=14, fontweight="bold", y=0.995)
    fig.text(
        0.5,
        0.012,
        "Panels use event-specific date windows. Missing or rejected daily values are not interpolated.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.945), h_pad=1.1)
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    context = read_csv(OUTPUTS / "q90_event_hydroclimate_context.csv")
    events = read_csv(OUTPUTS / "q90_drought_events.csv")
    FIGURES.mkdir(parents=True, exist_ok=True)
    make_state_space(context, FIGURES / "hydroclimate_state_space.png")
    make_event_hydrographs(events, FIGURES / "major_event_hydrographs.png")
    print("Created hydroclimatic state-space and major-event hydrograph figures.")


if __name__ == "__main__":
    main()
