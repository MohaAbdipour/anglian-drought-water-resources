"""Draw the evidence pathway used in the River Wensum drought study."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "docs" / "figures"

COLOURS = {
    "ink": "#18323f",
    "muted": "#516974",
    "flow": "#dceef4",
    "flow_edge": "#2d7189",
    "rain": "#e2edf8",
    "rain_edge": "#477da8",
    "groundwater": "#e8e2f2",
    "groundwater_edge": "#705b91",
    "quality": "#eef2e6",
    "quality_edge": "#668047",
    "analysis": "#fff0dd",
    "analysis_edge": "#b56b2d",
    "synthesis": "#f6e3e1",
    "synthesis_edge": "#a94d45",
    "output": "#e1eee9",
    "output_edge": "#3f7664",
    "arrow": "#6b7e86",
}


def add_box(
    axis,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    lines: list[str],
    face: str,
    edge: str,
    title_size: float = 11,
    body_size: float = 8.6,
) -> None:
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.5,
        facecolor=face,
        edgecolor=edge,
    )
    axis.add_patch(box)
    axis.text(
        x + 0.025 * width,
        y + height - 0.24 * height,
        title,
        ha="left",
        va="center",
        fontsize=title_size,
        fontweight="bold",
        color=COLOURS["ink"],
    )
    axis.text(
        x + 0.025 * width,
        y + height - 0.53 * height,
        "\n".join(lines),
        ha="left",
        va="top",
        fontsize=body_size,
        linespacing=1.35,
        color=COLOURS["muted"],
    )


def arrow(axis, start: tuple[float, float], end: tuple[float, float], curved: float = 0) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.35,
            color=COLOURS["arrow"],
            connectionstyle=f"arc3,rad={curved}",
            shrinkA=2,
            shrinkB=2,
        )
    )


def make_schematic(output_stem: Path) -> None:
    fig, axis = plt.subplots(figsize=(15.2, 8.7))
    fig.patch.set_facecolor("white")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")

    axis.text(
        0.5,
        0.965,
        "River Wensum low-flow drought analysis",
        ha="center",
        va="top",
        fontsize=20,
        fontweight="bold",
        color=COLOURS["ink"],
    )
    axis.text(
        0.5,
        0.925,
        "Evidence pathway from open observations to a qualified hydrological interpretation",
        ha="center",
        va="top",
        fontsize=11.5,
        color=COLOURS["muted"],
    )

    # Source observations
    add_box(
        axis, 0.04, 0.72, 0.27, 0.15,
        "River flow",
        ["EA qualified daily mean flow", "Fakenham · NRFA 34011 · 1966–2023"],
        COLOURS["flow"], COLOURS["flow_edge"],
    )
    add_box(
        axis, 0.365, 0.72, 0.27, 0.15,
        "Regional precipitation",
        ["Met Office HadSEEP daily totals", "Long-record context; not catchment rainfall"],
        COLOURS["rain"], COLOURS["rain_edge"],
    )
    add_box(
        axis, 0.69, 0.72, 0.27, 0.15,
        "Chalk groundwater",
        ["EA qualified dipped levels", "Great Ryburg borehole · 4.65 km away"],
        COLOURS["groundwater"], COLOURS["groundwater_edge"],
    )

    # Quality and provenance gate
    add_box(
        axis, 0.18, 0.52, 0.64, 0.125,
        "Identity, provenance and quality gates",
        [
            "Station and measure checks · OGL attribution · request URLs and SHA-256 checksums",
            "Good + Estimated observations · completed record to 2023 · no gap interpolation",
        ],
        COLOURS["quality"], COLOURS["quality_edge"], title_size=11.5, body_size=8.8,
    )
    for x in (0.175, 0.5, 0.825):
        arrow(axis, (x, 0.72), (0.5, 0.645), curved=(0.12 if x < 0.5 else -0.12 if x > 0.5 else 0))

    # Parallel analyses
    add_box(
        axis, 0.06, 0.29, 0.41, 0.15,
        "Low-flow event analysis",
        [
            "1991–2020 Q80 / Q90 / Q95 thresholds",
            "Duration · minimum flow · accumulated deficit",
            "Censoring and 5-day pooling sensitivities",
        ],
        COLOURS["analysis"], COLOURS["analysis_edge"],
    )
    add_box(
        axis, 0.53, 0.29, 0.41, 0.15,
        "Hydroclimatic context",
        [
            "180- and 365-day antecedent rainfall percentiles",
            "Nearest accepted groundwater level within ±45 days",
            "Seasonally matched 1991–2020 comparisons",
        ],
        COLOURS["analysis"], COLOURS["analysis_edge"],
    )
    arrow(axis, (0.41, 0.52), (0.265, 0.44), curved=0.06)
    arrow(axis, (0.59, 0.52), (0.735, 0.44), curved=-0.06)

    # Joint interpretation
    add_box(
        axis, 0.18, 0.095, 0.64, 0.115,
        "Joint evidence and qualified inference",
        [
            "Coverage-screened period comparison · three-year block-bootstrap uncertainty",
            "Observed drought behaviour, with abstraction and spatial-scale limits retained",
        ],
        COLOURS["synthesis"], COLOURS["synthesis_edge"], title_size=11.5, body_size=8.8,
    )
    arrow(axis, (0.265, 0.29), (0.41, 0.21), curved=-0.05)
    arrow(axis, (0.735, 0.29), (0.59, 0.21), curved=0.05)

    # Output band
    axis.add_patch(
        FancyBboxPatch(
            (0.18, 0.025), 0.64, 0.045,
            boxstyle="round,pad=0.008,rounding_size=0.014",
            linewidth=1.2,
            facecolor=COLOURS["output"],
            edgecolor=COLOURS["output_edge"],
        )
    )
    axis.text(
        0.5, 0.047,
        "Checked tables  ·  scientific figures  ·  methods  ·  synthesis",
        ha="center", va="center", fontsize=9.7, fontweight="bold", color=COLOURS["ink"],
    )
    arrow(axis, (0.5, 0.095), (0.5, 0.071))

    fig.text(
        0.985, 0.012,
        "Observed record: 1966–2023  |  seasonal reference: 1991–2020",
        ha="right", va="bottom", fontsize=8.5, color=COLOURS["muted"],
    )
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(output_stem.with_suffix(".png"), dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    make_schematic(FIGURES / "study_workflow")
    print("Created study workflow schematic as SVG and PNG.")


if __name__ == "__main__":
    main()
