"""Phase 1 figures: what the cleaning pipeline found and why each decision was taken."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import plotting as P
from .cleaning import CleaningLog
from .quality import IrreducibleError, LiquidusEvidence


def cleaning_funnel(log: CleaningLog, n_measured: int):
    stages = [
        ("Raw rows", log.get("load_raw").rows_after),
        ("After exact-duplicate drop", log.get("drop_exact_duplicates").rows_after),
        ("Canonical grades (twins merged)", log.get("collapse_to_grades").rows_after),
        ("Grades with measured TS", n_measured),
    ]
    labels, values = zip(*stages)
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    y = np.arange(len(values))[::-1]
    ax.barh(y, values, height=0.56, color=P.SKY)
    for yi, v in zip(y, values):
        ax.text(v + 25, yi, f"{v:,}", va="center", color=P.INK, fontsize=10)
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, max(values) * 1.12)
    ax.set_xlabel("Rows")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Cleaning funnel: {values[0]:,} listings describe {values[2]:,} grades")
    P.subtitle(ax, f"Exact duplicates and the spaced/hyphenated twin listings collapse; "
                   f"{values[2] - values[3]} grades lack a measured TS")
    P.source_note(fig)
    return fig


def twin_breakdown(listings: pd.DataFrame):
    """How the imputed rows are distributed across twin pairs."""
    g = listings.groupby("canonical_grade").agg(n=("listing_id", "size"), n_imp=("is_imputed_ts", "sum"))
    cats = pd.Series(np.select(
        [(g.n == 2) & (g.n_imp == 0), (g.n == 2) & (g.n_imp == 1), (g.n == 2) & (g.n_imp == 2),
         (g.n == 1) & (g.n_imp == 0), (g.n == 1) & (g.n_imp == 1)],
        ["Twin pair, both measured", "Twin pair, one imputed\n(measured twin recovers TS)",
         "Twin pair, both imputed", "Single listing, measured", "Single listing, imputed"], "?"),
        index=g.index).value_counts()
    order = ["Twin pair, both measured", "Twin pair, one imputed\n(measured twin recovers TS)",
             "Single listing, measured", "Twin pair, both imputed", "Single listing, imputed"]
    cats = cats.reindex(order).fillna(0).astype(int)
    colors = [P.SKY, P.FLAME, P.SKY, P.PINK, P.PINK]
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    y = np.arange(len(cats))[::-1]
    ax.barh(y, cats.values, height=0.56, color=colors)
    for yi, v in zip(y, cats.values):
        ax.text(v + 10, yi, f"{v:,}", va="center", color=P.INK, fontsize=10)
    ax.set_yticks(y, cats.index)
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, cats.max() * 1.14)
    ax.set_xlabel("Canonical grades")
    ax.grid(axis="y", visible=False)
    n_imp_rows = int(listings["is_imputed_ts"].sum())
    n_unmeasured = int(cats.iloc[3] + cats.iloc[4])
    ax.set_title("Imputation is mostly an artefact of the duplicated listing")
    P.subtitle(ax, f"{cats.iloc[1]} of {n_imp_rows} imputed rows have a twin with the measured strength; "
                   f"only {n_unmeasured} grades are truly unmeasured")
    P.source_note(fig)
    return fig


def liquidus_default(ev: LiquidusEvidence):
    low = ev.low_alloy.sort_values("C")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    nd, d = low[~low["is_default"]], low[low["is_default"]]
    ax.scatter(nd["C"], nd["liquidus_c"], s=26, color=P.SKY, linewidths=0.6, label=f"Other recorded values (n={len(nd)})", zorder=3)
    jitter = np.random.default_rng(0).uniform(-1.2, 1.2, len(d))
    ax.scatter(d["C"], d["liquidus_c"] + jitter, s=26, color=P.PINK, linewidths=0.6,
               label=f"Recorded 1460 °C (n={len(d)}, jittered ±1 °C)", zorder=3)
    cgrid = np.linspace(0, 1.0, 50)
    ax.plot(cgrid, 1536 - 78 * cgrid - 7.6 * 0.25 - 4.9 * 0.8 - 34 * 0.02 - 30 * 0.02, color=P.INK_2, lw=1.4,
            label="Empirical liquidus trend\n(typical Si 0.25, Mn 0.8, P/S 0.02)", zorder=2)
    ax.set_xlabel("Carbon (wt%)")
    ax.set_ylabel("Liquidus (°C)")
    ax.set_ylim(1380, 1560)
    ax.legend(loc="lower left")
    ax.set_title("1460 °C does not respond to carbon")
    P.subtitle(ax, "Carbon & low-alloy families, C ≤ 1 wt%: physics predicts a ~78 °C drop per wt% C")

    ax = axes[1]
    fam = ev.by_family.sort_values("share_1460")
    yy = np.arange(len(fam))
    ax.barh(yy, fam["share_1460"] * 100, height=0.6, color=P.PINK)
    for yi, (s, n) in enumerate(zip(fam["share_1460"], fam["n"])):
        ax.text(s * 100 + 1.5, yi, f"{s:.0%}  (n={n})", va="center", fontsize=8.5, color=P.INK_2)
    ax.set_yticks(yy, fam.index.str.replace("_", " "))
    ax.tick_params(axis="y", labelcolor=P.INK_2, labelsize=9)
    ax.set_xlim(0, 125)
    ax.set_xlabel("Grades recorded at 1460 °C (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Default concentrates in plain steels")
    P.subtitle(ax, "Never used for cast irons, high-speed steels, Fe-Ni alloys")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def processing_variants(ie: IrreducibleError, top: int = 16):
    g = ie.groups[ie.groups["ts_range"] > 0].head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    y = np.arange(len(g))
    ax.hlines(y, g["ts_min"], g["ts_max"], color=P.AXIS, lw=6, zorder=1)
    ax.scatter(g["ts_min"], y, color=P.SKY, s=48, zorder=3, label="Lowest TS in group")
    ax.scatter(g["ts_max"], y, color=P.PINK, s=48, zorder=3, label="Highest TS in group")
    labels = [f"{ex[:46]}{'…' if len(ex) > 46 else ''}  ({n} grades)" for ex, n in zip(g["example"], g["n"])]
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", labelcolor=P.INK_2, labelsize=8.5)
    for yi, r in zip(y, g["ts_range"]):
        ax.text(g["ts_max"].iloc[yi] + 25, yi, f"Δ {r:,.0f}", va="center", fontsize=8.5, color=P.INK_2)
    ax.set_xlabel("Tensile strength (MPa)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("Same chemistry, different strength: processing is not in the data")
    P.subtitle(ax, f"{ie.groups_with_spread} composition groups with measured TS spread; within-group MAE "
                   f"{ie.within_group_mae:.0f} MPa is the floor for these grades")
    P.source_note(fig)
    return fig
