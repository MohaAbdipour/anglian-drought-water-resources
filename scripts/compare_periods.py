"""Compare low-flow metrics across equal periods with coverage screening."""

from __future__ import annotations

import csv
import math
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_droughts import (  # noqa: E402
    annual_low_flow_metrics,
    load_observations,
    thresholds,
)


OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = ROOT / "docs" / "figures"
COVERAGE_THRESHOLD = 95.0
PERIODS = {
    "1967–1985": (1967, 1985),
    "1986–2004": (1986, 2004),
    "2005–2023": (2005, 2023),
}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def block_bootstrap_means(
    values: list[float | None],
    *,
    seed: int,
    replicates: int = 10_000,
    block_length: int = 3,
) -> list[float]:
    """Bootstrap a mean using overlapping blocks while retaining missing-year positions."""
    if len(values) < block_length:
        raise ValueError("The period is shorter than the selected bootstrap block")
    blocks = [values[index : index + block_length] for index in range(len(values) - block_length + 1)]
    rng = random.Random(seed)
    means = []
    required_blocks = math.ceil(len(values) / block_length)
    for _ in range(replicates):
        sample = []
        for _ in range(required_blocks):
            sample.extend(rng.choice(blocks))
        usable = [value for value in sample[: len(values)] if value is not None]
        if usable:
            means.append(sum(usable) / len(usable))
    if not means:
        raise RuntimeError("No bootstrap replicate contained an eligible year")
    return means


def confidence_interval(values: list[float]) -> tuple[float, float]:
    return percentile(values, 0.025), percentile(values, 0.975)


def period_values(
    rows: list[dict], start: int, end: int, field: str
) -> list[float | None]:
    by_year = {int(row["year"]): row for row in rows}
    values = []
    for year in range(start, end + 1):
        row = by_year[year]
        eligible = float(row["accepted_coverage_pct"]) >= COVERAGE_THRESHOLD
        values.append(float(row[field]) if eligible else None)
    return values


def summarise_screen(screen: str, q90: float, annual_rows: list[dict]) -> tuple[list[dict], dict]:
    summaries = []
    bootstrap_distributions: dict[str, dict[str, list[float]]] = {}
    for period_index, (period, (start, end)) in enumerate(PERIODS.items()):
        selected = [row for row in annual_rows if start <= int(row["year"]) <= end]
        eligible = [
            row for row in selected if float(row["accepted_coverage_pct"]) >= COVERAGE_THRESHOLD
        ]
        excluded = [
            str(row["year"])
            for row in selected
            if float(row["accepted_coverage_pct"]) < COVERAGE_THRESHOLD
        ]
        day_values = period_values(selected, start, end, "days_below_q90")
        deficit_values = period_values(selected, start, end, "deficit_volume_m3")
        day_bootstrap = block_bootstrap_means(day_values, seed=2300 + period_index)
        deficit_bootstrap = block_bootstrap_means(deficit_values, seed=7300 + period_index)
        day_low, day_high = confidence_interval(day_bootstrap)
        deficit_low, deficit_high = confidence_interval(deficit_bootstrap)
        mean_days = sum(value for value in day_values if value is not None) / len(eligible)
        mean_deficit = sum(value for value in deficit_values if value is not None) / len(eligible)
        summaries.append(
            {
                "quality_screen": screen,
                "period": period,
                "q90_m3s": round(q90, 6),
                "years": len(selected),
                "eligible_years": len(eligible),
                "excluded_years": ";".join(excluded),
                "drought_years": sum(float(row["days_below_q90"]) > 0 for row in eligible),
                "mean_days_below_q90": round(mean_days, 6),
                "mean_days_ci_low": round(day_low, 6),
                "mean_days_ci_high": round(day_high, 6),
                "mean_deficit_m3": round(mean_deficit, 6),
                "mean_deficit_ci_low_m3": round(deficit_low, 6),
                "mean_deficit_ci_high_m3": round(deficit_high, 6),
            }
        )
        bootstrap_distributions[period] = {
            "days": day_bootstrap,
            "deficit": deficit_bootstrap,
        }
    return summaries, bootstrap_distributions


def contrast_row(screen: str, metric: str, early: list[float], late: list[float]) -> dict:
    differences = [late_value - early_value for early_value, late_value in zip(early, late)]
    low, high = confidence_interval(differences)
    return {
        "quality_screen": screen,
        "contrast": "2005–2023 minus 1967–1985",
        "metric": metric,
        "mean_difference": round(sum(differences) / len(differences), 6),
        "ci_low": round(low, 6),
        "ci_high": round(high, 6),
        "bootstrap_replicates": len(differences),
        "block_length_years": 3,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_periods(rows: list[dict]) -> None:
    accepted = [row for row in rows if row["quality_screen"] == "accepted"]
    labels = [row["period"] for row in accepted]
    colours = ["#64748b", "#0f766e", "#b45309"]
    x = list(range(len(labels)))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.9))
    settings = [
        (
            "mean_days_below_q90",
            "mean_days_ci_low",
            "mean_days_ci_high",
            "Mean days below Q90 per eligible year",
            "Low-flow exposure",
            1.0,
        ),
        (
            "mean_deficit_m3",
            "mean_deficit_ci_low_m3",
            "mean_deficit_ci_high_m3",
            "Mean annual deficit (million m³)",
            "Accumulated deficit",
            1_000_000.0,
        ),
    ]
    for ax, (value_field, low_field, high_field, ylabel, title, scale) in zip(axes, settings):
        values = [float(row[value_field]) / scale for row in accepted]
        lower = [value - float(row[low_field]) / scale for value, row in zip(values, accepted)]
        upper = [float(row[high_field]) / scale - value for value, row in zip(values, accepted)]
        ax.bar(x, values, color=colours, width=0.64, alpha=0.9)
        ax.errorbar(x, values, yerr=[lower, upper], fmt="none", color="#111827", capsize=5)
        ax.set_xticks(x, labels)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", color="#d1d5db", linewidth=0.6, alpha=0.75)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for index, row in enumerate(accepted):
            ax.text(
                index,
                float(row[high_field]) / scale,
                f"n={row['eligible_years']}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    fig.suptitle("Q90 low-flow comparison across equal 19-year periods", fontsize=14)
    fig.text(
        0.01,
        0.01,
        "Means use years with ≥95% accepted daily coverage; bars show 95% three-year block-bootstrap intervals.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(FIGURE_DIR / "period_comparison.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    observations = load_observations()
    all_summaries = []
    contrasts = []
    for screen in ("accepted", "good_only"):
        q90 = thresholds(observations, screen)["Q90"]
        annual_rows = annual_low_flow_metrics(observations, q90, screen)
        summaries, distributions = summarise_screen(screen, q90, annual_rows)
        all_summaries.extend(summaries)
        early = distributions["1967–1985"]
        late = distributions["2005–2023"]
        contrasts.append(contrast_row(screen, "mean days below Q90", early["days"], late["days"]))
        contrasts.append(
            contrast_row(screen, "mean annual deficit m3", early["deficit"], late["deficit"])
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "period_comparison.csv", all_summaries)
    write_csv(OUTPUT_DIR / "period_contrasts.csv", contrasts)
    plot_periods(all_summaries)
    accepted_contrasts = [row for row in contrasts if row["quality_screen"] == "accepted"]
    print(
        "Accepted-value late-minus-early contrasts: "
        f"{accepted_contrasts[0]['mean_difference']:.2f} days/year and "
        f"{accepted_contrasts[1]['mean_difference'] / 1_000_000:.3f} million m3/year."
    )


if __name__ == "__main__":
    main()

