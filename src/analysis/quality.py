"""Data-quality investigations behind the cleaning decisions.

- `liquidus_default_evidence`: is liquidus = 1460 °C a placeholder?
- `irreducible_error`: how much TS varies for identical composition (the model ceiling)
- `imputation_sensitivity`: how headline statistics change with vs without imputed rows
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .constants import DEFAULT_LIQUIDUS_C, ELEMENTS


# --------------------------------------------------------------------------------------------
# Liquidus = 1460 °C
# --------------------------------------------------------------------------------------------
def empirical_liquidus(df: pd.DataFrame) -> pd.Series:
    """Common empirical liquidus correlation for low-alloy steels (°C):
    T_L = 1536 - (78C + 7.6Si + 4.9Mn + 34P + 30S + 5Cu + 3.1Ni + 1.3Cr + 3.6Al + 2Mo + 2V + 18Ti).
    Coefficients vary slightly between sources and the fit is only meaningful for C < ~1 wt%
    and modest alloying; it is used here as a reference trend, never as ground truth."""
    return 1536 - (
        78 * df["C"] + 7.6 * df["Si"] + 4.9 * df["Mn"] + 34 * df["P"] + 30 * df["S"] + 5 * df["Cu"]
        + 3.1 * df["Ni"] + 1.3 * df["Cr"] + 3.6 * df["Al"] + 2 * df["Mo"] + 2 * df["V"] + 18 * df["Ti"]
    )


LOW_ALLOY_FAMILIES = ["carbon", "alloy", "boron", "bearing", "spring", "nitriding", "weathering"]


@dataclass
class LiquidusEvidence:
    by_family: pd.DataFrame
    by_naming_source: pd.DataFrame
    by_name_format: pd.DataFrame
    carbon_bins: pd.DataFrame
    low_alloy: pd.DataFrame
    summary: dict


def liquidus_default_evidence(grades: pd.DataFrame, listings: pd.DataFrame) -> LiquidusEvidence:
    g = grades.copy()
    g["is_default"] = g["liquidus_c"] == DEFAULT_LIQUIDUS_C

    def share(frame: pd.DataFrame, by: str) -> pd.DataFrame:
        out = frame.groupby(by).agg(n=("is_default", "size"), n_1460=("is_default", "sum"),
                                    distinct_liquidus=("liquidus_c", "nunique"))
        out["share_1460"] = out["n_1460"] / out["n"]
        return out.sort_values("n", ascending=False)

    by_family = share(g, "family")
    by_source = share(g, "naming_source")
    lst = listings.assign(is_default=listings["liquidus_c"] == DEFAULT_LIQUIDUS_C)
    by_format = lst.groupby("name_format").agg(n=("is_default", "size"), n_1460=("is_default", "sum"))
    by_format["share_1460"] = by_format["n_1460"] / by_format["n"]

    low = g[g["family"].isin(LOW_ALLOY_FAMILIES) & (g["C"] <= 1.0)].copy()
    low["liquidus_empirical"] = empirical_liquidus(low)
    bins = pd.cut(low["C"], [0, 0.1, 0.2, 0.3, 0.45, 0.6, 1.0], include_lowest=True)
    carbon_bins = low.groupby(bins, observed=True).agg(
        n=("liquidus_c", "size"), share_1460=("is_default", "mean"),
        recorded_mean=("liquidus_c", "mean"), recorded_std=("liquidus_c", "std"),
        empirical_mean=("liquidus_empirical", "mean"))

    nd = low[~low["is_default"]]
    d = low[low["is_default"]]
    summary = {
        "n_grades_1460": int(g["is_default"].sum()),
        "share_grades_1460": float(g["is_default"].mean()),
        "n_listings_1460": int(lst["is_default"].sum()),
        "low_alloy_n": int(len(low)),
        "low_alloy_share_1460": float(low["is_default"].mean()),
        "corr_C_vs_recorded_nondefault": float(nd[["C", "liquidus_c"]].corr().iloc[0, 1]) if len(nd) > 2 else np.nan,
        "corr_empirical_vs_recorded_nondefault": float(nd[["liquidus_empirical", "liquidus_c"]].corr().iloc[0, 1]) if len(nd) > 2 else np.nan,
        "n_low_alloy_nondefault": int(len(nd)),
        "default_C_range": (float(d["C"].min()), float(d["C"].max())) if len(d) else (np.nan, np.nan),
        "default_empirical_range": (float(d["liquidus_empirical"].min()), float(d["liquidus_empirical"].max())) if len(d) else (np.nan, np.nan),
        "families_never_1460": by_family.index[by_family["n_1460"] == 0].tolist(),
    }
    return LiquidusEvidence(by_family, by_source, by_format, carbon_bins, low, summary)


# --------------------------------------------------------------------------------------------
# Irreducible error from processing (identical composition, different strength)
# --------------------------------------------------------------------------------------------
@dataclass
class IrreducibleError:
    oracle_mae: float
    oracle_rmse: float
    oracle_r2: float
    n_measured: int
    n_groups: int
    multi_member_groups: int
    multi_member_grades: int
    groups_with_spread: int
    within_group_mae: float
    within_group_rmse: float
    within_group_sd_pooled: float
    groups: pd.DataFrame

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "groups"}


def irreducible_error(grades: pd.DataFrame, group_col: str = "composition_group_id",
                      target: str = "tensile_strength_mpa") -> IrreducibleError:
    """Best any composition-only model can do: predict every grade with the mean TS of its
    composition group, in-sample. Singletons contribute zero error (their processing spread is
    unobservable), so the whole-dataset ceiling is optimistic; the multi-member statistics show
    the spread where it can actually be observed."""
    m = grades.dropna(subset=[target]).copy()
    m["_gm"] = m.groupby(group_col)[target].transform("mean")
    res = m[target] - m["_gm"]
    sst = ((m[target] - m[target].mean()) ** 2).sum()
    size = m.groupby(group_col)[target].transform("size")
    mm = m[size > 1]
    rmm = mm[target] - mm["_gm"]
    groups = mm.groupby(group_col).agg(
        n=(target, "size"), ts_min=(target, "min"), ts_max=(target, "max"), ts_sd=(target, "std"),
        family=("family", "first"), example=("display_name", "first"))
    groups["ts_range"] = groups["ts_max"] - groups["ts_min"]
    dof = int((groups["n"] - 1).sum())
    pooled = float(np.sqrt((rmm ** 2).sum() / dof)) if dof else 0.0
    return IrreducibleError(
        oracle_mae=float(res.abs().mean()), oracle_rmse=float(np.sqrt((res ** 2).mean())),
        oracle_r2=float(1 - (res ** 2).sum() / sst), n_measured=int(len(m)), n_groups=int(m[group_col].nunique()),
        multi_member_groups=int(len(groups)), multi_member_grades=int(len(mm)),
        groups_with_spread=int((groups["ts_range"] > 0).sum()),
        within_group_mae=float(rmm.abs().mean()), within_group_rmse=float(np.sqrt((rmm ** 2).mean())),
        within_group_sd_pooled=pooled,
        groups=groups.sort_values("ts_range", ascending=False))


# --------------------------------------------------------------------------------------------
# With vs without imputed rows
# --------------------------------------------------------------------------------------------
SENSITIVITY_ELEMENTS = ["C", "Mn", "Cr", "Ni", "Mo", "V", "Co"]


def _summary(ts: pd.Series, comp: pd.DataFrame, family: pd.Series, label: str) -> dict:
    out = {
        "scenario": label, "n": int(ts.notna().sum()), "ts_mean": ts.mean(), "ts_median": ts.median(),
        "ts_sd": ts.std(), "share_high_class": float((ts > 600).mean()), "share_low_class": float((ts < 300).mean()),
    }
    for el in SENSITIVITY_ELEMENTS:
        out[f"spearman_{el}"] = ts.corr(comp[el], method="spearman")
    out["spearman_CE"] = ts.corr(comp["carbon_equivalent"], method="spearman")
    fam_med = ts.groupby(family).median()
    for fam in ["carbon", "alloy", "stainless", "tool", "cast_iron_grey"]:
        out[f"median_{fam}"] = fam_med.get(fam, np.nan)
    return out


def imputation_sensitivity(listings: pd.DataFrame, grades: pd.DataFrame) -> pd.DataFrame:
    """Three ways to read strength:
    A. naive: every de-duplicated row, imputed constant treated as a measurement
    B. listing level, imputed rows dropped (twins still double-count most grades)
    C. grade level, measured only (the project's analysis unit)."""
    lst = listings.merge(grades[["grade_id", "carbon_equivalent"]], on="grade_id", how="left")
    a = _summary(lst["tensile_strength_raw"], lst, lst["family"], "A. naive rows (imputed kept)")
    keep = ~lst["is_imputed_ts"]
    b = _summary(lst.loc[keep, "tensile_strength_raw"], lst[keep], lst.loc[keep, "family"],
                 "B. rows, imputed dropped")
    gm = grades.dropna(subset=["tensile_strength_mpa"])
    c = _summary(gm["tensile_strength_mpa"], gm, gm["family"], "C. grades, measured (used)")
    return pd.DataFrame([a, b, c]).set_index("scenario")


def composition_sum_summary(grades: pd.DataFrame) -> dict:
    s = grades[ELEMENTS].sum(axis=1)
    return {"min": float(s.min()), "max": float(s.max()), "median": float(s.median()),
            "share_within_1pct": float(((s >= 99) & (s <= 101)).mean()),
            "n_outside_1pct": int(((s < 99) | (s > 101)).sum())}
