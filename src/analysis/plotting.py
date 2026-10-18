"""Shared dark figure theme for every chart in reports/figures/.

Palette = dark-mode steps of a CVD-validated categorical set (validated with the dataviz
skill's validator against surface #1a1a19: all checks pass; the first three slots pass
all-pairs, so scatter plots use at most three hues plus grey "Other").
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .constants import FIGURES  # noqa: E402

SURFACE = "#1a1a19"
PAGE = "#0d0d0d"
INK = "#ffffff"
INK_2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
OTHER = "#5a5955"      # recessive grey for "Other" / context points

SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = SERIES

# Sequential (one hue, dark surface -> bright) and diverging (blue <-> red, grey midpoint)
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue", ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"])
DIVERGING = LinearSegmentedColormap.from_list("div_blue_red", ["#3987e5", "#383835", "#e66767"])
# sequential ramp for the dark surface: dim -> bright so low values stay visible against the background
SEQ_ON_DARK = LinearSegmentedColormap.from_list("seq_dark", ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"])

FONT = ["Segoe UI", "Inter", "DejaVu Sans", "sans-serif"]


def apply_theme() -> None:
    if "seq_blue" not in matplotlib.colormaps:
        matplotlib.colormaps.register(SEQ_BLUE)
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight", "savefig.pad_inches": 0.25,
        "font.family": "sans-serif", "font.sans-serif": FONT, "font.size": 10.5,
        "text.color": INK, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 24,
        "axes.labelsize": 10.5, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True, "axes.prop_cycle": plt.cycler(color=SERIES),
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": MUTED, "ytick.labelcolor": MUTED,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 6, "ytick.major.pad": 6,
        "legend.frameon": False, "legend.fontsize": 9.5, "legend.labelcolor": INK_2,
        "lines.linewidth": 2.0, "lines.markersize": 6, "patch.edgecolor": SURFACE,
        "scatter.edgecolors": SURFACE, "image.cmap": "seq_blue",
    })


def subtitle(ax, text: str, offset: float = 4) -> None:
    """Secondary line under the left-aligned title (the 'so what' of the chart).
    `offset` is the gap in points above the axes (raise it when ticks sit on top)."""
    ax.annotate(text, xy=(0, 1), xycoords="axes fraction", xytext=(0, offset), textcoords="offset points",
                ha="left", va="bottom", fontsize=9.5, color=INK_2)


def source_note(fig, text: str = "Source: data/raw/Alloys.csv · SteelScope analysis") -> None:
    fig.text(0.01, -0.02, text, ha="left", va="top", fontsize=8, color=MUTED)


def save(fig, name: str, folder: Path = FIGURES) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fold_categories(series, keep: list[str], other: str = "Other"):
    """Map every category not in `keep` to `other` (never generate extra hues)."""
    return series.where(series.isin(keep), other)
