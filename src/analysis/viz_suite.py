"""Visual-analytics suite (notebook 04): summaries, binning, chi-square, regression, PCA, k-means,
circular migration (chord) plots, ring / donut, circular columns, treemap, radar and waterfall charts.

Geometry for the circular charts is computed by `*_geometry` functions that return plain DataFrames, so the
exact same shapes are exported for Tableau (which has no native chord or radar chart).
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import squarify
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch, PathPatch, Wedge
from matplotlib.path import Path
from scipy import stats
from sklearn.metrics import silhouette_samples

from . import plotting as P
from . import visual_stats as V
from .features import FAMILY_GROUP_ORDER, family_group

TS = V.TS
GROUP_COLOR = dict(zip(FAMILY_GROUP_ORDER, P.SERIES))   # fixed order: colour follows the group, never its rank
SCATTER_GROUPS = ["Carbon & low-alloy", "Stainless", "Cast iron"]   # ≤3 hues on scatters (all-pairs CVD rule)
SCATTER_COLOR = dict(zip(SCATTER_GROUPS, [P.BLUE, P.ORANGE, P.AQUA]))


def _title(fig, title: str, sub: str | None = None, y: float = 1.02):
    fig.suptitle(title, x=0.01, y=y, ha="left", fontsize=14, fontweight="semibold", color=P.INK)
    if sub:
        fig.text(0.01, y - 0.035, sub, ha="left", va="top", fontsize=10, color=P.INK_2)


def _clean_axis(ax):
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


# =============================================================================================
# A. Summaries
# =============================================================================================
FIVE_VARS = [TS, "liquidus_c", "carbon_equivalent", "alloying_total", "C", "Cr"]


def five_number_boxes(df: pd.DataFrame, fns: pd.DataFrame):
    fig, axes = plt.subplots(len(FIVE_VARS), 1, figsize=(12, 1.7 * len(FIVE_VARS) + 0.6))
    rng = np.random.default_rng(0)
    for ax, var in zip(axes, FIVE_VARS):
        s = df[var].dropna()
        r = fns.loc[var]
        ax.scatter(s, rng.uniform(-0.28, 0.28, len(s)), s=5, color=P.MUTED, alpha=0.35, linewidths=0, zorder=1)
        ax.boxplot(s, vert=False, widths=0.5, positions=[0], patch_artist=True, showfliers=False,
                   boxprops={"facecolor": to_rgba(P.BLUE, 0.25), "edgecolor": P.BLUE, "linewidth": 1.4},
                   whiskerprops={"color": P.BLUE}, capprops={"color": P.BLUE}, medianprops={"color": P.INK, "linewidth": 2.2})
        lo_x, hi_x = s.min(), s.max()
        span = (hi_x - lo_x) or 1.0
        last_frac, level = -1.0, 0
        for key, val in [("min", r["min"]), ("Q1", r["Q1"]), ("median", r["median"]), ("Q3", r["Q3"]), ("max", r["max"])]:
            frac = (val - lo_x) / span
            level = level + 1 if frac - last_frac < 0.07 else 0      # stagger labels that would collide
            last_frac = frac
            ax.annotate(f"{key} {val:,.4g}", (val, 0.33 + 0.27 * level), ha="center", va="bottom", fontsize=7.8,
                        color=P.INK_2)
            ax.plot([val, val], [0.27, 0.33 + 0.27 * level], color=P.AXIS, lw=0.8, zorder=0)
        ax.set_yticks([])
        ax.set_ylim(-0.45, 1.35)
        ax.set_ylabel(f"{r['label']}\n({r['unit']})", rotation=0, ha="right", va="center", fontsize=9.5, color=P.INK_2)
        ax.grid(axis="y", visible=False)
        ax.text(1.0, 1.0, f"IQR {r['IQR']:,.3g} · Tukey outliers {int(r['n_outliers'])} of {int(r['n'])}",
                transform=ax.transAxes, ha="right", va="top", fontsize=8, color=P.MUTED)
    fig.tight_layout(h_pad=1.2)
    _title(fig, "Five-number summary of the key variables",
           "Box = Q1–Q3, white line = median, whiskers to 1.5×IQR; dots = every grade", y=1.04)
    P.source_note(fig)
    return fig


def distribution_grid(df: pd.DataFrame):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.6))
    for ax, var in zip(axes.ravel(), FIVE_VARS):
        s = df[var].dropna()
        sns.histplot(s, bins=40, kde=True, ax=ax, color=P.BLUE, edgecolor=P.SURFACE, linewidth=0.4, alpha=0.75,
                     line_kws={"linewidth": 2})
        ax.axvline(s.mean(), color=P.ORANGE, lw=1.6, label=f"mean {s.mean():,.3g}")
        ax.axvline(s.median(), color=P.INK, lw=1.6, label=f"median {s.median():,.3g}")
        label, unit = V.SUMMARY_VARS[var]
        ax.set_xlabel(f"{label} ({unit})")
        ax.set_ylabel("Grades")
        ax.set_title(f"{label}: skew {stats.skew(s):+.2f}", fontsize=11, pad=8)
        ax.legend(fontsize=8.5, loc="upper right")
    fig.tight_layout(h_pad=2.2, w_pad=1.6)
    _title(fig, "Distributions: histograms with kernel density", "Most variables are right-skewed: mean > median", y=1.06)
    P.source_note(fig)
    return fig


def ridgeline(df: pd.DataFrame):
    m = df.dropna(subset=[TS])
    order = m.groupby("family_label")[TS].median().sort_values().index.tolist()
    xs = np.linspace(0, 2600, 500)
    fig, ax = plt.subplots(figsize=(11, 9))
    meds = m.groupby("family_label")[TS].median()
    norm = plt.Normalize(meds.min(), meds.max())
    step = 1.0
    for i, fam in enumerate(order):
        s = m.loc[m["family_label"] == fam, TS].values
        if len(s) < 3:
            continue
        dens = stats.gaussian_kde(s, bw_method=0.35)(xs)
        dens = dens / dens.max() * 1.6
        base = i * step
        color = P.SEQ_ON_DARK(norm(meds[fam]))
        ax.fill_between(xs, base, base + dens, color=color, alpha=0.85, zorder=len(order) - i, linewidth=0)
        ax.plot(xs, base + dens, color=P.SURFACE, lw=1.2, zorder=len(order) - i)
        ax.text(-30, base + 0.15, f"{fam}  (n={len(s)})", ha="right", va="bottom", fontsize=9, color=P.INK_2)
        ax.plot([meds[fam]] * 2, [base, base + 0.25], color=P.INK, lw=1.5, zorder=50)
    ax.set_yticks([])
    ax.set_xlim(0, 2600)
    ax.set_xlabel("Tensile strength (MPa)")
    ax.grid(axis="y", visible=False)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=P.SEQ_ON_DARK)
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Family median TS (MPa)", color=P.INK_2)
    cb.outline.set_visible(False)
    ax.set_title("Ridgeline: strength distribution of every family")
    P.subtitle(ax, "Kernel density per family, sorted by median (white tick); colour = median")
    P.source_note(fig)
    return fig


def ecdf_by_group(df: pd.DataFrame):
    m = df.dropna(subset=[TS])
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    for grp in FAMILY_GROUP_ORDER:
        s = np.sort(m.loc[m["family_group"] == grp, TS].values)
        if len(s):
            ax.step(s, np.arange(1, len(s) + 1) / len(s), where="post", color=GROUP_COLOR[grp], lw=2,
                    label=f"{grp} (n={len(s)})")
    ax.axhline(0.5, color=P.AXIS, lw=1)
    ax.set_xlabel("Tensile strength (MPa)")
    ax.set_ylabel("Share of grades at or below")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(loc="lower right")
    ax.set_title("Empirical cumulative distribution by family group")
    P.subtitle(ax, "Read across at 50 % for each group's median; a curve further right = stronger group")
    P.source_note(fig)
    return fig


def violin_strip(df: pd.DataFrame):
    m = df.dropna(subset=[TS])
    order = m.groupby("family_group")[TS].median().sort_values().index.tolist()
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    sns.violinplot(data=m, x="family_group", y=TS, order=order, hue="family_group", hue_order=order, legend=False,
                   palette=GROUP_COLOR, inner=None, cut=0, linewidth=0, density_norm="width", ax=ax, saturation=0.9)
    for c in ax.collections:
        c.set_alpha(0.45)
    sns.stripplot(data=m, x="family_group", y=TS, order=order, color=P.INK_2, size=2.2, alpha=0.45, jitter=0.22, ax=ax)
    sns.boxplot(data=m, x="family_group", y=TS, order=order, width=0.12, showfliers=False, ax=ax,
                boxprops={"facecolor": P.SURFACE, "edgecolor": P.INK}, whiskerprops={"color": P.INK},
                capprops={"color": P.INK}, medianprops={"color": P.ORANGE, "linewidth": 2})
    ax.set_xlabel("")
    ax.set_ylabel("Tensile strength (MPa)")
    ax.tick_params(axis="x", labelcolor=P.INK_2)
    ax.set_title("Violin + strip + box: shape, spread and every grade at once")
    P.subtitle(ax, "Violin width = density; inner box = IQR with orange median")
    P.source_note(fig)
    return fig


# =============================================================================================
# B. Binning
# =============================================================================================
def binning_comparison(df: pd.DataFrame, comp: pd.DataFrame):
    ts = df[TS].dropna()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), sharey=True)
    for ax, method, color in zip(axes, ["equal width", "equal frequency (quantile)"], [P.BLUE, P.ORANGE]):
        c = comp[comp["method"] == method]
        widths = c["high"] - c["low"]
        ax.bar(c["low"], c["n"], width=widths, align="edge", color=color, alpha=0.85, edgecolor=P.SURFACE, linewidth=2)
        for _, r in c.iterrows():
            ax.text((r["low"] + r["high"]) / 2, r["n"] + 12, f"{r['n']}", ha="center", fontsize=9, color=P.INK)
        ax.set_xlabel("Tensile strength (MPa)")
        ax.set_title(f"{method.capitalize()}: 5 bins", fontsize=11.5)
        P.subtitle(ax, "Equal ranges, very unequal counts" if method == "equal width" else "Equal counts, very unequal ranges")
    axes[0].set_ylabel("Grades per bin")
    fig.tight_layout(w_pad=2)
    _title(fig, "Binning a skewed variable: equal width vs equal frequency",
           f"Same {len(ts)} measured grades, same number of bins", y=1.07)
    P.source_note(fig)
    return fig


def band_stacks(df: pd.DataFrame):
    b = V.add_bins(df)
    m = b.dropna(subset=[TS]).copy()
    m["strength_class_name"] = m["strength_class"].astype(int).map(V.CLASS_NAMES)
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.9))
    for ax, (band, title) in zip(axes, [("carbon_band", "Carbon band → family group"),
                                        ("alloy_band", "Alloy-content band → strength class")]):
        if band == "carbon_band":
            ct = pd.crosstab(b[band], b["family_group"], normalize="index").reindex(columns=FAMILY_GROUP_ORDER, fill_value=0)
            counts, colors = b[band].value_counts(), [GROUP_COLOR[c] for c in ct.columns]
        else:
            ct = pd.crosstab(m[band], m["strength_class_name"], normalize="index")[list(V.CLASS_NAMES.values())]
            counts, colors = m[band].value_counts(), [P.AQUA, P.BLUE, P.ORANGE]
        left = np.zeros(len(ct))
        y = np.arange(len(ct))[::-1]
        for col, color in zip(ct.columns, colors):
            vals = ct[col].values
            ax.barh(y, vals, left=left, color=color, height=0.6, edgecolor=P.SURFACE, linewidth=2, label=col)
            for yi, v, l in zip(y, vals, left):
                if v >= 0.08:
                    ax.text(l + v / 2, yi, f"{v:.0%}", ha="center", va="center", fontsize=8.5, color=P.INK)
            left += vals
        ax.set_yticks(y, [f"{i}\nn={counts.get(i, 0)}" for i in ct.index], fontsize=9)
        ax.tick_params(axis="y", labelcolor=P.INK_2)
        ax.set_xlim(0, 1)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.grid(False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=8.5)
        ax.set_title(title, fontsize=12)
    fig.tight_layout(w_pad=4)
    _title(fig, "Domain bins: metallurgical carbon bands and alloy-content bands",
           "Binning continuous chemistry into engineer-readable categories", y=1.07)
    P.source_note(fig)
    return fig


# =============================================================================================
# C. Chi-square
# =============================================================================================
def chi_square_panels(results: list, show: int = 3):
    fig, axes = plt.subplots(1, show, figsize=(15.5, 5.2), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    for ax, r in zip(axes, results[:show]):
        res = r.std_residuals
        vmax = max(4, float(np.nanmax(np.abs(res.values))))
        ax.imshow(res.values, cmap=P.DIVERGING, vmin=-vmax, vmax=vmax, aspect="auto")
        for i in range(res.shape[0]):
            for j in range(res.shape[1]):
                ax.text(j, i, f"{r.observed.iat[i, j]}\n({res.iat[i, j]:+.1f})", ha="center", va="center", fontsize=8,
                        color=P.INK)
        ax.set_xticks(range(res.shape[1]), [str(c) for c in res.columns], fontsize=8.5, rotation=15)
        ax.set_yticks(range(res.shape[0]), [str(i) for i in res.index], fontsize=8.5)
        ax.tick_params(axis="both", labelcolor=P.INK_2)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(r.name, fontsize=11, pad=34)
        P.subtitle(ax, f"χ²={r.chi2:,.0f}, df={r.dof}, Cramér's V={r.cramers_v:.2f}, perm. p={r.p_permutation:.4f}", offset=16)
    fig.tight_layout(w_pad=2.5)
    _title(fig, "Chi-square tests of independence: where the counts deviate",
           "Cell = observed count (standardized residual). Red = more grades than independence predicts, blue = fewer",
           y=1.1)
    P.source_note(fig)
    return fig


def cramers_lollipop(results: list):
    t = pd.DataFrame([r.as_row() for r in results]).sort_values("cramers_v")
    fig, ax = plt.subplots(figsize=(10.5, 4))
    y = np.arange(len(t))
    ax.hlines(y, 0, t["cramers_v"], color=P.AXIS, lw=3)
    ax.scatter(t["cramers_v"], y, s=120, color=P.ORANGE, zorder=3)
    for yi, (v, p, ok) in enumerate(zip(t["cramers_v"], t["p_permutation"], t["asymptotic_valid"])):
        flag = "" if ok else "  · sparse cells: rely on permutation p"
        ax.text(v + 0.02, yi, f"V={v:.2f} · perm. p={p:.4f}{flag}", va="center", fontsize=8.8, color=P.INK_2)
    ax.set_yticks(y, t["test"])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 1.25)
    ax.set_xlabel("Cramér's V (0 = independent, 1 = perfectly associated)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Strength of association across all chi-square tests")
    P.subtitle(ax, "Every association is significant; Cramér's V shows how strong it is")
    P.source_note(fig)
    return fig


# =============================================================================================
# D. Correlation and regression
# =============================================================================================
def correlation_clustermap(df: pd.DataFrame):
    cols = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu", "N", "Nb", "Ti", "Al", "P", "S",
            "carbon_equivalent", "alloying_total", TS, "liquidus_c"]
    corr = df[cols].corr(method="spearman").rename(index={TS: "TS", "liquidus_c": "Liquidus", "carbon_equivalent": "CE",
                                                          "alloying_total": "Alloy total"},
                                                   columns={TS: "TS", "liquidus_c": "Liquidus", "carbon_equivalent": "CE",
                                                            "alloying_total": "Alloy total"})
    g = sns.clustermap(corr, cmap=P.DIVERGING, vmin=-1, vmax=1, figsize=(11, 10), linewidths=0.6, linecolor=P.SURFACE,
                       annot=True, fmt=".1f", annot_kws={"fontsize": 7, "color": P.INK}, dendrogram_ratio=0.12,
                       cbar_pos=(0.02, 0.83, 0.025, 0.14), tree_kws={"colors": P.MUTED})
    g.ax_heatmap.tick_params(colors=P.INK_2, labelsize=9)
    g.ax_cbar.tick_params(colors=P.MUTED)
    g.figure.suptitle("Spearman correlation clustermap: elements that travel together",
                      x=0.01, ha="left", y=1.02, fontsize=14, fontweight="semibold", color=P.INK)
    g.figure.text(0.01, 0.995, "Hierarchical clustering reorders rows and columns so correlated blocks sit together",
                  ha="left", va="top", fontsize=10, color=P.INK_2)
    return g.figure


def simple_regression(reg: dict):
    c, res = reg["carbon"], reg["simple"]
    grid = np.linspace(0, c["C"].max(), 100)
    band = V.simple_regression_bands(res, grid)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    ax.fill_between(band["x"], band["pi_low"], band["pi_high"], color=to_rgba(P.BLUE, 0.12), label="95 % prediction band")
    ax.fill_between(band["x"], band["ci_low"], band["ci_high"], color=to_rgba(P.BLUE, 0.35), label="95 % confidence band")
    ax.scatter(c["C"], c[TS], s=20, color=P.BLUE, linewidths=0.4, zorder=3, label=f"Carbon steels (n={res.n})")
    ax.plot(band["x"], band["fit"], color=P.ORANGE, lw=2.2, zorder=4,
            label=f"TS = {res.coef[0]:.0f} + {res.coef[1]:.0f}·C")
    ax.set_xlabel("Carbon (wt%)")
    ax.set_ylabel("Tensile strength (MPa)")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title(f"Simple linear regression: R² = {res.r2:.2f}, p = {res.p[1]:.1e}")
    P.subtitle(ax, f"+{res.coef[1] / 10:.0f} MPa per 0.1 % C (95 % CI {res.ci_low[1] / 10:.0f} to {res.ci_high[1] / 10:.0f})")
    ax = axes[1]
    ax.scatter(res.fitted, res.resid, s=16, color=P.BLUE, linewidths=0.3)
    ax.axhline(0, color=P.AXIS, lw=1.2)
    ax.set_xlabel("Fitted TS (MPa)")
    ax.set_ylabel("Residual (MPa)")
    ax.set_title("Residuals vs fitted")
    P.subtitle(ax, f"Residual SD {res.sigma:.0f} MPa; spread widens with strength")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def multiple_regression(reg: dict):
    res, std = reg["multi"], reg["std_multi"]
    t = std.table().drop("Intercept").sort_values("coef")
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5), gridspec_kw={"width_ratios": [1.2, 1, 1]})
    ax = axes[0]
    y = np.arange(len(t))
    sig = t["p_value"] < 0.05
    ax.hlines(y, t["ci95_low"], t["ci95_high"], color=P.MUTED, lw=2)
    ax.scatter(t["coef"][sig], y[sig.values], color=P.ORANGE, s=70, zorder=3, label="p < 0.05")
    ax.scatter(t["coef"][~sig], y[~sig.values], facecolors=P.SURFACE, edgecolors=P.MUTED, s=70, zorder=3, label="not significant")
    ax.axvline(0, color=P.AXIS, lw=1.2)
    raw = res.table()
    ax.set_yticks(y, [f"{e}  ({raw.loc[e, 'coef']:+.0f} MPa/wt%)" for e in t.index])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlabel("Standardized coefficient β (95 % CI)")
    ax.legend(loc="lower right", fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Multiple regression, carbon & low-alloy steels (n={res.n})", fontsize=11.5)
    P.subtitle(ax, f"R² = {res.r2:.2f}, adj. R² = {res.adj_r2:.2f}, F = {res.f_stat:.1f} (p = {res.f_p:.1e})")
    ax = axes[1]
    ax.scatter(res.fitted, res.resid, s=12, color=P.BLUE, linewidths=0)
    ax.axhline(0, color=P.AXIS, lw=1.2)
    ax.set_xlabel("Fitted TS (MPa)")
    ax.set_ylabel("Residual (MPa)")
    ax.set_title("Residuals vs fitted", fontsize=11.5)
    P.subtitle(ax, "High-strength spring/maraging-type outliers above")
    ax = axes[2]
    (osm, osr), (slope, intercept, _) = stats.probplot(res.resid, dist="norm")
    ax.scatter(osm, osr, s=12, color=P.BLUE, linewidths=0)
    ax.plot(osm, slope * np.asarray(osm) + intercept, color=P.ORANGE, lw=1.8)
    ax.set_xlabel("Theoretical normal quantile")
    ax.set_ylabel("Ordered residual (MPa)")
    ax.set_title("Normal Q-Q plot", fontsize=11.5)
    P.subtitle(ax, "Heavy right tail: residuals are not normal")
    fig.tight_layout(w_pad=2.5)
    P.source_note(fig)
    return fig


def joint_hex(df: pd.DataFrame):
    plain = df[df["family_group"] == "Carbon & low-alloy"].dropna(subset=[TS])
    plain = plain[plain["carbon_equivalent"] <= 1.6]
    g = sns.jointplot(data=plain, x="carbon_equivalent", y=TS, kind="hex", height=7.5, ratio=4,
                      joint_kws={"gridsize": 28, "cmap": P.SEQ_ON_DARK, "mincnt": 1, "edgecolors": P.SURFACE},
                      marginal_kws={"color": P.BLUE, "edgecolor": P.SURFACE, "bins": 30})
    g.set_axis_labels("Carbon equivalent, IIW (wt%)", "Tensile strength (MPa)")
    rho = stats.spearmanr(plain["carbon_equivalent"], plain[TS])[0]
    g.figure.suptitle(f"Hexbin joint plot: CE vs strength in carbon & low-alloy steels (ρ = {rho:.2f})",
                      x=0.01, ha="left", y=1.02, fontsize=13, fontweight="semibold", color=P.INK)
    return g.figure


def pairplot(df: pd.DataFrame):
    m = df.dropna(subset=[TS])
    m = m[m["family_group"].isin(SCATTER_GROUPS)]
    cols = [TS, "carbon_equivalent", "C", "Cr", "Ni"]
    d = m[cols + ["family_group"]].rename(columns={TS: "TS (MPa)", "carbon_equivalent": "CE"})
    g = sns.pairplot(d, hue="family_group", hue_order=SCATTER_GROUPS, palette=SCATTER_COLOR, corner=True, height=2.3,
                     plot_kws={"s": 10, "linewidth": 0, "alpha": 0.7}, diag_kind="kde", diag_kws={"fill": True, "alpha": 0.35})
    g.figure.suptitle("Pair plot of strength and key chemistry for the three largest groups",
                      x=0.01, ha="left", y=1.02, fontsize=13, fontweight="semibold", color=P.INK)
    return g.figure


# =============================================================================================
# E. PCA
# =============================================================================================
def pca_scree(pca: dict):
    ev = pca["explained"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    ax = axes[0]
    x = np.arange(1, len(ev) + 1)
    ax.bar(x, ev["explained_variance_ratio"] * 100, color=P.BLUE, edgecolor=P.SURFACE, linewidth=2, label="Each component")
    ax.plot(x, ev["cumulative"] * 100, color=P.ORANGE, marker="o", ms=4, label="Cumulative")
    ax.axhline(80, color=P.AXIS, lw=1)
    ax.text(len(ev), 81.5, "80 %", ha="right", fontsize=8.5, color=P.MUTED)
    ax.set_xlabel("Principal component")
    ax.set_ylabel("Variance explained (%)")
    ax.legend(loc="center right")
    ax.set_title(f"Scree plot: {pca['n_for_80pct']} components reach 80 %", fontsize=11.5)
    P.subtitle(ax, f"Kaiser rule (eigenvalue > 1) keeps {pca['n_kaiser']}: chemistry is genuinely high-dimensional")
    ax = axes[1]
    L = pca["loadings"].iloc[:, :5]
    order = L["PC1"].abs().sort_values(ascending=False).index
    L = L.loc[order]
    ax.imshow(L.values, cmap=P.DIVERGING, vmin=-1, vmax=1, aspect="auto")
    for i in range(L.shape[0]):
        for j in range(L.shape[1]):
            if abs(L.iat[i, j]) >= 0.4:
                ax.text(j, i, f"{L.iat[i, j]:+.2f}", ha="center", va="center", fontsize=7.5, color=P.INK)
    ax.set_xticks(range(5), L.columns)
    ax.set_yticks(range(len(L)), L.index, fontsize=8)
    ax.tick_params(axis="both", labelcolor=P.INK_2)
    ax.grid(False)
    ax.set_title("Loadings (correlation of element with PC)", fontsize=11.5)
    P.subtitle(ax, "Values shown where |loading| ≥ 0.4")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def pca_biplot(df: pd.DataFrame, pca: dict, n_arrows: int = 8):
    sc = pca["scores"]
    L = pca["loadings"][["PC1", "PC2"]]
    ev = pca["explained"]["explained_variance_ratio"]
    fig, ax = plt.subplots(figsize=(11, 8))
    grp = df["family_group"].to_numpy()
    other = ~np.isin(grp, SCATTER_GROUPS)
    ax.scatter(sc[other, 0], sc[other, 1], s=10, color=P.OTHER, linewidths=0, label="Other groups")
    for gname in SCATTER_GROUPS:
        msk = grp == gname
        ax.scatter(sc[msk, 0], sc[msk, 1], s=13, color=SCATTER_COLOR[gname], linewidths=0.2, label=gname, alpha=0.85)
    top = L.pow(2).sum(axis=1).sort_values(ascending=False).head(n_arrows).index
    scale = np.abs(sc[:, :2]).max() / np.abs(L.loc[top].values).max() * 0.55
    for el in top:
        x, y = L.loc[el] * scale
        ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops={"arrowstyle": "-|>", "color": P.INK, "lw": 1.4})
        ax.text(x * 1.08, y * 1.08, el, color=P.INK, fontsize=10, fontweight="semibold", ha="center", va="center")
    ax.axhline(0, color=P.AXIS, lw=1)
    ax.axvline(0, color=P.AXIS, lw=1)
    ax.set_xlabel(f"PC1 ({ev.iloc[0]:.1%} of variance)")
    ax.set_ylabel(f"PC2 ({ev.iloc[1]:.1%} of variance)")
    ax.legend(loc="upper right")
    ax.set_title("PCA biplot: grades (dots) and element loadings (arrows)")
    P.subtitle(ax, "Arrows point to where an element is high; stainless and cast iron pull away from plain steels")
    P.source_note(fig)
    return fig


# =============================================================================================
# F. K-means
# =============================================================================================
def kmeans_elbow(scan: pd.DataFrame, k: int):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    for ax, col, color, title in [(axes[0], "inertia", P.BLUE, "Elbow: within-cluster sum of squares"),
                                  (axes[1], "silhouette", P.ORANGE, "Silhouette score (higher = better separated)")]:
        ax.plot(scan.index, scan[col], marker="o", color=color, ms=6)
        ax.scatter([k], [scan.loc[k, col]], s=150, facecolors="none", edgecolors=P.INK, lw=1.8, zorder=3)
        ax.set_xlabel("Number of clusters k")
        ax.set_title(title, fontsize=11.5)
        ax.set_xticks(scan.index)
    axes[0].set_ylabel("Inertia")
    axes[1].set_ylabel("Mean silhouette")
    P.subtitle(axes[0], f"Ringed: k = {k}, chosen as best silhouette within 4–8 (one colour/panel per cluster)")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def silhouette_plot(X: np.ndarray, labels: np.ndarray, names: dict):
    sil = silhouette_samples(X, labels)
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    y0 = 0
    for c in sorted(set(labels)):
        v = np.sort(sil[labels == c])
        ax.fill_betweenx(np.arange(y0, y0 + len(v)), 0, v, color=P.SERIES[c % 8], alpha=0.85, linewidth=0)
        ax.text(-0.02, y0 + len(v) / 2, names[c], ha="right", va="center", fontsize=8.5, color=P.INK_2)
        y0 += len(v) + 12
    ax.axvline(sil.mean(), color=P.INK, lw=1.4)
    ax.text(sil.mean() + 0.01, y0 * 0.98, f"mean {sil.mean():.2f}", fontsize=9, color=P.INK)
    ax.set_yticks([])
    ax.set_xlim(-0.4, 1)
    ax.set_xlabel("Silhouette coefficient per grade")
    ax.grid(axis="y", visible=False)
    ax.set_title("Silhouette profile of each k-means cluster")
    P.subtitle(ax, "Wide, mostly-positive blades = coherent clusters; negative values = grades closer to another cluster")
    P.source_note(fig)
    return fig


def kmeans_small_multiples(sc: np.ndarray, labels: np.ndarray, names: dict):
    k = len(names)
    cols = 4
    rows = int(np.ceil(k / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(14.5, 3.6 * rows), sharex=True, sharey=True)
    for ax, c in zip(axes.ravel(), sorted(names)):
        on = labels == c
        ax.scatter(sc[~on, 0], sc[~on, 1], s=4, color=P.OTHER, linewidths=0, alpha=0.5)
        ax.scatter(sc[on, 0], sc[on, 1], s=8, color=P.BLUE, linewidths=0)
        ax.set_title(f"{names[c]}  n={on.sum()}", fontsize=9.5)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[k:]:
        ax.axis("off")
    fig.tight_layout()
    _title(fig, "K-means clusters on the PCA plane, one panel per cluster",
           "Blue = cluster members, grey = all other grades (PC1 × PC2)", y=1.05)
    P.source_note(fig)
    return fig


def cluster_heatmap(df: pd.DataFrame, labels: np.ndarray, names: dict, X: np.ndarray, feats: list[str]):
    z = pd.DataFrame(X, columns=feats).groupby(labels).mean()
    z.index = [names[i] for i in z.index]
    z = z[[f for f in feats if f != "trace_total"]]
    ts = df.assign(_c=labels).groupby("_c")[TS].median()
    fig, ax = plt.subplots(figsize=(14, 5.2))
    ax.imshow(z.values, cmap=P.DIVERGING, vmin=-2.5, vmax=2.5, aspect="auto")
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            if abs(z.iat[i, j]) >= 1:
                ax.text(j, i, f"{z.iat[i, j]:+.1f}", ha="center", va="center", fontsize=7.5, color=P.INK)
    ax.set_xticks(range(z.shape[1]), z.columns, fontsize=9)
    ax.set_yticks(range(z.shape[0]), [f"{n}  · median TS {ts.iloc[i]:.0f}" for i, n in enumerate(z.index)], fontsize=8.5)
    ax.tick_params(axis="both", labelcolor=P.INK_2)
    ax.grid(False)
    ax.set_title("Cluster fingerprints: mean standardized log-composition")
    P.subtitle(ax, "Red = element well above the dataset average for that cluster; values shown where |z| ≥ 1")
    P.source_note(fig)
    return fig


# =============================================================================================
# G. Circular migration (chord) plot
# =============================================================================================
def _arc(a0: float, a1: float, r: float = 1.0, n: int = 24) -> np.ndarray:
    t = np.radians(np.linspace(a0, a1, max(2, n)))
    return np.column_stack([r * np.cos(t), r * np.sin(t)])


def _bezier(p0, p1, p2, p3, n: int = 30) -> np.ndarray:
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def chord_geometry(flows: pd.DataFrame, sources: list[str], targets: list[str], gap: float = 2.0,
                   split_gap: float = 14.0, r: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Circular-migration-plot layout. Sources occupy the left half of the circle, targets the right half;
    each ribbon's width at both ends is proportional to its flow. Returns (arcs, ribbon polygons)."""
    out_tot = flows.groupby("source")["value"].sum().reindex(sources).fillna(0)
    in_tot = flows.groupby("target")["value"].sum().reindex(targets).fillna(0)
    total = flows["value"].sum()
    avail = 180 - split_gap - gap * (max(len(sources), len(targets)) - 1)
    deg_per = avail / total
    arcs = []
    a = 90 + split_gap / 2                                    # sources: counter-clockwise from the top-left
    for s in sources:
        span = out_tot[s] * deg_per
        arcs.append({"node": s, "side": "source", "a0": a, "a1": a + span, "value": out_tot[s]})
        a += span + gap
    a = 90 - split_gap / 2                                    # targets: clockwise from the top-right
    for t in targets:
        span = in_tot[t] * deg_per
        arcs.append({"node": t, "side": "target", "a0": a - span, "a1": a, "value": in_tot[t]})
        a -= span + gap
    arcs = pd.DataFrame(arcs)
    pos = {(row.side, row.node): row for row in arcs.itertuples()}
    s_cursor = {s: pos[("source", s)].a0 for s in sources}
    t_cursor = {t: pos[("target", t)].a1 for t in targets}
    ribbons = []
    order_t = {t: i for i, t in enumerate(targets)}
    order_s = {s: i for i, s in enumerate(sources)}
    f = flows.copy()
    f["_ot"], f["_os"] = f["target"].map(order_t), f["source"].map(order_s)
    for rid, row in enumerate(f.sort_values(["_os", "_ot"]).itertuples()):
        span = row.value * deg_per
        sa0, sa1 = s_cursor[row.source], s_cursor[row.source] + span
        s_cursor[row.source] = sa1
        ta1, ta0 = t_cursor[row.target], t_cursor[row.target] - span
        t_cursor[row.target] = ta0
        src = _arc(sa0, sa1, r)
        tgt = _arc(ta1, ta0, r)
        c1 = _bezier(src[-1], src[-1] * 0.25, tgt[0] * 0.25, tgt[0])
        c2 = _bezier(tgt[-1], tgt[-1] * 0.25, src[0] * 0.25, src[0])
        poly = np.vstack([src, c1, tgt, c2])
        for k, (x, y) in enumerate(poly):
            ribbons.append({"ribbon_id": rid, "source": row.source, "target": row.target, "value": row.value,
                            "point_order": k, "x": x, "y": y})
    return arcs, pd.DataFrame(ribbons)


