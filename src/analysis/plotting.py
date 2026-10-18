"""Shared "Neon Forge" theme for every chart in reports/figures/.

A midnight-violet canvas with a soft glow, maximum-chroma categorical hues and plasma-style ramps.
The categorical palette was validated with the dataviz skill's validator against the surface #0e0b1e
(dark mode): lightness band, chroma floor, adjacent CVD separation (worst ΔE 9.7), normal-vision floor
(worst ΔE 18.5) and contrast all pass; the first three slots also pass all-pairs, so scatter plots use
at most three hues plus a recessive "Other".
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import patheffects as pe  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .constants import FIGURES  # noqa: E402

# ---- canvas & ink ------------------------------------------------------------------------
SURFACE = "#0e0b1e"     # midnight violet
SURFACE_2 = "#1a1536"   # raised panels, callout boxes
GLOW_BG = "#221a4d"     # soft radial glow behind the plot
INK = "#ffffff"
INK_2 = "#d4ceef"       # lavender-grey secondary text
MUTED = "#948db4"
GRID = "#251f45"
AXIS = "#3b3463"
OTHER = "#4b4470"       # recessive context marks ("Other", non-highlighted)
GOLD = "#ffd166"        # story accent: callout arrows and rings (annotation only, never a data series)

# ---- categorical: fixed order, never cycled ----------------------------------------------
SKY, PINK, FLAME, VIOLET, LIME, MAGENTA, TEAL, AMBER = SERIES = [
    "#0d9de5", "#ff0d89", "#ed6300", "#a053fd", "#5bab0f", "#ef0be8", "#07a4a4", "#c58501"]

# ---- sequential & diverging ---------------------------------------------------------------
# Plasma-style ramp (indigo -> magenta -> orange -> gold): monotonic in lightness, colour-blind safe,
# and it starts above the canvas so the lowest values never disappear.
_PLASMA = plt.get_cmap("plasma")(np.linspace(0.14, 1.0, 256))
SEQ = LinearSegmentedColormap.from_list("neon_seq", _PLASMA)
SEQ_ON_DARK = SEQ                                   # name used by older figure code
DIVERGING = LinearSegmentedColormap.from_list("neon_div", [SKY, "#2b2547", PINK])

FONT = ["Segoe UI", "Inter", "DejaVu Sans", "sans-serif"]


def apply_theme() -> None:
    if "neon_seq" not in matplotlib.colormaps:
        matplotlib.colormaps.register(SEQ)
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": "none", "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight", "savefig.pad_inches": 0.3,
        "font.family": "sans-serif", "font.sans-serif": FONT, "font.size": 10.5,
        "text.color": INK, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titlesize": 13.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 24,
        "axes.labelsize": 10.5, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True, "axes.prop_cycle": plt.cycler(color=SERIES),
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": MUTED, "ytick.labelcolor": MUTED,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 6, "ytick.major.pad": 6,
        "legend.frameon": False, "legend.fontsize": 9.5, "legend.labelcolor": INK_2,
        "lines.linewidth": 2.2, "lines.markersize": 6, "patch.edgecolor": SURFACE,
        "scatter.edgecolors": SURFACE, "image.cmap": "neon_seq",
    })


# ---- story helpers ------------------------------------------------------------------------
def subtitle(ax, text: str, offset: float = 4) -> None:
    """Secondary line under the left-aligned title (the 'so what' of the chart).
    `offset` is the gap in points above the axes (raise it when ticks sit on top)."""
    ax.annotate(text, xy=(0, 1), xycoords="axes fraction", xytext=(0, offset), textcoords="offset points",
                ha="left", va="bottom", fontsize=9.8, color=INK_2)


def callout(ax, text: str, xy, xytext, ha: str = "left", rad: float = 0.25, fontsize: float = 9.5,
            textcoords: str = "data", zorder: int = 30):
    """A story beat pinned to the data: gold arrow + framed text (text stays in ink colours)."""
    return ax.annotate(text, xy=xy, xytext=xytext, textcoords=textcoords, ha=ha, va="center", fontsize=fontsize,
                       color=INK, fontweight="semibold", zorder=zorder,
                       bbox={"boxstyle": "round,pad=0.45", "fc": SURFACE_2, "ec": GOLD, "lw": 1.1, "alpha": 0.95},
                       arrowprops={"arrowstyle": "-|>", "color": GOLD, "lw": 1.4,
                                   "connectionstyle": f"arc3,rad={rad}", "shrinkB": 4})


def ring(ax, x, y, size: float = 260, zorder: int = 25):
    """Gold halo around a point that the story is about."""
    ax.scatter([x], [y], s=size, facecolors="none", edgecolors=GOLD, linewidths=1.8, zorder=zorder)


def glow(artist, color: str, width: float = 2.2, layers: int = 4):
    """Neon glow: soft translucent strokes under a line or outline."""
    effects = [pe.Stroke(linewidth=width + 2.5 * i, foreground=color, alpha=0.09) for i in range(layers, 0, -1)]
    artist.set_path_effects(effects + [pe.Normal()])
    return artist


def source_note(fig, text: str = "Source: data/raw/Alloys.csv · SteelScope analysis") -> None:
    fig.text(0.01, -0.02, text, ha="left", va="top", fontsize=8, color=MUTED)


def _backdrop(fig) -> None:
    """Soft radial glow behind everything; the edges fade into SURFACE so tight cropping leaves no seam."""
    if getattr(fig, "_neon_backdrop", False):
        return
    bg = fig.add_axes([0, 0, 1, 1], zorder=-100)
    bg.set_axis_off()
    y, x = np.mgrid[-1:1:240j, -1:1:240j]
    r = np.sqrt((x * 0.9) ** 2 + ((y - 0.45) * 1.1) ** 2)
    img = np.clip(1 - r / 1.5, 0, 1) ** 2
    img *= np.clip(1 - np.abs(x) ** 6, 0, 1) * np.clip(1 - np.abs(y) ** 6, 0, 1)   # fade to SURFACE at the edges: no seam
    bg.imshow(img, cmap=LinearSegmentedColormap.from_list("bg", [SURFACE, GLOW_BG]), extent=[0, 1, 0, 1],
              aspect="auto", origin="lower", interpolation="bicubic")
    fig._neon_backdrop = True


def save(fig, name: str, folder: Path = FIGURES) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    _backdrop(fig)
    fig.savefig(path)
    plt.close(fig)
    return path


def fold_categories(series, keep: list[str], other: str = "Other"):
    """Map every category not in `keep` to `other` (never generate extra hues)."""
    return series.where(series.isin(keep), other)
