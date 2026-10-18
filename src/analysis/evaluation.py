"""Runs every model comparison once and persists the results.

`run_evaluation` is called by notebook 03 (which then plots each part) and by the CLI pipeline, so the
numbers in reports/, the docs and the app all come from the same run.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from . import modeling as M
from .clustering import ClusteringResult, run_clustering
from .constants import REPORTS, TABLES
from .quality import IrreducibleError, irreducible_error
from .substitutes import evaluate_transforms

logger = logging.getLogger("steelscope.evaluation")

REGRESSORS = ["Global median", "Family median (baseline)", "Ridge", "Random forest", "Gradient boosting"]
CLASSIFIERS = ["Family majority (baseline)", "Logistic regression (balanced)", "Gradient boosting (balanced)"]
CHOSEN_REGRESSOR = ("Gradient boosting", "composition+family")
CHOSEN_TRANSFORM = "log1p + z-score"


@dataclass
class Evaluation:
    measured: pd.DataFrame
    ceiling: IrreducibleError
    reg_table: pd.DataFrame
    reg_results: dict
    leakage: pd.DataFrame
    clf_table: pd.DataFrame
    clf_results: dict
    y_class: pd.Series
    perm_importance: pd.DataFrame
    intervals: M.IntervalResult
    clustering: ClusteringResult
    substitute_eval: pd.DataFrame

    @property
    def chosen_oof(self) -> pd.Series:
        return self.reg_results[CHOSEN_REGRESSOR].oof

    @property
    def baseline_mae(self) -> float:
        return float(self.reg_table.loc[self.reg_table["model"] == "Family median (baseline)", "MAE_mean"].iloc[0])

    def chosen_row(self) -> pd.Series:
        t = self.reg_table
        return t[(t["model"] == CHOSEN_REGRESSOR[0]) & (t["features"] == CHOSEN_REGRESSOR[1])].iloc[0]


def run_evaluation(grades: pd.DataFrame, listings: pd.DataFrame, rare: list[str], with_tuned: bool = True,
                   with_umap: bool = True) -> Evaluation:
    measured = grades.dropna(subset=[M.TARGET]).reset_index(drop=True)
    logger.info("regression comparison")
    reg_table, reg_results = M.compare_regressors(grades, rare, REGRESSORS, ["composition", "composition+family"])
    if with_tuned:   # nested GroupKFold tuning: checks the fixed GBM settings are not leaving accuracy behind
        t2, r2 = M.compare_regressors(grades, rare, ["Gradient boosting (tuned)"], ["composition+family"])
        reg_table, reg_results = pd.concat([reg_table, t2], ignore_index=True), {**reg_results, **r2}
    logger.info("leakage demo")
    leakage = M.leakage_demo(grades, listings, rare)
    logger.info("classification")
    clf_table, clf_results, y_class = M.compare_classifiers(grades, rare, CLASSIFIERS,
                                                            regressor_oof=reg_results[CHOSEN_REGRESSOR].oof)
    logger.info("importance, intervals, clustering, substitutes")
    perm = M.heldout_permutation_importance(grades, rare)
    intervals = M.conformal_intervals(grades, rare)
    clustering = run_clustering(grades, rare, with_umap=with_umap)
    sub_eval = evaluate_transforms(grades, rare)
    return Evaluation(measured, irreducible_error(grades), reg_table, reg_results, leakage, clf_table, clf_results,
                      y_class, perm, intervals, clustering, sub_eval)


def metrics_summary(ev: Evaluation) -> dict:
    chosen = ev.chosen_row()
    m = ev.measured
    shared = m["composition_group_n_measured"] > 1
    err = (ev.chosen_oof - m[M.TARGET]).abs()
    gbm_clf = ev.clf_table.set_index("model").loc["Gradient boosting (balanced)"]
    return {
        "n_grades_measured": int(len(m)),
        "cv": "GroupKFold by composition_group_id, 5 folds x 3 seeds (0, 1, 2)",
        "ceiling": ev.ceiling.as_dict(),
        "chosen_regressor": {"model": CHOSEN_REGRESSOR[0], "features": CHOSEN_REGRESSOR[1],
                             **{k: float(chosen[k]) for k in ["MAE_mean", "MAE_std", "RMSE_mean", "RMSE_std", "R2_mean", "R2_std",
                                                               "oof_MAE", "oof_RMSE", "oof_R2"]},
                             "oof_MAE_unique_composition": float(err[~shared].mean()),
                             "oof_MAE_shared_composition": float(err[shared].mean()),
                             "oof_median_AE": float(err.median()),
                             "hyperparameters": {k: v for k, v in M.make_regressor("Gradient boosting", None).get_params().items()
                                                 if k in ("learning_rate", "max_leaf_nodes", "min_samples_leaf",
                                                          "l2_regularization", "max_iter")}},
        "baseline_family_median": {k: float(v) for k, v in ev.reg_table.set_index("model").loc[
            "Family median (baseline)", ["MAE_mean", "RMSE_mean", "R2_mean"]].items()},
        "classifier": {"model": "Gradient boosting (balanced)",
                       **{k: float(gbm_clf[k]) for k in ["macro_F1_mean", "macro_F1_std", "balanced_accuracy_mean",
                                                         "oof_macro_F1", "oof_balanced_accuracy", "recall_class_0",
                                                         "recall_class_1", "recall_class_2"]},
                       "confusion_oof": M.confusion(ev.y_class, ev.clf_results["Gradient boosting (balanced)"].oof.astype(int)).values.tolist()},
        "intervals": {"nominal": ev.intervals.nominal, "coverage_raw": ev.intervals.coverage_raw,
                      "coverage_calibrated": ev.intervals.coverage_calibrated,
                      "mean_width_calibrated": ev.intervals.mean_width_calibrated, "q_hat_final": ev.intervals.q_hat_final,
                      "by_group_type": ev.intervals.by_group_type.reset_index().to_dict(orient="records")},
        "clustering": {"k": ev.clustering.k, "silhouette": float(ev.clustering.silhouette_by_k[ev.clustering.k]),
                       "agreement": ev.clustering.agreement.to_dict(orient="records")},
        "substitutes": {"transform": CHOSEN_TRANSFORM, **ev.substitute_eval.loc[CHOSEN_TRANSFORM].to_dict(),
                        "random_baseline": ev.substitute_eval.loc["random pair (baseline)"].to_dict()},
    }


def save_evaluation(ev: Evaluation) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    ev.reg_table.to_csv(TABLES / "regression_comparison.csv", index=False)
    ev.leakage.to_csv(TABLES / "leakage_demo.csv", index=False)
    ev.clf_table.to_csv(TABLES / "classifier_comparison.csv", index=False)
    M.confusion(ev.y_class, ev.clf_results["Gradient boosting (balanced)"].oof.astype(int)).to_csv(TABLES / "confusion_gbm.csv")
    ev.perm_importance.to_csv(TABLES / "permutation_importance.csv")
    ev.intervals.by_group_type.to_csv(TABLES / "interval_coverage.csv")
    ev.clustering.agreement.to_csv(TABLES / "cluster_family_agreement.csv", index=False)
    ev.clustering.profiles.to_csv(TABLES / "cluster_profiles.csv")
    ev.clustering.contingency.to_csv(TABLES / "cluster_family_contingency.csv")
    ev.clustering.silhouette_by_k.to_csv(TABLES / "silhouette_by_k.csv")
    ev.substitute_eval.to_csv(TABLES / "substitute_transform_eval.csv")
    M.save_json(metrics_summary(ev), REPORTS / "metrics.json")