def circular_migration(flows: pd.DataFrame, sources: list[str], targets: list[str], source_colors: dict,
                       title: str, subtitle: str, min_label_share: float = 0.012):
    arcs, rib = chord_geometry(flows, sources, targets)
    total = flows["value"].sum()
    fig, ax = plt.subplots(figsize=(12.5, 11))
    for rid, poly in rib.groupby("ribbon_id"):
        src = poly["source"].iloc[0]
        ax.add_patch(PathPatch(Path(poly[["x", "y"]].to_numpy()), facecolor=to_rgba(source_colors[src], 0.55),
                               edgecolor=to_rgba(source_colors[src], 0.9), lw=0.4))
    for a in arcs.itertuples():
        color = source_colors.get(a.node, P.MUTED) if a.side == "source" else P.INK_2
        ax.add_patch(Wedge((0, 0), 1.09, a.a0, a.a1, width=0.07, facecolor=color, edgecolor=P.SURFACE, lw=1))
        mid = np.radians((a.a0 + a.a1) / 2)
        if a.value / total < min_label_share:
            continue
        x, y = 1.14 * np.cos(mid), 1.14 * np.sin(mid)
        deg = np.degrees(mid)
        left = 90 < deg % 360 < 270
        ax.text(x, y, f"{a.node}\n{int(a.value):,}", ha="right" if left else "left", va="center",
                rotation=deg + 180 if left else deg, rotation_mode="anchor", fontsize=9, color=P.INK)
    ax.text(-1.0, 1.32, "FROM", fontsize=10, color=P.MUTED, fontweight="semibold", ha="center")
    ax.text(1.0, 1.32, "TO", fontsize=10, color=P.MUTED, fontweight="semibold", ha="center")
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.55, 1.45)
    ax.set_aspect("equal")
    _clean_axis(ax)
    ax.set_title(title, fontsize=14)
    P.subtitle(ax, subtitle)
    P.source_note(fig)
    return fig


