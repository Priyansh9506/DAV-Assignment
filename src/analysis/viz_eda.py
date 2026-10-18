"""Phase 2 EDA figures. Each function answers one question and returns a matplotlib Figure."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from . import eda as E
from . import plotting as P
from .features import FAMILY_GROUP_ORDER as GROUP_ORDER
from .features import family_group

TS = E.TS
SEQ_ON_DARK = P.SEQ_ON_DARK

GROUP_COLOR = dict(zip(GROUP_ORDER, P.SERIES))   # fixed order: colour follows the group, never its rank


# ---------------------------------------------------------------------------------- Q1
def strength_by_family(grades: pd.DataFrame):
    m = E.measured(grades)
    order = m.groupby("family_label")[TS].median().sort_values().index.tolist()
    data = [m.loc[m["family_label"] == f, TS].values for f in order]
    fig, ax = plt.subplots(figsize=(10, 7.2))
    y = np.arange(len(order))
    rng = np.random.default_rng(1)
    for yi, d in zip(y, data):
        ax.scatter(d, yi + rng.uniform(-0.18, 0.18, len(d)), s=7, color=P.MUTED, alpha=0.45, linewidths=0, zorder=2)
    bp = ax.boxplot(data, positions=y, vert=False, widths=0.55, patch_artist=True, showfliers=False,
                    medianprops={"color": P.INK, "linewidth": 2}, whiskerprops={"color": P.BLUE, "linewidth": 1.2},
                    capprops={"color": P.BLUE, "linewidth": 1.2},
                    boxprops={"facecolor": (0.22, 0.53, 0.9, 0.28), "edgecolor": P.BLUE, "linewidth": 1.2})
    for yi, d in zip(y, data):
        ax.text(2560, yi, f"n={len(d)}", va="center", ha="left", fontsize=8.5, color=P.MUTED)
    ax.set_yticks(y, order)
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 2700)
    ax.set_xlabel("Tensile strength (MPa)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Family sets the strength range before chemistry fine-tunes it")
    P.subtitle(ax, "Measured grades only. Boxes = IQR, line = median, dots = individual grades")
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q2
def carbon_paradox(grades: pd.DataFrame, ce: dict):
    m = E.measured(grades)
    grp = family_group(m["family"])
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True)
    ax = axes[0]
    for name, color in [("Other", P.OTHER), ("Carbon & low-alloy", P.BLUE), ("Cast iron", P.ORANGE)]:
        s = m[(grp == name) if name != "Other" else ~grp.isin(["Carbon & low-alloy", "Cast iron"])]
        ax.scatter(s["C"], s[TS], s=16, color=color, linewidths=0.4, label=f"{name if name != 'Other' else 'All other families'} (n={len(s)})",
                   zorder=3 if name != "Other" else 2)
    ax.set_xlabel("Carbon (wt%)")
    ax.set_ylabel("Tensile strength (MPa)")
    ax.legend(loc="upper right")
    ax.set_title(f"Pooled: no carbon signal (ρ = {ce['rho_all']:.2f})")
    P.subtitle(ax, "Cast irons carry 2–4 % C but are mostly weak, cancelling the steel trend")

    ax = axes[1]
    plain = m[m["family"].isin(E.PLAIN_STEEL_FAMILIES) & (m["C"] <= 1.0)]
    carbon = plain[plain["family"] == "carbon"]
    other_plain = plain[plain["family"] != "carbon"]
    ax.scatter(other_plain["C"], other_plain[TS], s=16, color=P.OTHER, linewidths=0.4,
               label=f"Low-alloy families (n={len(other_plain)})", zorder=2)
    ax.scatter(carbon["C"], carbon[TS], s=18, color=P.BLUE, linewidths=0.4, label=f"Carbon / non-alloy (n={len(carbon)})", zorder=3)
    ts_fit = stats.theilslopes(carbon[TS], carbon["C"])
    xx = np.linspace(0, carbon["C"].max(), 50)
    ax.plot(xx, ts_fit.intercept + ts_fit.slope * xx, color=P.INK, lw=1.6, zorder=4,
            label=f"Theil–Sen fit: +{ce['theil_sen_mpa_per_0p1C']:.0f} MPa per 0.1 % C")
    ax.set_xlabel("Carbon (wt%)")
    ax.legend(loc="upper left")
    ax.set_title(f"Within carbon & low-alloy steels: ρ = {ce['rho_plain']:.2f}")
    P.subtitle(ax, f"Carbon family alone: ρ = {ce['rho_carbon_family']:.2f}; C ≤ 1 wt%")
    fig.tight_layout(w_pad=2.5)
    P.source_note(fig)
    return fig


def correlation_heatmap(rho: pd.DataFrame, sizes: pd.Series):
    labels = {"carbon_equivalent": "Carbon equivalent", "alloying_total": "Alloying total (100 − Fe)"}
    fig, ax = plt.subplots(figsize=(10, 7.6))
    vals = rho.values.astype(float)
    im = ax.imshow(np.ma.masked_invalid(vals), cmap=P.DIVERGING, vmin=-0.8, vmax=0.8, aspect="auto")
    ax.set_facecolor(P.SURFACE)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                ax.text(j, i, "–", ha="center", va="center", color=P.MUTED, fontsize=9)
            elif abs(v) >= 0.3:
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", color=P.INK, fontsize=9, fontweight="semibold")
    ax.set_xticks(range(len(rho.columns)), [f"{c}\n(n={sizes[c]})" for c in rho.columns], fontsize=9)
    ax.set_yticks(range(len(rho.index)), [labels.get(f, f) for f in rho.index])
    ax.tick_params(axis="both", labelcolor=P.INK_2)
    ax.xaxis.tick_top()
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Spearman ρ with tensile strength", color=P.INK_2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=P.MUTED)
    ax.set_title("Element–strength relationships flip sign between families", pad=62)
    P.subtitle(ax, "Values shown where |ρ| ≥ 0.3; '–' = element (near-)absent in that group", offset=42)
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q3
def cr_ni_map(grades: pd.DataFrame, profile: pd.DataFrame):
    m = E.measured(grades)
    s = m[m["family"] == "stainless"].sort_values(TS)
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    sc = ax.scatter(s["Cr"], s["Ni"], c=s[TS], cmap=SEQ_ON_DARK, vmin=450, vmax=1050, s=26, linewidths=0.5,
                    edgecolors=P.SURFACE, zorder=3)
    ax.axhline(8, color=P.AXIS, lw=1, zorder=1)
    ax.axhline(3, color=P.AXIS, lw=1, zorder=1)
    ax.plot([20, 20], [3, 8], color=P.AXIS, lw=1, zorder=1)
    pos = {"Austenitic (Ni ≥ 8)": (25.5, 30), "Duplex-type (Cr ≥ 20, Ni 3–8)": (25.5, 5.6),
           "Ni-bearing martensitic / PH (Ni 3–8, Cr < 20)": (6.5, 5.6), "Ferritic / martensitic (Ni < 3)": (6.5, 1.3)}
    for name, (x, y) in pos.items():
        if name in profile.index:
            r = profile.loc[name]
            ax.text(x, y, f"{name}\nmedian {r['median_ts']:.0f} MPa · n={int(r['n'])}", fontsize=8.5, color=P.INK_2,
                    va="center", ha="left", bbox={"facecolor": P.SURFACE, "edgecolor": "none", "alpha": 0.8, "pad": 2})
    ax.set_xlabel("Chromium (wt%)")
    ax.set_ylabel("Nickel (wt%)")
    ax.set_yscale("symlog", linthresh=2)
    ax.set_yticks([0, 1, 2, 3, 5, 8, 15, 25, 40], ["0", "1", "2", "3", "5", "8", "15", "25", "40"])
    cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02, extend="both")
    cb.set_label("Tensile strength (MPa)", color=P.INK_2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=P.MUTED)
    ax.set_title("Stainless strength follows microstructure, not alloy content")
    P.subtitle(ax, "Stainless grades on the Cr–Ni map (Ni on a symlog axis); duplex and PH grades out-pull fully austenitic ones")
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q4
def ce_small_multiples(grades: pd.DataFrame, ce_tab: pd.DataFrame):
    m = E.measured(grades)
    panels = ["Carbon & low-alloy", "Tool & high-speed", "Stainless"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=True)
    for ax, name in zip(axes, panels):
        s = E.subset(m, E.FAMILY_GROUPS[name])
        ax.scatter(s["carbon_equivalent"], s[TS], s=14, color=P.BLUE, linewidths=0.3)
        r = ce_tab.loc[name]
        ax.set_title(f"{name}: ρ = {r['rho_CE']:.2f}", fontsize=11.5)
        P.subtitle(ax, f"n = {int(r['n'])}")
        ax.set_xlabel("Carbon equivalent, IIW (wt%)")
    axes[0].set_ylabel("Tensile strength (MPa)")
    fig.suptitle("Carbon equivalent predicts strength in plain and tool steels, not in stainless",
                 x=0.01, ha="left", fontsize=13, fontweight="semibold", color=P.INK, y=1.06)
    fig.tight_layout(w_pad=2)
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q5
def design_space(grades: pd.DataFrame, ds: dict):
    m = E.measured(grades)
    grp = family_group(m["family"])
    show = ["Carbon & low-alloy", "Stainless", "Cast iron"]
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    rng = np.random.default_rng(3)
    other = m[~grp.isin(show)]
    ax.scatter(other["liquidus_c"], other[TS], s=14, color=P.OTHER, linewidths=0, label=f"Other families (n={len(other)})", zorder=2)
    for name, color in zip(show, [P.BLUE, P.ORANGE, P.AQUA]):
        s = m[grp == name]
        d, nd = s[s["liquidus_is_default"]], s[~s["liquidus_is_default"]]
        ax.scatter(nd["liquidus_c"], nd[TS], s=18, color=color, linewidths=0.4, label=f"{name} (n={len(s)})", zorder=3)
        if len(d):
            ax.scatter(d["liquidus_c"] + rng.uniform(-4, 4, len(d)), d[TS], s=18, facecolors="none", edgecolors=color,
                       linewidths=0.9, zorder=3)
    ax.scatter([], [], s=18, facecolors="none", edgecolors=P.INK_2, label="Hollow = default 1460 °C liquidus (x-jittered ±4 °C)")
    ax.set_xlabel("Liquidus, melting completion (°C)")
    ax.set_ylabel("Tensile strength (MPa)")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Strength and liquidus are near-independent design axes")
    P.subtitle(ax, f"All grades: Spearman ρ = {ds['spearman_all']:.2f}, Pearson r = {ds['pearson_all']:.2f}.  "
                   f"Excluding default liquidus (n = {ds['n_non_default']}): ρ = {ds['spearman_non_default']:.2f}, "
                   f"r = {ds['pearson_non_default']:.2f}")
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q6
def class_drivers(sep: pd.DataFrame, grades: pd.DataFrame, top: int = 10):
    labels = {"carbon_equivalent": "Carbon equivalent", "alloying_total": "Alloying total", "cr_eq": "Cr equivalent",
              "ni_eq": "Ni equivalent"}
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    s = sep.head(top).iloc[::-1]
    ax.barh(range(len(s)), s["epsilon_sq"], height=0.6, color=P.BLUE)
    for i, (feat, r) in enumerate(s.iterrows()):
        meds = (r["median_low"], r["median_medium"], r["median_high"])
        if max(meds) > 0:
            txt = "median " + " / ".join(f"{v:.2g}" for v in meds)
        else:   # element absent from most grades: the share that contain it is the informative number
            txt = "present in " + " / ".join(f"{v:.0%}" for v in
                                              (r["share_nonzero_low"], r["share_nonzero_medium"], r["share_nonzero_high"]))
        ax.text(r["epsilon_sq"] + 0.004, i, txt, va="center", fontsize=8, color=P.INK_2)
    ax.set_yticks(range(len(s)), [labels.get(f, f) for f in s.index])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, s["epsilon_sq"].max() * 2.0)
    ax.set_xlabel("Effect size ε² (Kruskal–Wallis across the 3 classes)")
    ax.grid(axis="y", visible=False)
    ax.set_title("What separates strength classes")
    P.subtitle(ax, "Annotations: low / medium / high class (median wt%, or share of grades containing the element)")

    ax = axes[1]
    m = E.measured(grades)
    m = m.assign(group=family_group(m["family"]))
    ct = pd.crosstab(m["strength_class_label"], m["group"], normalize="index").reindex(columns=GROUP_ORDER, fill_value=0)
    counts = m["strength_class_label"].value_counts()
    order = ["Low (<300 MPa)", "Medium (300-600 MPa)", "High (>600 MPa)"]
    ct = ct.reindex(order)
    left = np.zeros(len(ct))
    for g in GROUP_ORDER:
        vals = ct[g].values
        ax.barh(range(len(ct)), vals, left=left, height=0.55, color=GROUP_COLOR[g], label=g, edgecolor=P.SURFACE, linewidth=2)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 0.07:
                ax.text(l + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8.5, color=P.INK)
        left += vals
    ax.set_yticks(range(len(ct)), [f"{c}\nn={counts.get(c, 0)}" for c in ct.index])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9)
    ax.set_title("Family mix of each class")
    P.subtitle(ax, "Low class is essentially cast iron; high class is alloy-rich")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


# ---------------------------------------------------------------------------------- Q7
def imputation_sensitivity(listings: pd.DataFrame, grades: pd.DataFrame, sens: pd.DataFrame):
    bins = np.arange(100, 2501, 25)
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    naive = listings["tensile_strength_raw"]
    meas = grades[TS].dropna()
    ax.hist(naive, bins=bins, histtype="step", color=P.ORANGE, lw=2, label=f"Naive: every listing, imputed kept (n={len(naive)})")
    ax.hist(meas, bins=bins, histtype="step", color=P.BLUE, lw=2, label=f"Used: one row per grade, measured only (n={len(meas)})")
    peak = naive.round(0).value_counts().idxmax()
    ax.annotate(f"Imputed spike at {peak:.0f} MPa", xy=(peak, np.histogram(naive, bins=bins)[0].max()),
                xytext=(1000, np.histogram(naive, bins=bins)[0].max() * 0.9), color=P.INK_2, fontsize=9,
                arrowprops={"arrowstyle": "-", "color": P.MUTED, "lw": 0.8})
    ax.set_xlim(100, 2500)
    ax.set_xlabel("Tensile strength (MPa)")
    ax.set_ylabel("Count per 25 MPa bin")
    ax.legend(loc="upper right")
    a, c = sens.iloc[0], sens.iloc[2]
    ax.set_title("Keeping imputed rows fakes a peak and inflates the high-strength class")
    P.subtitle(ax, f"High-class share {a['share_high_class']:.0%} naive vs {c['share_high_class']:.0%} measured; "
                   f"median {a['ts_median']:.0f} vs {c['ts_median']:.0f} MPa")
    P.source_note(fig)
    return fig
