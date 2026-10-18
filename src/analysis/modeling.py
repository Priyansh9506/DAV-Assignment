"""Strength models evaluated with GroupKFold by composition group.

Why GroupKFold: grades with identical chemistry (processing variants) must never sit on both sides of a
split, otherwise the model is scored on chemistry it has already memorised. Everything here operates on
the grade table (one row per canonical grade, measured TS only).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import (balanced_accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, r2_score)
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import features as F
from .constants import ELEMENTS, RANDOM_STATE

TARGET = "tensile_strength_mpa"
CLASS_TARGET = "strength_class"
GROUP = "composition_group_id"
CATEGORICAL = ["family", "product_form"]
ENGINEERED = ["alloying_total", "carbon_equivalent", "cr_eq", "ni_eq"]


def composition_features(rare: list[str]) -> list[str]:
    """Element columns used by models: every non-rare element except Fe (Fe = 100 - alloying_total), plus
    the summed rare elements."""
    return [el for el in ELEMENTS if el not in rare and el != "Fe"] + ["trace_total"]


@dataclass(frozen=True)
class FeatureSpec:
    numeric: list[str]
    categorical: list[str]

    @property
    def columns(self) -> list[str]:
        return self.numeric + self.categorical


def feature_specs(rare: list[str]) -> dict[str, FeatureSpec]:
    num = composition_features(rare) + ENGINEERED
    return {"composition": FeatureSpec(num, []), "composition+family": FeatureSpec(num, CATEGORICAL)}


def category_levels(grades: pd.DataFrame) -> dict[str, list[str]]:
    return {c: sorted(grades[c].dropna().unique().tolist()) for c in CATEGORICAL}


def build_X(df: pd.DataFrame, spec: FeatureSpec, levels: dict[str, list[str]], rare: list[str]) -> pd.DataFrame:
    """Model matrix from a frame holding all element columns (+ family/product_form when needed).
    Engineered features are recomputed from the elements, so the app and the notebooks build X identically."""
    engineered = F.composition_features(df)
    X = pd.DataFrame(index=df.index)
    for c in spec.numeric:
        if c == "trace_total":
            X[c] = df[rare].sum(axis=1)
        elif c in engineered.columns:
            X[c] = engineered[c]
        else:
            X[c] = df[c]
    X = X.astype(float)
    for c in spec.categorical:
        X[c] = pd.Categorical(df[c], categories=levels[c])
    return X


# --------------------------------------------------------------------------------------------
# Estimators
# --------------------------------------------------------------------------------------------
class FamilyMedianRegressor(RegressorMixin, BaseEstimator):
    """Baseline: predict the training median TS of the grade's family (global median if unseen)."""

    def fit(self, X, y):
        y = pd.Series(np.asarray(y), index=X.index)
        self.medians_ = y.groupby(X["family"].astype(str)).median().to_dict()
        self.global_ = float(y.median())
        return self

    def predict(self, X):
        return X["family"].astype(str).map(self.medians_).fillna(self.global_).to_numpy(dtype=float)


class FamilyMajorityClassifier(ClassifierMixin, BaseEstimator):
    """Baseline: predict the most common strength class of the grade's family."""

    def fit(self, X, y):
        y = pd.Series(np.asarray(y), index=X.index)
        self.classes_ = np.unique(y)
        self.majority_ = y.groupby(X["family"].astype(str)).agg(lambda s: s.value_counts().idxmax()).to_dict()
        self.global_ = y.value_counts().idxmax()
        return self

    def predict(self, X):
        return X["family"].astype(str).map(self.majority_).fillna(self.global_).to_numpy()