# =============================================================================================
# H. Ring / donut, circular columns, treemap
# =============================================================================================
def _shade(color: str, i: int, n: int) -> tuple:
    base = np.array(to_rgba(color))
    t = 0.25 + 0.75 * (i / max(n - 1, 1))
    return tuple(np.clip(base[:3] * (0.55 + 0.6 * t), 0, 1)) + (1.0,)


def ring_chart(df: pd.DataFrame):
    inner = df["family_group"].value_counts().reindex(FAMILY_GROUP_ORDER).dropna()
    fig, ax = plt.subplots(figsize=(11, 11))
    outer_vals, outer_cols, outer_lab = [], [], []
    for g in inner.index:
        fams = df.loc[df["family_group"] == g, "family_label"].value_counts()
        for i, (f, n) in enumerate(fams.items()):
            outer_vals.append(n)
            outer_cols.append(_shade(GROUP_COLOR[g], i, len(fams)))
            outer_lab.append(f if n / len(df) > 0.015 else "")
    ax.pie(inner.values, radius=0.68, colors=[GROUP_COLOR[g] for g in inner.index], startangle=90, counterclock=False,
           wedgeprops={"width": 0.26, "edgecolor": P.SURFACE, "linewidth": 2.5},
           labels=[f"{g}\n{int(n)}" if n / inner.sum() > 0.08 else "" for g, n in inner.items()], labeldistance=0.62,
           textprops={"fontsize": 9.5, "color": P.INK, "ha": "center"})
    ax.legend(handles=[Patch(color=GROUP_COLOR[gname], label=f"{gname} ({int(n)})") for gname, n in inner.items()],
              loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=9.5)
    wedges, _ = ax.pie(outer_vals, radius=1.0, colors=outer_cols, startangle=90, counterclock=False,
                       wedgeprops={"width": 0.28, "edgecolor": P.SURFACE, "linewidth": 1.5})
    for w, lab, n in zip(wedges, outer_lab, outer_vals):
        if not lab:
            continue
        ang = np.radians((w.theta1 + w.theta2) / 2)
        x, y = 1.06 * np.cos(ang), 1.06 * np.sin(ang)
        ax.text(x, y, f"{lab} ({n})", ha="left" if x > 0 else "right", va="center", fontsize=8.6, color=P.INK_2)
    ax.text(0, 0, f"{len(df):,}\ngrades", ha="center", va="center", fontsize=17, fontweight="semibold", color=P.INK)
    ax.set_title("Ring diagram: family groups (inner) and families (outer)", fontsize=14)
    P.subtitle(ax, "Two-level donut / sunburst; arc length = number of grades")
    P.source_note(fig)
    return fig


