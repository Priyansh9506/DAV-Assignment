"""Fit the deployed models and persist every artifact the app and the exports read.

Artifacts (models/):
    ts_point.joblib, ts_q_lo.joblib, ts_q_hi.joblib   tensile-strength GBM + 10th/90th percentile GBMs
    strength_class.joblib                              balanced GBM classifier (no TS input)
    model_meta.json                                    features, category levels, q_hat, CV metrics, versions
    substitute_index.json                              transform + standardization for the substitute engine
Per-grade outputs: data/processed/model_outputs.csv (out-of-fold predictions, intervals, clusters, 2-D maps).
"""
from __future__ import annotations

import datetime as dt
import logging

import joblib
import numpy as np
import pandas as pd
import sklearn

from . import modeling as M
from .constants import DATA_PROCESSED, MODELS_DIR
from .evaluation import CHOSEN_REGRESSOR, CHOSEN_TRANSFORM, Evaluation, metrics_summary
from .substitutes import SubstituteIndex, substitute_features

logger = logging.getLogger("steelscope.train")
MODEL_OUTPUTS_CSV = DATA_PROCESSED / "model_outputs.csv"
CHOSEN_HGB_PARAMS = {"learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 5}


def predict_interval(models: dict, X: pd.DataFrame, q_hat: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Point prediction and conformalized 80 % interval; the interval is forced to contain the point
    prediction (quantile models can cross) and floored at 0 MPa."""
    point = models["point"].predict(X)
    lo = np.minimum(models["q_lo"].predict(X) - q_hat, point)
    hi = np.maximum(models["q_hi"].predict(X) + q_hat, point)
    return point, np.maximum(lo, 0.0), hi


def train_and_save(grades: pd.DataFrame, rare: list[str], ev: Evaluation) -> pd.DataFrame:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    final = M.fit_final_models(grades, rare, CHOSEN_HGB_PARAMS, alpha=1 - ev.intervals.nominal)
    for key, name in [("point", "ts_point"), ("q_lo", "ts_q_lo"), ("q_hi", "ts_q_hi"), ("classifier", "strength_class")]:
        joblib.dump(final[key], MODELS_DIR / f"{name}.joblib")

    spec, levels = final["spec"], final["levels"]
    summary = metrics_summary(ev)
    meta = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "target": M.TARGET, "unit": "MPa",
        "numeric_features": spec.numeric, "categorical_features": spec.categorical, "category_levels": levels,
        "rare_elements": rare, "n_train": final["n_train"],
        "interval": {"nominal_coverage": ev.intervals.nominal, "q_hat": ev.intervals.q_hat_final,
                     "cv_coverage": ev.intervals.coverage_calibrated, "cv_mean_width": ev.intervals.mean_width_calibrated},
        "cv_metrics": summary["chosen_regressor"], "baseline": summary["baseline_family_median"],
        "ceiling": summary["ceiling"], "classifier": summary["classifier"],
        "hyperparameters": {**M.HGB_FIXED, **CHOSEN_HGB_PARAMS},
        "warning": "Composition-only model: processing / heat treatment is not modelled.",
    }
    M.save_json(meta, MODELS_DIR / "model_meta.json")
    sub_idx = SubstituteIndex.fit(grades, substitute_features(rare), CHOSEN_TRANSFORM)
    M.save_json({**sub_idx.to_config(), "evaluation": summary["substitutes"]}, MODELS_DIR / "substitute_index.json")

    out = per_grade_outputs(grades, rare, ev, final)
    out.to_csv(MODEL_OUTPUTS_CSV, index=False)
    logger.info("saved models and %s (%d rows)", MODEL_OUTPUTS_CSV.name, len(out))
    return out


def per_grade_outputs(grades: pd.DataFrame, rare: list[str], ev: Evaluation, final: dict) -> pd.DataFrame:
    """One row per grade. Measured grades get out-of-fold predictions (honest residuals); the 7 grades
    without measured TS get the final model's prediction, flagged as such."""
    g = grades.reset_index(drop=True)
    X_all = M.build_X(g, final["spec"], final["levels"], rare)
    point, lo, hi = predict_interval(final, X_all, ev.intervals.q_hat_final)
    cls_final = final["classifier"].predict(X_all)

    m = ev.measured
    oof = pd.DataFrame({
        "grade_id": m["grade_id"], "oof_pred": ev.chosen_oof.values,
        "oof_lo": ev.intervals.lower.values, "oof_hi": ev.intervals.upper.values,
        "oof_class": ev.clf_results["Gradient boosting (balanced)"].oof.astype(int).values,
        "cv_fold": ev.reg_results[CHOSEN_REGRESSOR].fold_of.values,
    })
    out = pd.DataFrame({"grade_id": g["grade_id"], "final_pred": point, "final_lo": lo, "final_hi": hi,
                        "final_class": cls_final}).merge(oof, on="grade_id", how="left")
    has_oof = out["oof_pred"].notna()
    out["ts_pred_mpa"] = np.where(has_oof, out["oof_pred"], out["final_pred"])
    out["ts_pred_lo_mpa"] = np.where(has_oof, np.maximum(out["oof_lo"], 0), out["final_lo"])
    out["ts_pred_hi_mpa"] = np.where(has_oof, out["oof_hi"], out["final_hi"])
    out["strength_class_pred"] = np.where(has_oof, out["oof_class"], out["final_class"]).astype(int)
    out["pred_source"] = np.where(has_oof, "out_of_fold", "final_model_no_measured_ts")
    ts = g.set_index("grade_id")["tensile_strength_mpa"]
    out["residual_mpa"] = out["grade_id"].map(ts) - out["ts_pred_mpa"]
    out["in_interval"] = (out["grade_id"].map(ts) >= out["ts_pred_lo_mpa"]) & (out["grade_id"].map(ts) <= out["ts_pred_hi_mpa"])
    out.loc[~has_oof, "in_interval"] = np.nan

    cl = ev.clustering
    out["cluster_id"] = cl.kmeans_labels
    out["cluster_label"] = pd.Series(cl.kmeans_labels).map(cl.profiles["label"]).values
    out["hdbscan_cluster"] = cl.hdbscan_labels
    out["pca_1"], out["pca_2"] = cl.pca_xy[:, 0], cl.pca_xy[:, 1]
    if cl.umap_xy is not None:
        out["umap_1"], out["umap_2"] = cl.umap_xy[:, 0], cl.umap_xy[:, 1]
    keep = ["grade_id", "ts_pred_mpa", "ts_pred_lo_mpa", "ts_pred_hi_mpa", "residual_mpa", "in_interval", "pred_source",
            "strength_class_pred", "cv_fold", "cluster_id", "cluster_label", "hdbscan_cluster", "pca_1", "pca_2"]
    keep += [c for c in ["umap_1", "umap_2"] if c in out.columns]
    return out[keep]


def load_artifacts() -> dict:
    import json
    meta = json.loads((MODELS_DIR / "model_meta.json").read_text(encoding="utf-8"))
    models = {k: joblib.load(MODELS_DIR / f"{f}.joblib") for k, f in
              [("point", "ts_point"), ("q_lo", "ts_q_lo"), ("q_hi", "ts_q_hi"), ("classifier", "strength_class")]}
    return {"meta": meta, **models}
