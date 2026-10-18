"""Phase 2 model figures (notebook 03)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import plotting as P
from .features import FAMILY_GROUP_ORDER, family_group

TS = "tensile_strength_mpa"


def model_comparison(tab: pd.DataFrame, baseline_mae: float, ie, chosen: tuple[str, str]):
    t = tab.copy()
    t["label"] = t["model"] + "  ·  " + t["features"]
    t = t.sort_values("MAE_mean", ascending=False)
    is_chosen = (t["model"] == chosen[0]) & (t["features"] == chosen[1])
    colors = np.where(is_chosen, P.BLUE, P.OTHER)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=True)
    y = np.arange(len(t))
    ax = axes[0]
    ax.barh(y, t["MAE_mean"], xerr=t["MAE_std"], height=0.6, color=colors, error_kw={"ecolor": P.MUTED, "lw": 1})
    for yi, v in zip(y, t["MAE_mean"]):
        ax.text(v + 12, yi, f"{v:.0f}", va="center", fontsize=8.5, color=P.INK_2)
    ax.axvline(ie.oracle_mae, color=P.AQUA, lw=1.4)
    ax.text(ie.oracle_mae + 3, len(t) - 0.4, f"composition-only\nceiling {ie.oracle_mae:.0f}", color=P.AQUA, fontsize=8, va="top")
    ax.axvline(baseline_mae, color=P.ORANGE, lw=1.4)
    ax.text(baseline_mae + 3, -0.6, f"family-median baseline {baseline_mae:.0f}", color=P.ORANGE, fontsize=8)
    ax.set_yticks(y, t["label"])
    ax.tick_params(axis="y", labelcolor=P.INK_2, labelsize=9)
    ax.set_xlabel("MAE (MPa), GroupKFold 5×3, lower is better")
    ax.grid(axis="y", visible=False)
    ax.set_title("Error")
    P.subtitle(ax, "Bars = mean over 15 folds, whiskers = ±1 SD")
    ax = axes[1]
    ax.barh(y, t["R2_mean"], xerr=t["R2_std"], height=0.6, color=colors, error_kw={"ecolor": P.MUTED, "lw": 1})
    for yi, v in zip(y, t["R2_mean"]):
        ax.text(max(v, 0) + 0.03, yi, f"{v:.2f}", va="center", fontsize=8.5, color=P.INK_2)
    ax.axvline(ie.oracle_r2, color=P.AQUA, lw=1.4)
    ax.text(ie.oracle_r2 - 0.02, len(t) - 0.4, f"ceiling\n{ie.oracle_r2:.2f}", color=P.AQUA, fontsize=8, va="top", ha="right")
    ax.axvline(0, color=P.AXIS, lw=1)
    ax.set_xlim(-0.2, 1.05)
    ax.set_xlabel("R², higher is better")
    ax.grid(axis="y", visible=False)
    ax.set_title("Explained variance")
    P.subtitle(ax, "Highlighted = model deployed in the app")
    fig.suptitle("Gradient boosting halves the baseline error; linear models cannot beat family medians",
                 x=0.01, ha="left", fontsize=13.5, fontweight="semibold", color=P.INK, y=1.04)
    fig.tight_layout(w_pad=2)
    P.source_note(fig)
    return fig


def leakage_demo(leak: pd.DataFrame):
    t = leak.iloc[::-1]
    colors = [P.BLUE if "used" in s else P.OTHER for s in t["setup"]]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    y = np.arange(len(t))
    ax.barh(y, t["R2_mean"], xerr=t["R2_std"], height=0.58, color=colors, error_kw={"ecolor": P.MUTED, "lw": 1})
    for yi, (r2, mae, n) in enumerate(zip(t["R2_mean"], t["MAE_mean"], t["n_rows"])):
        ax.text(r2 + 0.03, yi, f"R² {r2:.2f} · MAE {mae:.0f} MPa · {n} rows", va="center", fontsize=8.5, color=P.INK_2)
    ax.set_yticks(y, t["setup"])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 1.45)
    ax.set_xlabel("R² (same gradient-boosting model, 5-fold × 3)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Twin listings leak: random splits overstate accuracy")
    P.subtitle(ax, "Twins in train and test inflate R²; imputed targets add noise; GroupKFold on grades is the honest score")
    P.source_note(fig)
    return fig


def pred_vs_actual(m: pd.DataFrame, oof: pd.Series):
    shared = m["composition_group_n_measured"].to_numpy() > 1
    y = m[TS].to_numpy()
    p = oof.to_numpy()
    fig, ax = plt.subplots(figsize=(7.8, 7))
    lim = (0, 2600)
    ax.plot(lim, lim, color=P.AXIS, lw=1.2, zorder=1)
    for mask, color, name in [(~shared, P.BLUE, "Unique composition"), (shared, P.ORANGE, "Composition shared with other grades")]:
        mae = np.mean(np.abs(y[mask] - p[mask]))
        ax.scatter(y[mask], p[mask], s=16, color=color, linewidths=0.4, zorder=3 if mask is shared else 2,
                   label=f"{name}: n={mask.sum()}, MAE {mae:.0f} MPa")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal")
    ax.set_xlabel("Measured tensile strength (MPa)")
    ax.set_ylabel("Predicted, out-of-fold (MPa)")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Where the model misses, processing is the reason")
    P.subtitle(ax, "Grades sharing their exact chemistry with other tempers carry most of the large errors")
    P.source_note(fig)
    return fig


def error_by_family(m: pd.DataFrame, oof: pd.Series):
    e = pd.DataFrame({"family": m["family_label"], "ae": (oof - m[TS]).abs()})
    t = e.groupby("family")["ae"].agg(["size", "mean", "median"]).sort_values("mean")
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    y = np.arange(len(t))
    ax.barh(y, t["mean"], height=0.6, color=P.BLUE, label="Mean absolute error")
    ax.scatter(t["median"], y, color=P.INK, s=22, zorder=3, label="Median absolute error")
    for yi, (v, n) in enumerate(zip(t["mean"], t["size"])):
        ax.text(v + 6, yi, f"{v:.0f}  (n={n})", va="center", fontsize=8.5, color=P.INK_2)
    ax.set_yticks(y, t.index)
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, t["mean"].max() * 1.25)
    ax.set_xlabel("Absolute error, out-of-fold (MPa)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    ax.set_title("Error is lowest where chemistry decides strength")
    P.subtitle(ax, "Maraging, ductile and malleable irons are heat-treatment-defined: the model cannot see that")
    P.source_note(fig)
    return fig


def classifier_results(tab: pd.DataFrame, cm: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    t = tab.iloc[::-1]
    colors = [P.BLUE if "Gradient boosting (balanced)" == mname else P.OTHER for mname in t["model"]]
    y = np.arange(len(t))
    ax.barh(y, t["oof_macro_F1"], height=0.58, color=colors)
    for yi, (f1, ba) in enumerate(zip(t["oof_macro_F1"], t["oof_balanced_accuracy"])):
        ax.text(f1 + 0.015, yi, f"macro-F1 {f1:.2f} · bal. acc. {ba:.2f}", va="center", fontsize=8.5, color=P.INK_2)
    ax.set_yticks(y, t["model"])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 1.45)
    ax.set_xlabel("Macro-F1, out-of-fold (GroupKFold)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Strength class from composition, no TS used")
    P.subtitle(ax, "Class-balanced models; macro-F1 weights the 23-grade low class equally")
    ax = axes[1]
    v = cm.to_numpy()
    rown = v / v.sum(axis=1, keepdims=True)
    ax.imshow(rown, cmap=P.SEQ_ON_DARK, vmin=0, vmax=1)
    names = ["Low", "Medium", "High"]
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{v[i, j]}\n{rown[i, j]:.0%}", ha="center", va="center", fontsize=9.5,
                    color=P.SURFACE if rown[i, j] > 0.55 else P.INK)
    ax.set_xticks(range(3), [f"pred {n}" for n in names])
    ax.set_yticks(range(3), [f"true {n}" for n in names])
    ax.tick_params(axis="both", labelcolor=P.INK_2)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Gradient boosting confusion matrix")
    P.subtitle(ax, "Counts and row % (recall); errors are almost all medium ↔ high near 600 MPa")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def importance(perm: pd.DataFrame, shap_mean: pd.Series, top: int = 14):
    labels = {"carbon_equivalent": "Carbon equivalent", "alloying_total": "Alloying total", "cr_eq": "Cr equivalent",
              "ni_eq": "Ni equivalent", "product_form": "Product form", "family": "Family", "trace_total": "Trace elements"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    p = perm.head(top).iloc[::-1]
    ax = axes[0]
    y = np.arange(len(p))
    ax.barh(y, p["mae_increase_mean"], xerr=p["mae_increase_sd"], height=0.6, color=P.BLUE,
            error_kw={"ecolor": P.MUTED, "lw": 1})
    ax.set_yticks(y, [labels.get(f, f) for f in p.index])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlabel("MAE increase when shuffled (MPa), held-out folds")
    ax.grid(axis="y", visible=False)
    ax.set_title("Permutation importance")
    P.subtitle(ax, "Mean ± SD across the 5 held-out folds")
    s = shap_mean.head(top).iloc[::-1]
    ax = axes[1]
    y = np.arange(len(s))
    ax.barh(y, s.values, height=0.6, color=P.BLUE)
    ax.set_yticks(y, [labels.get(f, f) for f in s.index])
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlabel("Mean |SHAP value| (MPa)")
    ax.grid(axis="y", visible=False)
    ax.set_title("SHAP (permutation explainer, deployed model)")
    P.subtitle(ax, "Average push of each feature on a grade's prediction")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def shap_dependence(X: pd.DataFrame, sv: np.ndarray, cols: list[str], families: pd.Series,
                    features=("C", "Ni", "carbon_equivalent")):
    names = {"carbon_equivalent": "Carbon equivalent (wt%)", "C": "Carbon (wt%)", "Ni": "Nickel (wt%)"}
    grp = family_group(families.reset_index(drop=True))
    show = ["Carbon & low-alloy", "Stainless", "Cast iron"]
    fig, axes = plt.subplots(1, len(features), figsize=(14, 4.4), sharey=True)
    for ax, f in zip(axes, features):
        j = cols.index(f)
        xv = X[f].to_numpy()
        other = ~grp.isin(show).to_numpy()
        ax.scatter(xv[other], sv[other, j], s=12, color=P.OTHER, linewidths=0, label="Other families")
        for name, color in zip(show, [P.BLUE, P.ORANGE, P.AQUA]):
            msk = (grp == name).to_numpy()
            ax.scatter(xv[msk], sv[msk, j], s=14, color=color, linewidths=0.3, label=name)
        ax.axhline(0, color=P.AXIS, lw=1)
        ax.set_xlabel(names.get(f, f))
        if f in ("Ni", "carbon_equivalent"):
            ax.set_xscale("symlog", linthresh=1)
    axes[0].set_ylabel("SHAP value: effect on predicted TS (MPa)")
    axes[0].legend(loc="upper left", fontsize=8.5)
    fig.suptitle("How the model uses carbon, nickel and CE depends on the family",
                 x=0.01, ha="left", fontsize=13, fontweight="semibold", color=P.INK, y=1.03)
    fig.tight_layout(w_pad=2)
    P.source_note(fig)
    return fig


def interval_coverage(iv, m: pd.DataFrame, oof: pd.Series, n_show: int = 70, seed: int = 0):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axes[0]
    bars = [("Quantile GBMs, raw", iv.coverage_raw), ("After conformal\ncalibration (all)", iv.coverage_calibrated)]
    bars += [(f"Calibrated:\n{k.lower()}", v) for k, v in iv.by_group_type["coverage"].items()]
    y = np.arange(len(bars))[::-1]
    ax.barh(y, [b[1] for b in bars], height=0.58, color=[P.OTHER, P.BLUE, P.BLUE, P.BLUE])
    for yi, (_, v) in zip(y, bars):
        ax.text(v + 0.01, yi, f"{v:.1%}", va="center", fontsize=9, color=P.INK_2)
    ax.axvline(iv.nominal, color=P.ORANGE, lw=1.4)
    ax.text(iv.nominal + 0.005, len(bars) - 0.45, f"target {iv.nominal:.0%}", color=P.ORANGE, fontsize=8.5)
    ax.set_yticks(y, [b[0] for b in bars])
    ax.tick_params(axis="y", labelcolor=P.INK_2, labelsize=9)
    ax.set_xlim(0, 1.05)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Share of grades whose measured TS falls inside the interval")
    ax.grid(axis="y", visible=False)
    ax.set_title("80 % prediction intervals: coverage")
    P.subtitle(ax, "Cross-conformal: each fold calibrated on the other folds only")
    ax = axes[1]
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(m), n_show, replace=False))
    order = idx[np.argsort(oof.to_numpy()[idx])]
    x = np.arange(len(order))
    y_true = m[TS].to_numpy()[order]
    lo, hi = iv.lower.to_numpy()[order], iv.upper.to_numpy()[order]
    inside = (y_true >= lo) & (y_true <= hi)
    ax.vlines(x, lo, hi, color=P.AXIS, lw=4, label="80 % interval")
    ax.scatter(x, oof.to_numpy()[order], color=P.INK_2, s=10, zorder=3, label="Prediction")
    ax.scatter(x[inside], y_true[inside], color=P.BLUE, s=18, zorder=4, label="Measured, inside")
    ax.scatter(x[~inside], y_true[~inside], color=P.ORANGE, s=22, zorder=4, marker="D", label="Measured, outside")
    ax.set_xticks([])
    ax.set_xlabel(f"{n_show} random grades, sorted by prediction")
    ax.set_ylabel("Tensile strength (MPa)")
    ax.legend(loc="upper left", fontsize=8.5, ncol=2)
    ax.set_title("What the app's uncertainty range looks like")
    P.subtitle(ax, f"Mean calibrated width {iv.mean_width_calibrated:.0f} MPa")
    fig.tight_layout(w_pad=3)
    P.source_note(fig)
    return fig


def clustering_overview(res, grades: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.6), gridspec_kw={"width_ratios": [1, 2.3]})
    ax = axes[0]
    s = res.silhouette_by_k
    ax.plot(s.index, s.values, color=P.BLUE, marker="o", ms=5)
    ax.scatter([res.k], [s[res.k]], color=P.ORANGE, s=60, zorder=3)
    ax.annotate(f"k = {res.k}", (res.k, s[res.k]), xytext=(-40, 10), textcoords="offset points", color=P.INK_2, fontsize=9)
    ax.set_xlabel("Number of clusters k")
    ax.set_ylabel("Silhouette score")
    ax.set_title("KMeans: choosing k")
    P.subtitle(ax, "Standardized log1p composition")
    ax = axes[1]
    ct = res.contingency
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index, ct.sum(axis=0).sort_values(ascending=False).index]
    share = ct.div(ct.sum(axis=1), axis=0)
    ax.imshow(np.ma.masked_where(ct.to_numpy() == 0, share.to_numpy()), cmap=P.SEQ_ON_DARK, vmin=0, vmax=1, aspect="auto")
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            v = ct.iat[i, j]
            if v:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=7.5,
                        color=P.SURFACE if share.iat[i, j] > 0.55 else P.INK)
    ax.set_xticks(range(ct.shape[1]), ct.columns, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(ct.shape[0]), [f"{lab[:44]}  n={n}" for lab, n in zip(ct.index, ct.sum(axis=1))], fontsize=8)
    ax.tick_params(axis="both", labelcolor=P.INK_2)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title("Composition clusters vs named families")
    P.subtitle(ax, "Cell = grades; shade = share of the cluster. Stainless splits by chemistry; plain-steel families merge")
    fig.tight_layout(w_pad=2)
    P.source_note(fig)
    return fig


def umap_small_multiples(xy: np.ndarray, grades: pd.DataFrame):
    grp = family_group(grades["family"].reset_index(drop=True))
    groups = [g for g in FAMILY_GROUP_ORDER if g in set(grp)]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.4), sharex=True, sharey=True)
    for ax, name in zip(axes.ravel(), groups):
        on = (grp == name).to_numpy()
        ax.scatter(xy[~on, 0], xy[~on, 1], s=5, color=P.OTHER, linewidths=0, alpha=0.6)
        ax.scatter(xy[on, 0], xy[on, 1], s=9, color=P.BLUE, linewidths=0)
        ax.set_title(f"{name}  (n={on.sum()})", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
    fig.suptitle("UMAP of composition space: each panel highlights one family group",
                 x=0.01, ha="left", fontsize=13, fontweight="semibold", color=P.INK, y=1.01)
    fig.tight_layout()
    P.source_note(fig)
    return fig


def substitute_eval(ev: pd.DataFrame, chosen: str):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 3.8), sharey=True)
    t = ev.iloc[::-1]
    y = np.arange(len(t))
    colors = [P.BLUE if i == chosen else P.OTHER for i in t.index]
    ax = axes[0]
    ax.barh(y, t["family_agree@1"], height=0.58, color=colors)
    for yi, v in zip(y, t["family_agree@1"]):
        ax.text(v + 0.01, yi, f"{v:.1%}", va="center", fontsize=9, color=P.INK_2)
    ax.set_yticks(y, t.index)
    ax.tick_params(axis="y", labelcolor=P.INK_2)
    ax.set_xlim(0, 1.15)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Nearest neighbour in the same family")
    ax.grid(axis="y", visible=False)
    ax.set_title("Substitute engine: which distance?")
    P.subtitle(ax, "Nearest neighbour with a different composition")
    ax = axes[1]
    ax.barh(y, t["median_abs_dTS@1"], height=0.58, color=colors)
    for yi, v in zip(y, t["median_abs_dTS@1"]):
        ax.text(v + 2, yi, f"{v:.0f} MPa", va="center", fontsize=9, color=P.INK_2)
    ax.set_xlim(0, t["median_abs_dTS@1"].max() * 1.25)
    ax.set_xlabel("Median |ΔTS| to nearest neighbour (MPa)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Strength similarity")
    P.subtitle(ax, "Lower is better")
    fig.tight_layout(w_pad=2)
    P.source_note(fig)
    return fig