def radial_bar_geometry(values: pd.Series, inner: float = 0.35, max_len: float = 0.6, gap_frac: float = 0.15,
                        n: int = 12) -> pd.DataFrame:
    """Polygons for a circular column chart (bars radiate from an inner circle), clockwise from the top."""
    k = len(values)
    width = 360 / k
    vmax = values.max()
    rows = []
    for i, (label, v) in enumerate(values.items()):
        a_mid = 90 - i * width
        a0, a1 = a_mid - width * (1 - gap_frac) / 2, a_mid + width * (1 - gap_frac) / 2
        r1 = inner + max_len * v / vmax
        pts = np.vstack([_arc(a0, a1, inner, n), _arc(a1, a0, r1, n)])
        for j, (x, y) in enumerate(pts):
            rows.append({"bar": label, "value": v, "angle_mid": a_mid, "point_order": j, "x": x, "y": y})
    return pd.DataFrame(rows)


def circular_columns(values: pd.Series, colors: list, title: str, subtitle: str, unit: str, center: str):
    geo = radial_bar_geometry(values)
    fig, ax = plt.subplots(figsize=(11.5, 11.5))
    for (label, poly), color in zip(geo.groupby("bar", sort=False), colors):
        ax.add_patch(PathPatch(Path(poly[["x", "y"]].to_numpy()), facecolor=color, edgecolor=P.SURFACE, lw=1))
        a = np.radians(poly["angle_mid"].iloc[0])
        v = poly["value"].iloc[0]
        r = 0.35 + 0.6 * v / values.max() + 0.03
        deg = np.degrees(a) % 360
        flip = 90 < deg < 270
        ax.text(r * np.cos(a), r * np.sin(a), f"{label}  {v:,.0f}{unit}" if not flip else f"{v:,.0f}{unit}  {label}",
                rotation=deg + 180 if flip else deg, rotation_mode="anchor", ha="right" if flip else "left",
                va="center", fontsize=8.6, color=P.INK_2)
    for frac in (0.25, 0.5, 0.75, 1.0):
        ax.add_patch(plt.Circle((0, 0), 0.35 + 0.6 * frac, fill=False, color=P.GRID, lw=0.8, zorder=0))
    ax.text(0, 0, center, ha="center", va="center", fontsize=12, color=P.INK, fontweight="semibold")
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    _clean_axis(ax)
    ax.set_title(title, fontsize=14)
    P.subtitle(ax, subtitle)
    P.source_note(fig)
    return fig