def _preprocessor(spec: FeatureSpec, scale: bool) -> ColumnTransformer:
    num = StandardScaler() if scale else "passthrough"
    parts = [("num", num, spec.numeric)]
    if spec.categorical:
        parts.append(("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), spec.categorical))
    return ColumnTransformer(parts, verbose_feature_names_out=False)


HGB_GRID = {"learning_rate": [0.05, 0.1], "max_leaf_nodes": [15, 31], "min_samples_leaf": [5, 15]}
HGB_FIXED = {"max_iter": 400, "l2_regularization": 1.0, "random_state": RANDOM_STATE}


def make_regressor(name: str, spec: FeatureSpec):
    if name == "Global median":
        return DummyRegressor(strategy="median")
    if name == "Family median (baseline)":
        return FamilyMedianRegressor()
    if name == "Ridge":
        return Pipeline([("prep", _preprocessor(spec, scale=True)), ("model", RidgeCV(alphas=np.logspace(-3, 3, 25)))])
    if name == "Random forest":
        return Pipeline([("prep", _preprocessor(spec, scale=False)),
                         ("model", RandomForestRegressor(n_estimators=400, min_samples_leaf=2, max_features=0.5,
                                                         n_jobs=-1, random_state=RANDOM_STATE))])
    if name == "Gradient boosting (tuned)":
        return GridSearchCV(HistGradientBoostingRegressor(**HGB_FIXED), HGB_GRID, cv=GroupKFold(n_splits=3),
                            scoring="neg_mean_absolute_error", n_jobs=-1)
    if name == "Gradient boosting":
        return HistGradientBoostingRegressor(**HGB_FIXED, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=5)
    raise KeyError(name)


def make_classifier(name: str, spec: FeatureSpec):
    if name == "Family majority (baseline)":
        return FamilyMajorityClassifier()
    if name == "Logistic regression (balanced)":
        return Pipeline([("prep", _preprocessor(spec, scale=True)),
                         ("model", LogisticRegression(class_weight="balanced", max_iter=5000, C=1.0))])
    if name == "Gradient boosting (balanced)":
        return HistGradientBoostingClassifier(class_weight="balanced", max_iter=300, learning_rate=0.05,
                                              max_leaf_nodes=15, min_samples_leaf=5, l2_regularization=1.0,
                                              random_state=RANDOM_STATE)
    raise KeyError(name)


def _fit(est, X, y, groups):
    if isinstance(est, GridSearchCV):
        return est.fit(X, y, groups=groups)
    return est.fit(X, y)


# --------------------------------------------------------------------------------------------
# Cross-validation
# --------------------------------------------------------------------------------------------
def regression_metrics(y, p) -> dict:
    return {"MAE": mean_absolute_error(y, p), "RMSE": float(np.sqrt(mean_squared_error(y, p))), "R2": r2_score(y, p)}


def group_splits(X, y, groups, seed: int, n_splits: int = 5):
    return list(GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X, y, groups))


@dataclass
class CVResult:
    fold_metrics: pd.DataFrame          # one row per (seed, fold)
    oof: pd.Series                      # out-of-fold predictions for the first seed
    fold_of: pd.Series                  # fold index per row for the first seed
    best_params: list = field(default_factory=list)

    def summary(self) -> pd.Series:
        agg = self.fold_metrics.drop(columns=["seed", "fold"]).agg(["mean", "std"])
        return pd.Series({f"{m}_{s}": agg.loc[s, m] for m in agg.columns for s in ["mean", "std"]})


def cross_validate(make_est, X: pd.DataFrame, y: pd.Series, groups: pd.Series, seeds=(0, 1, 2),
                   n_splits: int = 5, task: str = "regression") -> CVResult:
    rows, best = [], []
    oof = pd.Series(np.nan, index=X.index, dtype=float)
    fold_of = pd.Series(-1, index=X.index)
    for seed in seeds:
        for k, (tr, te) in enumerate(group_splits(X, y, groups, seed, n_splits)):
            est = _fit(make_est(), X.iloc[tr], y.iloc[tr], groups.iloc[tr])
            if isinstance(est, GridSearchCV):
                best.append(est.best_params_)
            p = est.predict(X.iloc[te])
            if task == "regression":
                m = regression_metrics(y.iloc[te], p)
            else:
                m = {"macro_F1": f1_score(y.iloc[te], p, average="macro"),
                     "balanced_accuracy": balanced_accuracy_score(y.iloc[te], p),
                     "accuracy": float(np.mean(np.asarray(p) == y.iloc[te].to_numpy()))}
            rows.append({"seed": seed, "fold": k, **m})
            if seed == seeds[0]:
                oof.iloc[te] = p
                fold_of.iloc[te] = k
    return CVResult(pd.DataFrame(rows), oof, fold_of, best)


def compare_regressors(grades: pd.DataFrame, rare: list[str], models: list[str], spec_names: list[str],
                       seeds=(0, 1, 2)) -> tuple[pd.DataFrame, dict]:
    m = grades.dropna(subset=[TARGET]).reset_index(drop=True)
    levels, specs = category_levels(grades), feature_specs(rare)
    X_full = build_X(m, specs["composition+family"], levels, rare)
    y, groups = m[TARGET], m[GROUP]
    rows, results = [], {}
    for name in models:
        is_baseline = name in ("Global median", "Family median (baseline)")
        for spec_name in (["family only"] if is_baseline else spec_names):
            spec = specs.get(spec_name, specs["composition+family"])
            X = X_full[["family"]] if is_baseline else X_full[spec.columns]
            res = cross_validate(lambda: make_regressor(name, spec), X, y, groups, seeds)
            results[(name, spec_name)] = res
            rows.append({"model": name, "features": spec_name, **res.summary().to_dict(),
                         **{f"oof_{k}": v for k, v in regression_metrics(y, res.oof).items()}})
    return pd.DataFrame(rows), results


def leakage_demo(grades: pd.DataFrame, listings: pd.DataFrame, rare: list[str], seeds=(0, 1, 2)) -> pd.DataFrame:
    """Same model, four evaluation set-ups, to show how duplicates and imputed rows inflate or distort scores."""
    levels, spec = category_levels(grades), feature_specs(rare)["composition+family"]
    meta = grades.set_index("grade_id")[["family", "product_form", "trace_total", GROUP]]
    lst = listings.drop(columns=["family", GROUP], errors="ignore").join(meta, on="grade_id")
    setups = {
        "Listing rows incl. imputed TS, random KFold": (lst, "tensile_strength_raw", False),
        "Listing rows, imputed dropped, random KFold": (lst[~lst["is_imputed_ts"]], "tensile_strength_raw", False),
        "One row per grade, random KFold": (grades.dropna(subset=[TARGET]), TARGET, False),
        "One row per grade, GroupKFold (used)": (grades.dropna(subset=[TARGET]), TARGET, True),
    }
    rows = []
    for label, (df, target, grouped) in setups.items():
        df = df.reset_index(drop=True)
        X, y, g = build_X(df, spec, levels, rare), df[target], df[GROUP]
        for seed in seeds:
            splitter = GroupKFold(5, shuffle=True, random_state=seed) if grouped else KFold(5, shuffle=True, random_state=seed)
            for tr, te in splitter.split(X, y, g):
                est = make_regressor("Gradient boosting", spec).fit(X.iloc[tr], y.iloc[tr])
                rows.append({"setup": label, "n_rows": len(df), **regression_metrics(y.iloc[te], est.predict(X.iloc[te]))})
    out = pd.DataFrame(rows).groupby(["setup", "n_rows"], sort=False)[["MAE", "RMSE", "R2"]].agg(["mean", "std"])
    out.columns = [f"{a}_{b}" for a, b in out.columns]
    return out.reset_index()


# --------------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------------
def compare_classifiers(grades: pd.DataFrame, rare: list[str], models: list[str], seeds=(0, 1, 2),
                        regressor_oof: pd.Series | None = None):
    from .cleaning import strength_class
    m = grades.dropna(subset=[TARGET]).reset_index(drop=True)
    levels, spec = category_levels(grades), feature_specs(rare)["composition+family"]
    X, y, groups = build_X(m, spec, levels, rare), m[CLASS_TARGET].astype(int), m[GROUP]
    rows, results = [], {}
    for name in models:
        res = cross_validate(lambda: make_classifier(name, spec), X, y, groups, seeds, task="classification")
        results[name] = res
        oof = res.oof.astype(int)
        rows.append({"model": name, **res.summary().to_dict(),
                     "oof_macro_F1": f1_score(y, oof, average="macro"),
                     "oof_balanced_accuracy": balanced_accuracy_score(y, oof),
                     **{f"recall_class_{c}": float(((oof == c) & (y == c)).sum() / (y == c).sum()) for c in [0, 1, 2]}})
    if regressor_oof is not None:   # thresholding the TS regressor's out-of-fold prediction
        p = strength_class(pd.Series(regressor_oof.values)).astype(int)
        rows.append({"model": "GBM regressor, thresholded", "oof_macro_F1": f1_score(y, p, average="macro"),
                     "oof_balanced_accuracy": balanced_accuracy_score(y, p),
                     **{f"recall_class_{c}": float(((p == c) & (y == c)).sum() / (y == c).sum()) for c in [0, 1, 2]}})
        results["GBM regressor, thresholded"] = p
    return pd.DataFrame(rows), results, y


def confusion(y, p, labels=(0, 1, 2)) -> pd.DataFrame:
    return pd.DataFrame(confusion_matrix(y, p, labels=list(labels)),
                        index=[f"true {c}" for c in labels], columns=[f"pred {c}" for c in labels])


# --------------------------------------------------------------------------------------------
# Importance
# --------------------------------------------------------------------------------------------
def heldout_permutation_importance(grades: pd.DataFrame, rare: list[str], seed: int = 0, n_repeats: int = 10) -> pd.DataFrame:
    """Permutation importance measured on each held-out fold (never on training rows), averaged over folds.
    Categorical columns are permuted whole (e.g. 'family' as one feature, not per one-hot level)."""
    m = grades.dropna(subset=[TARGET]).reset_index(drop=True)
    levels, spec = category_levels(grades), feature_specs(rare)["composition+family"]
    X, y, groups = build_X(m, spec, levels, rare), m[TARGET], m[GROUP]
    frames = []
    for k, (tr, te) in enumerate(group_splits(X, y, groups, seed)):
        est = make_regressor("Gradient boosting", spec).fit(X.iloc[tr], y.iloc[tr])
        r = permutation_importance(est, X.iloc[te], y.iloc[te], scoring="neg_mean_absolute_error",
                                   n_repeats=n_repeats, random_state=RANDOM_STATE, n_jobs=-1)
        frames.append(pd.DataFrame({"feature": X.columns, "fold": k, "mae_increase": r.importances_mean}))
    imp = pd.concat(frames).groupby("feature")["mae_increase"].agg(["mean", "std"]).sort_values("mean", ascending=False)
    return imp.rename(columns={"mean": "mae_increase_mean", "std": "mae_increase_sd"})


# --------------------------------------------------------------------------------------------
# Prediction intervals: conformalized quantile regression (CQR)
# --------------------------------------------------------------------------------------------
@dataclass
class IntervalResult:
    lower: pd.Series
    upper: pd.Series
    coverage_raw: float
    coverage_calibrated: float
    mean_width_raw: float
    mean_width_calibrated: float
    q_hat_final: float
    nominal: float
    by_group_type: pd.DataFrame


def conformal_intervals(grades: pd.DataFrame, rare: list[str], alpha: float = 0.2, seed: int = 0) -> IntervalResult:
    """Out-of-fold 10th/90th-percentile GBMs, then a cross-conformal correction: fold k's interval is widened
    by the conformity quantile computed on the *other* folds only, so the reported coverage is honest."""
    m = grades.dropna(subset=[TARGET]).reset_index(drop=True)
    levels, spec = category_levels(grades), feature_specs(rare)["composition+family"]
    X, y, groups = build_X(m, spec, levels, rare), m[TARGET], m[GROUP]
    lo, hi, fold = pd.Series(np.nan, index=m.index), pd.Series(np.nan, index=m.index), pd.Series(-1, index=m.index)
    for k, (tr, te) in enumerate(group_splits(X, y, groups, seed)):
        for q, store in [(alpha / 2, lo), (1 - alpha / 2, hi)]:
            est = quantile_model(q).fit(X.iloc[tr], y.iloc[tr])
            store.iloc[te] = est.predict(X.iloc[te])
        fold.iloc[te] = k
    score = np.maximum(lo - y, y - hi)
    lo_c, hi_c = lo.copy(), hi.copy()
    for k in sorted(fold.unique()):
        other = score[fold != k]
        n = len(other)
        q_hat = float(np.quantile(other, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))
        lo_c[fold == k] -= q_hat
        hi_c[fold == k] += q_hat
    n = len(score)
    q_final = float(np.quantile(score, min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)))
    covered = (y >= lo_c) & (y <= hi_c)
    gtype = np.where(m["composition_group_n_measured"] > 1, "Composition shared with other grades", "Unique composition")
    by = pd.DataFrame({"covered": covered, "width": hi_c - lo_c, "type": gtype}).groupby("type").agg(
        n=("covered", "size"), coverage=("covered", "mean"), mean_width=("width", "mean"))
    return IntervalResult(lo_c, hi_c, float(((y >= lo) & (y <= hi)).mean()), float(covered.mean()),
                          float((hi - lo).mean()), float((hi_c - lo_c).mean()), q_final, 1 - alpha, by)


def quantile_model(q: float) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, **HGB_FIXED, learning_rate=0.05,
                                         max_leaf_nodes=15, min_samples_leaf=10)


# --------------------------------------------------------------------------------------------
# Final models for the app
# --------------------------------------------------------------------------------------------
def fit_final_models(grades: pd.DataFrame, rare: list[str], hgb_params: dict, alpha: float = 0.2) -> dict:
    m = grades.dropna(subset=[TARGET]).reset_index(drop=True)
    levels, spec = category_levels(grades), feature_specs(rare)["composition+family"]
    X, y = build_X(m, spec, levels, rare), m[TARGET]
    point = HistGradientBoostingRegressor(**{**HGB_FIXED, **hgb_params}).fit(X, y)
    q_lo = quantile_model(alpha / 2).fit(X, y)
    q_hi = quantile_model(1 - alpha / 2).fit(X, y)
    clf = make_classifier("Gradient boosting (balanced)", spec).fit(X, m[CLASS_TARGET].astype(int))
    return {"point": point, "q_lo": q_lo, "q_hi": q_hi, "classifier": clf, "spec": spec, "levels": levels,
            "n_train": int(len(m))}


def save_json(obj, path) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=2, default=default), encoding="utf-8")

