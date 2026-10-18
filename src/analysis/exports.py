"""Phase 3: exports for Tableau and KNIME, plus Python reference numbers for the KNIME cross-check.

    python -m src.analysis.exports
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from . import modeling as M
from .cleaning import load_clean_grades, load_pipeline_meta
from .constants import ELEMENTS, EXPORTS_KNIME, EXPORTS_TABLEAU, RANDOM_STATE, REPORTS, TABLES
from .features import family_group
from .substitutes import SubstituteIndex, substitute_features
from .train import MODEL_OUTPUTS_CSV

logger = logging.getLogger("steelscope.exports")
TS = "tensile_strength_mpa"


def _load():
    grades = load_clean_grades()
    meta = load_pipeline_meta()
    outputs = pd.read_csv(MODEL_OUTPUTS_CSV)
    metrics = json.loads((REPORTS / "metrics.json").read_text(encoding="utf-8"))
    return grades, meta, outputs, metrics


# ------------------------------------------------------------------------------------- Tableau
def steels_wide(grades: pd.DataFrame, outputs: pd.DataFrame) -> pd.DataFrame:
    w = grades.merge(outputs, on="grade_id", how="left")
    w.insert(w.columns.get_loc("family_label") + 1, "family_group", family_group(w["family"]))
    w["abs_residual_mpa"] = w["residual_mpa"].abs()
    w["strength_class_pred_label"] = w["strength_class_pred"].map(
        {0: "Low (<300 MPa)", 1: "Medium (300-600 MPa)", 2: "High (>600 MPa)"})
    w["shares_composition"] = w["composition_group_size"] > 1
    return w


def steels_long(grades: pd.DataFrame, rare: list[str]) -> pd.DataFrame:
    """One row per (grade, element), zeros included so averages per family stay correct in Tableau."""
    long = grades.melt(id_vars=["grade_id", "display_name", "family", "family_label", "naming_source", "product_form"],
                       value_vars=ELEMENTS, var_name="element", value_name="wt_pct")
    long.insert(long.columns.get_loc("family_label") + 1, "family_group", family_group(long["family"]))
    long["is_rare_element"] = long["element"].isin(rare)
    long["is_present"] = long["wt_pct"] > 0
    long["element_role"] = np.select([long["element"] == "Fe", long["element"].isin(rare)], ["base", "trace"], "alloying")
    return long.sort_values(["grade_id", "element"]).reset_index(drop=True)


def family_summary(wide: pd.DataFrame) -> pd.DataFrame:
    g = wide.groupby(["family", "family_label", "family_group"])
    s = g.agg(n_grades=("grade_id", "size"), n_measured_ts=(TS, "count"),
              ts_p10=(TS, lambda v: v.quantile(.1)), ts_median=(TS, "median"), ts_p90=(TS, lambda v: v.quantile(.9)),
              liquidus_median=("liquidus_c", "median"), share_default_liquidus=("liquidus_is_default", "mean"),
              alloying_total_median=("alloying_total", "median"), carbon_equivalent_median=("carbon_equivalent", "median"),
              C_median=("C", "median"), Cr_median=("Cr", "median"), Ni_median=("Ni", "median"), Mo_median=("Mo", "median"),
              model_mae_oof=("abs_residual_mpa", "mean"), interval_coverage_oof=("in_interval", "mean"),
              share_shared_composition=("shares_composition", "mean"),
              dominant_cluster=("cluster_label", lambda v: v.value_counts().index[0]))
    return s.reset_index().sort_values("ts_median")


def model_metrics_long() -> pd.DataFrame:
    """Tidy table of every evaluation number (one metric per row) for Tableau and the docs."""
    rows = []
    reg = pd.read_csv(TABLES / "regression_comparison.csv")
    for _, r in reg.iterrows():
        for met in ["MAE", "RMSE", "R2"]:
            rows.append({"task": "TS regression", "model": r["model"], "features": r["features"], "metric": met,
                         "value": r[f"{met}_mean"], "sd": r[f"{met}_std"], "evaluation": "GroupKFold 5x3"})
    clf = pd.read_csv(TABLES / "classifier_comparison.csv")
    for _, r in clf.iterrows():
        for met in ["macro_F1", "balanced_accuracy", "accuracy"]:
            if f"{met}_mean" in r and pd.notna(r.get(f"{met}_mean")):
                rows.append({"task": "Strength class", "model": r["model"], "features": "composition+family",
                             "metric": met, "value": r[f"{met}_mean"], "sd": r[f"{met}_std"], "evaluation": "GroupKFold 5x3"})
        rows.append({"task": "Strength class", "model": r["model"], "features": "composition+family",
                     "metric": "macro_F1 (pooled OOF)", "value": r["oof_macro_F1"], "sd": np.nan, "evaluation": "OOF seed 0"})
    leak = pd.read_csv(TABLES / "leakage_demo.csv")
    for _, r in leak.iterrows():
        for met in ["MAE", "R2"]:
            rows.append({"task": "Leakage demo", "model": "Gradient boosting", "features": r["setup"], "metric": met,
                         "value": r[f"{met}_mean"], "sd": r[f"{met}_std"], "evaluation": r["setup"]})
    metrics = json.loads((REPORTS / "metrics.json").read_text(encoding="utf-8"))
    c = metrics["ceiling"]
    for met, key in [("MAE", "oracle_mae"), ("RMSE", "oracle_rmse"), ("R2", "oracle_r2")]:
        rows.append({"task": "TS regression", "model": "Ceiling: composition-group mean (oracle)", "features": "exact composition",
                     "metric": met, "value": c[key], "sd": np.nan, "evaluation": "in-sample, optimistic"})
    iv = metrics["intervals"]
    for met in ["coverage_raw", "coverage_calibrated", "mean_width_calibrated"]:
        rows.append({"task": "Prediction interval (80%)", "model": "Quantile GBM + cross-conformal", "features": "composition+family",
                     "metric": met, "value": iv[met], "sd": np.nan, "evaluation": "OOF seed 0"})
    return pd.DataFrame(rows)


def feature_importance() -> pd.DataFrame:
    perm = pd.read_csv(TABLES / "permutation_importance.csv", index_col=0)
    out = perm.copy()
    shap_path = TABLES / "shap_importance.csv"
    if shap_path.exists():
        out = out.join(pd.read_csv(shap_path, index_col=0)["mean_abs_shap_mpa"])
    out["rank_permutation"] = out["mae_increase_mean"].rank(ascending=False).astype(int)
    if "mean_abs_shap_mpa" in out:
        out["rank_shap"] = out["mean_abs_shap_mpa"].rank(ascending=False).astype(int)
    out.index.name = "feature"
    return out.reset_index().sort_values("rank_permutation")


# --------------------------------------------------------------------------------------- KNIME
KNIME_TEST_SIZE = 0.2


def knime_split(grades: pd.DataFrame) -> pd.Series:
    """Group-safe 80/20 split of the measured grades (identical chemistry stays on one side)."""
    m = grades.dropna(subset=[TS])
    gss = GroupShuffleSplit(n_splits=1, test_size=KNIME_TEST_SIZE, random_state=RANDOM_STATE)
    tr, te = next(gss.split(m, groups=m["composition_group_id"]))
    split = pd.Series("excluded_no_measured_ts", index=grades.index)
    split.loc[m.index[tr]] = "train"
    split.loc[m.index[te]] = "test"
    return split


def knime_input(grades: pd.DataFrame, rare: list[str]) -> pd.DataFrame:
    """Model-ready table. Rows are ordered train -> test -> unmeasured so that, after KNIME's Row Filter drops
    the imputed rows, Partitioning with 'Take from top' reproduces the Python split exactly."""
    k = grades.copy()
    k["split"] = knime_split(k)
    order = {"train": 0, "test": 1, "excluded_no_measured_ts": 2}
    k = k.sort_values(["split", "grade_id"], key=lambda s: s.map(order) if s.name == "split" else s)
    eng = ["alloying_total", "carbon_equivalent", "cr_eq", "ni_eq"]
    cols = (["grade_id", "display_name", "canonical_grade", "family", "family_label", "product_form", "naming_source",
             "is_imputed_ts", TS, "strength_class", "liquidus_c", "liquidus_is_default", "composition_group_id", "split"]
            + ELEMENTS + ["trace_total"])
    out = k[cols].copy()
    for c in eng:   # Python's values, so KNIME's Math Formula results can be diffed against them
        out[f"{c}_python"] = k[c]
    out["strength_class"] = out["strength_class"].astype("Int64")
    return out.reset_index(drop=True)


def knime_reference(knime: pd.DataFrame, rare: list[str], k_clusters: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Python numbers on the exact KNIME hold-out, with settings close to KNIME's node defaults."""
    num = M.composition_features(rare) + ["alloying_total", "carbon_equivalent", "cr_eq", "ni_eq"]
    cat = ["family", "product_form"]
    d = knime[knime["split"] != "excluded_no_measured_ts"].rename(columns={f"{c}_python": c for c in
                                                                          ["alloying_total", "carbon_equivalent", "cr_eq", "ni_eq"]})
    tr, te = d[d["split"] == "train"], d[d["split"] == "test"]
    prep = ColumnTransformer([("num", "passthrough", num), ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    regs = {
        "Random Forest (100 trees, sqrt features)": RandomForestRegressor(n_estimators=100, max_features="sqrt",
                                                                          random_state=RANDOM_STATE, n_jobs=-1),
        "Gradient Boosted Trees (100 trees, depth 4, lr 0.1)": GradientBoostingRegressor(n_estimators=100, max_depth=4,
                                                                                          learning_rate=0.1, random_state=RANDOM_STATE),
    }
    rows = [{"check": "rows", "item": "train", "value": len(tr)}, {"check": "rows", "item": "test", "value": len(te)},
            {"check": "rows", "item": "after Row Filter (measured TS)", "value": len(d)},
            {"check": "rows", "item": "removed by Row Filter (is_imputed_ts = true)", "value": int(knime["is_imputed_ts"].sum())}]
    for name, est in regs.items():
        p = Pipeline([("prep", prep), ("model", est)]).fit(tr[num + cat], tr[TS]).predict(te[num + cat])
        y = te[TS]
        rows += [{"check": "Numeric Scorer", "item": f"{name} | {met}", "value": val} for met, val in [
            ("R^2", r2_score(y, p)), ("mean absolute error", mean_absolute_error(y, p)),
            ("root mean squared error", float(np.sqrt(mean_squared_error(y, p)))),
            ("mean squared error", mean_squared_error(y, p))]]
    clf = Pipeline([("prep", prep), ("model", RandomForestClassifier(n_estimators=100, max_features="sqrt",
                                                                    random_state=RANDOM_STATE, n_jobs=-1))])
    pc = clf.fit(tr[num + cat], tr["strength_class"].astype(int)).predict(te[num + cat])
    yc = te["strength_class"].astype(int)
    rows += [{"check": "Scorer", "item": f"Random Forest classifier | {met}", "value": val} for met, val in [
        ("accuracy", accuracy_score(yc, pc)), ("Cohen's kappa", cohen_kappa_score(yc, pc)),
        ("macro F1", f1_score(yc, pc, average="macro"))]]
    for c in [0, 1, 2]:
        rows.append({"check": "Scorer", "item": f"test rows with true class {c}", "value": int((yc == c).sum())})
    for c in ["alloying_total", "carbon_equivalent", "cr_eq", "ni_eq"]:
        rows += [{"check": "Math Formula", "item": f"{c} | {stat}", "value": float(getattr(d[c], stat)())}
                 for stat in ["mean", "min", "max"]]
    idx = SubstituteIndex.fit(knime.reset_index(drop=True), substitute_features(rare), "log1p + z-score")
    km = KMeans(k_clusters, n_init=50, random_state=RANDOM_STATE).fit_predict(idx.matrix)
    sizes = pd.Series(km).value_counts().sort_values(ascending=False).values
    rows.append({"check": "k-Means", "item": f"cluster sizes, largest first (k={k_clusters}, all {len(knime)} rows)",
                 "value": " ".join(map(str, sizes))})
    confusion = pd.crosstab(pd.Series(yc.values, name="true"), pd.Series(pc, name="pred"))
    return pd.DataFrame(rows), confusion


# ---------------------------------------------------------------------------------- orchestration
def build_all() -> dict:
    grades, meta, outputs, metrics = _load()
    rare = meta["rare_elements"]
    EXPORTS_TABLEAU.mkdir(parents=True, exist_ok=True)
    EXPORTS_KNIME.mkdir(parents=True, exist_ok=True)
    wide = steels_wide(grades, outputs)
    files = {
        EXPORTS_TABLEAU / "steels_wide.csv": wide,
        EXPORTS_TABLEAU / "steels_long.csv": steels_long(grades, rare),
        EXPORTS_TABLEAU / "family_summary.csv": family_summary(wide),
        EXPORTS_TABLEAU / "model_metrics.csv": model_metrics_long(),
        EXPORTS_TABLEAU / "feature_importance.csv": feature_importance(),
    }
    knime = knime_input(grades, rare)
    ref, conf = knime_reference(knime, rare, metrics["clustering"]["k"])
    files[EXPORTS_KNIME / "knime_input.csv"] = knime
    files[EXPORTS_KNIME / "python_reference_metrics.csv"] = ref
    files[EXPORTS_KNIME / "python_reference_confusion.csv"] = conf
    files[EXPORTS_KNIME / "python_cv_metrics.csv"] = files[EXPORTS_TABLEAU / "model_metrics.csv"]
    for path, df in files.items():
        df.to_csv(path, index=path.name == "python_reference_confusion.csv")
        logger.info("%-40s %6d rows x %3d cols", f"{path.parent.name}/{path.name}", len(df), df.shape[1])
    return {p.name: df for p, df in files.items()}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_all()


if __name__ == "__main__":
    main()