def treemap(df: pd.DataFrame, W: float = 100, H: float = 62):
    m = df.copy()
    grp_n = m["family_group"].value_counts().reindex(FAMILY_GROUP_ORDER).dropna()
    fam = m.groupby(["family_group", "family_label"]).agg(n=("grade_id", "size"), med=(TS, "median")).reset_index()
    norm = plt.Normalize(fam["med"].min(), 1100)   # capped so one ~1800 MPa family does not flatten the scale
    fig, ax = plt.subplots(figsize=(15, 9.3))
    rects = squarify.squarify(squarify.normalize_sizes(grp_n.values.tolist(), W, H), 0, 0, W, H)
    for g, r in zip(grp_n.index, rects):
        sub = fam[fam["family_group"] == g].sort_values("n", ascending=False)
        pad = 0.45
        inner = squarify.squarify(squarify.normalize_sizes(sub["n"].tolist(), r["dx"] - 2 * pad, r["dy"] - 2 * pad - 2.4),
                                  r["x"] + pad, r["y"] + pad, r["dx"] - 2 * pad, r["dy"] - 2 * pad - 2.4)
        ax.add_patch(plt.Rectangle((r["x"], r["y"]), r["dx"], r["dy"], facecolor=P.SURFACE, edgecolor=GROUP_COLOR[g], lw=2.5))
        ax.text(r["x"] + 0.8, r["y"] + r["dy"] - 1.3, f"{g.upper()}  ·  {int(grp_n[g])}", fontsize=9.5,
                fontweight="semibold", color=GROUP_COLOR[g], va="center")
        for (_, f), ir in zip(sub.iterrows(), inner):
            color = P.SEQ_ON_DARK(norm(f["med"])) if pd.notna(f["med"]) else P.OTHER
            ax.add_patch(plt.Rectangle((ir["x"], ir["y"]), ir["dx"], ir["dy"], facecolor=color, edgecolor=P.SURFACE, lw=1.6))
            ink = P.SURFACE if norm(f["med"]) > 0.6 else P.INK
            if ir["dx"] > 7 and ir["dy"] > 4:
                ax.text(ir["x"] + 0.6, ir["y"] + ir["dy"] - 0.6, f"{f['family_label']}\n{f['n']} grades\nmedian {f['med']:.0f} MPa",
                        fontsize=8.2, va="top", color=ink)
            elif ir["dx"] > 3.2 and ir["dy"] > 3:
                short = (f["family_label"].replace(" steel", "").replace(" cast iron", " iron")
                         .replace("Fe-Ni/Co special alloy", "Fe-Ni/Co").replace("Austenitic (Ni-Resist)", "Ni-Resist"))
                ax.text(ir["x"] + 0.4, ir["y"] + ir["dy"] - 0.4, f"{short}\n{f['n']} · {f['med']:.0f}", fontsize=6.8,
                        va="top", color=ink)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    _clean_axis(ax)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=P.SEQ_ON_DARK)
    cb = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.01, extend="max")
    cb.set_label("Family median tensile strength (MPa)", color=P.INK_2)
    cb.outline.set_visible(False)
    ax.set_title("Treemap: area = number of grades, colour = median strength")
    P.subtitle(ax, "Outer frames = family groups; tiles = families (small tiles: name, grades · median MPa)")
    P.source_note(fig)
    return fig


