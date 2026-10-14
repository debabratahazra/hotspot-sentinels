"""Generate the two diagrams the submission deck needs.

Drawn rather than hand-made so they stay in step with the codebase: the boxes
below are the actual modules and the arrows are the actual call order in
main.analyze_hotspot.

Run with:  uv run --with matplotlib --no-project python tools/make_deck_diagrams.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "deck-assets"

INK = "#13203a"
MUTED = "#5a6b85"
EDGE = "#b9c4d6"
GOOGLE = "#1a73e8"
AI = "#a142f4"
WARN = "#e8710a"
GOOD = "#1e8e3e"
PAPER = "#ffffff"


def box(ax, x, y, w, h, title, subtitle="", accent=INK, fill="#f6f8fc"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.6, edgecolor=accent, facecolor=fill, zorder=2))
    ax.text(x + w / 2, y + h / 2 + (0.018 if subtitle else 0), title,
            ha="center", va="center", fontsize=9.5, color=INK,
            fontweight="bold", zorder=3)
    if subtitle:
        ax.text(x + w / 2, y + h / 2 - 0.028, subtitle, ha="center", va="center",
                fontsize=7.6, color=MUTED, zorder=3)


def arrow(ax, start, end, label="", accent=MUTED, rad=0.0, t=0.5, label_dy=0.018):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.4,
        color=accent, connectionstyle=f"arc3,rad={rad}", zorder=1,
        shrinkA=2, shrinkB=4))
    if label:
        # t places the label along the arrow; midpoints collide with the boxes.
        ax.text(start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t + label_dy,
                label, ha="center", va="bottom", fontsize=7.2, color=accent,
                zorder=4, bbox=dict(boxstyle="round,pad=0.18", facecolor=PAPER,
                                    edgecolor="none", alpha=0.92))


def canvas(width, height, title):
    fig, ax = plt.subplots(figsize=(width, height), dpi=220)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.965, title, ha="center", va="top", fontsize=12.5,
            color=INK, fontweight="bold")
    return fig, ax


def process_flow() -> Path:
    fig, ax = canvas(11, 5.6, "Process flow — image or coordinate to retrofit plan")

    box(ax, 0.02, 0.56, 0.17, 0.15, "Operator", "upload or coordinate", GOOGLE)
    box(ax, 0.02, 0.26, 0.17, 0.15, "Streamlit dashboard", "Cloud Run", GOOGLE)
    box(ax, 0.26, 0.40, 0.19, 0.17, "FastAPI backend", "POST /api/analyze", GOOGLE, "#eef4ff")

    box(ax, 0.52, 0.72, 0.21, 0.14, "Maps Static API", "satellite imagery", MUTED)
    box(ax, 0.52, 0.53, 0.21, 0.14, "BigQuery", "NOAA GSOD ambient °C", MUTED)
    box(ax, 0.52, 0.34, 0.21, 0.14, "Gemini 2.5 Flash", "surfaces → JSON schema", AI, "#f7f0ff")
    box(ax, 0.52, 0.15, 0.21, 0.14, "Firestore", "scan record", MUTED)

    box(ax, 0.79, 0.53, 0.19, 0.14, "Pub/Sub", "if HVI ≥ 8.0", WARN, "#fff5e9")
    box(ax, 0.79, 0.31, 0.19, 0.14, "Public alert wall", "Firebase Hosting", GOOD, "#edf8f0")
    box(ax, 0.79, 0.09, 0.19, 0.14, "HVI + blueprint", "back to the operator", GOOGLE)

    arrow(ax, (0.105, 0.56), (0.105, 0.41), "1", t=0.5, label_dy=-0.005)
    arrow(ax, (0.19, 0.335), (0.26, 0.45), "2  POST", t=0.5, label_dy=0.006)
    for y, n in ((0.79, "3  imagery"), (0.60, "4  telemetry"), (0.41, "5  analyse"), (0.22, "6  persist")):
        arrow(ax, (0.45, 0.49), (0.52, y), n, t=0.38, label_dy=0.004)
    arrow(ax, (0.73, 0.60), (0.79, 0.60), "7  CRITICAL only", WARN, t=0.5, label_dy=0.012)
    arrow(ax, (0.885, 0.53), (0.885, 0.45), "", GOOD)
    arrow(ax, (0.73, 0.41), (0.79, 0.16), "8  report", GOOGLE, rad=0.12, t=0.42, label_dy=0.012)

    ax.text(0.5, 0.035, "Every cloud call is isolated: a failed alert or climate lookup "
                        "degrades the report, it never fails the analysis.",
            ha="center", va="bottom", fontsize=8, color=MUTED, style="italic")

    path = ASSETS / "diagram-process-flow.png"
    fig.savefig(path, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)
    return path


def architecture() -> Path:
    fig, ax = canvas(11, 6.0, "Architecture — Google Cloud, region asia-southeast1")

    def band(y, h, label, fill):
        ax.add_patch(FancyBboxPatch((0.015, y), 0.97, h,
                                    boxstyle="round,pad=0.004,rounding_size=0.012",
                                    linewidth=0, facecolor=fill, zorder=0))
        # Left margin, vertically centred: stacking it above the boxes crowded them.
        ax.text(0.032, y + h / 2, label, ha="left", va="center", fontsize=7.6,
                color=MUTED, fontweight="bold", rotation=90, zorder=1)

    band(0.735, 0.17, "PRESENTATION", "#f3f6fb")
    band(0.515, 0.20, "APPLICATION", "#eef4ff")
    band(0.245, 0.25, "DATA & AI", "#f7f3ff")
    band(0.025, 0.20, "PLATFORM", "#f4f7f4")

    left, width, gap = 0.075, 0.283, 0.015

    def col(i):
        return left + i * (width + gap)

    box(ax, col(0), 0.775, width, 0.105, "Streamlit dashboard", "planners · Cloud Run", GOOGLE)
    box(ax, col(1), 0.775, width, 0.105, "Public alert wall", "citizens · Firebase Hosting", GOOD, "#edf8f0")
    box(ax, col(2), 0.775, width, 0.105, "REST API", "8 endpoints · OpenAPI", GOOGLE)

    box(ax, col(0), 0.555, width * 1.5 + gap, 0.11, "FastAPI — the only HTTP layer",
        "async orchestration · Pydantic contracts", GOOGLE, "#eef4ff")
    box(ax, col(1) + width * 0.5 + gap, 0.555, width * 1.5, 0.11, "services/ and tools/",
        "vision · alerts · database · climate · imagery · geocoding · places", MUTED)

    box(ax, col(0), 0.375, width, 0.095, "Gemini 2.5 Flash", "Vertex AI · JSON schema", AI, "#f7f0ff")
    box(ax, col(1), 0.375, width, 0.095, "Firestore", "scans + curated alerts", MUTED)
    box(ax, col(2), 0.375, width, 0.095, "BigQuery", "NOAA GSOD (US location)", MUTED)
    box(ax, col(0), 0.265, width, 0.095, "Cloud Storage", "shared imagery cache", MUTED)
    box(ax, col(1), 0.265, width, 0.095, "Pub/Sub", "CRITICAL alert fan-out", WARN, "#fff5e9")
    box(ax, col(2), 0.265, width, 0.095, "Maps · Geocoding · Places", "key never reaches browser", MUTED)

    box(ax, col(0), 0.125, width, 0.09, "Cloud Run", "2 containers · scale to zero", GOOGLE)
    box(ax, col(1), 0.125, width, 0.09, "Secret Manager", "mounted, not env vars", GOOD, "#edf8f0")
    box(ax, col(2), 0.125, width, 0.09, "GitHub Actions", "WIF · zero key files", GOOD, "#edf8f0")
    box(ax, col(0), 0.04, width * 3 + gap * 2, 0.07,
        "One runtime service account · six narrow roles · 815 tests · 96% backend coverage",
        "", INK, "#ffffff")

    path = ASSETS / "diagram-architecture.png"
    fig.savefig(path, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)
    return path


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for path in (process_flow(), architecture()):
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