# =============================================================================================
# I. Radar charts
# =============================================================================================
def radar_geometry(table: pd.DataFrame, scale_max: float) -> pd.DataFrame:
    """Closed polygon (x, y) per row of `table` (rows = entities, columns = radar axes), clockwise from top."""
    axes_ = list(table.columns)
    ang = np.radians(90 - np.arange(len(axes_)) * 360 / len(axes_))
    rows = []
    for ent, r in table.iterrows():
        vals = r.fillna(0).to_numpy(float) / scale_max
        for i in range(len(axes_) + 1):
            j = i % len(axes_)
            rows.append({"entity": ent, "axis": axes_[j], "point_order": i, "value": r.iloc[j], "scaled": vals[j],
                         "angle_deg": float(np.degrees(ang[j])), "x": vals[j] * np.cos(ang[j]), "y": vals[j] * np.sin(ang[j])})
    return pd.DataFrame(rows)


def _radar_axes(ax, labels, rings=(0.25, 0.5, 0.75, 1.0), ring_labels=None):
    n = len(labels)
    ang = np.radians(90 - np.arange(n) * 360 / n)
    for r in rings:
        pts = np.column_stack([r * np.cos(ang), r * np.sin(ang)])
        ax.add_patch(plt.Polygon(pts, closed=True, fill=False, edgecolor=P.GRID, lw=0.9))
    for a, lab in zip(ang, labels):
        ax.plot([0, np.cos(a)], [0, np.sin(a)], color=P.GRID, lw=0.9)
        ax.text(1.17 * np.cos(a), 1.17 * np.sin(a), lab, ha="center", va="center", fontsize=8.6, color=P.INK_2)
    if ring_labels:
        for r, t in zip(rings, ring_labels):
            ax.text(0.02, r + 0.02, t, fontsize=7, color=P.MUTED)
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.3, 1.35)
    ax.set_aspect("equal")
    _clean_axis(ax)


def _radar_poly(ax, geo_ent: pd.DataFrame, color, alpha=0.32, lw=2.0, label=None):
    ax.fill(geo_ent["x"], geo_ent["y"], color=to_rgba(color, alpha), zorder=2)
    ax.plot(geo_ent["x"], geo_ent["y"], color=color, lw=lw, zorder=3, label=label)
    ax.scatter(geo_ent["x"].iloc[:-1], geo_ent["y"].iloc[:-1], s=14, color=color, zorder=4)


def radar_small_multiples(table: pd.DataFrame, colors: dict | str, title: str, subtitle: str, scale_max: float = 1.0,
                          reference: pd.Series | None = None, ref_label: str = "", ring_labels=None, cols: int = 3):
    geo = radar_geometry(table, scale_max)
    ref_geo = radar_geometry(reference.to_frame().T, scale_max) if reference is not None else None
    n = len(table)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 4.6 * rows))
    for ax, ent in zip(np.atleast_1d(axes).ravel(), table.index):
        _radar_axes(ax, list(table.columns), ring_labels=ring_labels)
        if ref_geo is not None:
            ax.plot(ref_geo["x"], ref_geo["y"], color=P.MUTED, lw=1.2, zorder=2)
        color = colors[ent] if isinstance(colors, dict) else colors
        _radar_poly(ax, geo[geo["entity"] == ent], color)
        ax.set_title(ent, fontsize=11.5, pad=6, loc="center")
    for ax in np.atleast_1d(axes).ravel()[n:]:
        ax.axis("off")
    fig.tight_layout(h_pad=1.5)
    sub = subtitle + (f"  ·  grey outline = {ref_label}" if reference is not None else "")
    _title(fig, title, sub, y=1.05)
    P.source_note(fig)
    return fig


def radar_overlay(table: pd.DataFrame, colors: list, title: str, subtitle: str, ring_labels=None):
    geo = radar_geometry(table, 100.0)
    fig, ax = plt.subplots(figsize=(9, 8.6))
    _radar_axes(ax, list(table.columns), ring_labels=ring_labels)
    for ent, color in zip(table.index, colors):
        _radar_poly(ax, geo[geo["entity"] == ent], color, alpha=0.18, lw=2.4, label=ent)
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.05))
    ax.set_title(title, fontsize=13.5, loc="left")
    P.subtitle(ax, subtitle)
    P.source_note(fig)
    return fig


# =============================================================================================
# J. Waterfall
# =============================================================================================
def waterfall(wf: pd.DataFrame, title: str, subtitle: str, unit: str = "", fmt: str = "{:,.0f}", xlabel_rot: int = 0,
              zero_based: bool = True):
    """Waterfall chart. zero_based=False starts the axis just below the data so small steps on a large total stay
    visible; the subtitle then states where the axis starts (a non-zero baseline must always be declared)."""
    lay = V.waterfall_layout(wf)
    vals = lay[["start", "end"]].to_numpy()
    if zero_based:
        floor = 0.0
    else:
        deltas = lay[lay["kind"] == "delta"][["start", "end"]].to_numpy()
        span = vals.max() - deltas.min()
        floor = float(np.floor((deltas.min() - 0.6 * span) / 10) * 10)
        subtitle = f"{subtitle}  ·  axis starts at {floor:,.0f}{unit}"
    fig, ax = plt.subplots(figsize=(max(9, 1.35 * len(lay)), 5.6))
    x = np.arange(len(lay))
    pad = (vals.max() - floor) * 0.015
    for i, r in lay.iterrows():
        lo, hi = sorted([r["start"], r["end"]])
        if r["kind"] == "total":
            lo, color = floor, P.BLUE
        else:
            color = P.AQUA if r["value"] >= 0 else P.ORANGE
        ax.bar(i, hi - lo, bottom=lo, width=0.62, color=color, edgecolor=P.SURFACE, linewidth=1.5)
        label = fmt.format(r["value"]) if r["kind"] == "total" else ("+" if r["value"] >= 0 else "−") + fmt.format(abs(r["value"]))
        ax.text(i, hi + pad, f"{label}{unit}", ha="center", va="bottom", fontsize=9.5, color=P.INK)
        if i < len(lay) - 1:
            ax.plot([i + 0.31, i + 0.69], [r["end"]] * 2, color=P.MUTED, lw=1)
    ax.set_ylim(floor, vals.max() + (vals.max() - floor) * 0.12)
    ax.set_xticks(x, lay["step"], rotation=xlabel_rot, ha="right" if xlabel_rot else "center")
    ax.tick_params(axis="x", labelcolor=P.INK_2)
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[Patch(color=P.BLUE, label="Total"), Patch(color=P.AQUA, label="Increase"),
                       Patch(color=P.ORANGE, label="Decrease")], loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.set_title(title)
    P.subtitle(ax, subtitle)
    if xlabel_rot:   # rotated labels hang lower: push the source line below them
        fig.text(0.01, -0.2, "Source: data/raw/Alloys.csv · SteelScope analysis", ha="left", va="top", fontsize=8, color=P.MUTED)
    else:
        P.source_note(fig)
    return fig


# =============================================================================================
# K. Parallel coordinates
# =============================================================================================
def parallel_coordinates(df: pd.DataFrame):
    cols = [TS, "liquidus_c", "carbon_equivalent", "alloying_total", "C", "Cr", "Ni", "Mo"]
    labels = ["TS", "Liquidus", "CE", "Alloy", "C", "Cr", "Ni", "Mo"]
    med = df.groupby("family_group")[cols].median().reindex([g for g in FAMILY_GROUP_ORDER if g in set(df["family_group"])])
    lo, hi = df[cols].quantile(0.02), df[cols].quantile(0.98)
    scaled = ((med - lo) / (hi - lo)).clip(0, 1)
    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    x = np.arange(len(cols))
    for g, row in scaled.iterrows():
        ax.plot(x, row.values, color=GROUP_COLOR[g], lw=2.6, marker="o", ms=6, label=g)
    for xi in x:
        ax.axvline(xi, color=P.AXIS, lw=1)
    ax.set_xticks(x, [f"{lab}\n{lo.iloc[i]:.3g}–{hi.iloc[i]:.3g}" for i, lab in enumerate(labels)], fontsize=9)
    ax.set_yticks([0, 0.5, 1], ["P2", "mid", "P98"])
    ax.tick_params(axis="x", labelcolor=P.INK_2)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=6, fontsize=9)
    ax.set_title("Parallel coordinates: family-group medians across eight properties")
    P.subtitle(ax, "Each axis scaled from its 2nd to 98th percentile (range under the label)")
    P.source_note(fig)
    return fig
