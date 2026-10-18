"""Question-driven EDA statistics. Figures live in viz_eda.py; this module only computes."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .features import CAST_IRON_FAMILIES, PLAIN_STEEL_FAMILIES

TS = "tensile_strength_mpa"

FAMILY_GROUPS: dict[str, list[str] | None] = {
    "All grades": None,
    "Carbon & low-alloy": PLAIN_STEEL_FAMILIES,
    "Stainless": ["stainless"],
    "Tool & high-speed": ["tool", "high_speed"],
    "Cast irons": CAST_IRON_FAMILIES,
    "Weld metal": ["weld_metal"],
}
CORRELATION_FEATURES = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu", "N", "Nb", "Ti", "Al",
                        "carbon_equivalent", "alloying_total"]


def measured(grades: pd.DataFrame) -> pd.DataFrame:
    """Grades with a measured tensile strength (the only rows used for strength statistics)."""
    return grades[grades[TS].notna()].copy()


def subset(grades: pd.DataFrame, families: list[str] | None) -> pd.DataFrame:
    return grades if families is None else grades[grades["family"].isin(families)]


# ---------------------------------------------------------------------------------- Q1 family
def family_strength_table(grades: pd.DataFrame) -> pd.DataFrame:
    m = measured(grades)
    t = m.groupby(["family", "family_label"])[TS].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    t = t.rename(columns={"count": "n", "10%": "p10", "25%": "p25", "50%": "median", "75%": "p75", "90%": "p90"})
    t["iqr"] = t["p75"] - t["p25"]
    return t[["n", "min", "p10", "p25", "median", "p75", "p90", "max", "iqr"]].reset_index().sort_values("median")


def kruskal_family(grades: pd.DataFrame) -> dict:
    m = measured(grades)
    samples = [g[TS].values for _, g in m.groupby("family") if len(g) >= 5]
    h, p = stats.kruskal(*samples)
    n, k = sum(len(s) for s in samples), len(samples)
    return {"H": float(h), "p_value": float(p), "epsilon_sq": float((h - k + 1) / (n - k)), "n_families": k}


# ---------------------------------------------------------------------------- Q2 correlations
def element_correlations(grades: pd.DataFrame, features: list[str] = CORRELATION_FEATURES,
                         min_nonzero: int = 8) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Spearman rho of each feature with TS, overall and within family groups.
    A cell is NaN when the feature is (near-)constant in the group (< min_nonzero distinct non-zero values)."""
    m = measured(grades)
    rho, pval, sizes = {}, {}, {}
    for name, fams in FAMILY_GROUPS.items():
        s = subset(m, fams)
        sizes[name] = len(s)
        r_col, p_col = {}, {}
        for f in features:
            if (s[f] > 0).sum() < min_nonzero or s[f].nunique() < 3:
                r_col[f], p_col[f] = np.nan, np.nan
                continue
            r, p = stats.spearmanr(s[f], s[TS])
            r_col[f], p_col[f] = r, p
        rho[name], pval[name] = r_col, p_col
    return pd.DataFrame(rho), pd.DataFrame(pval), pd.Series(sizes, name="n")


def carbon_effect(grades: pd.DataFrame, max_c: float = 1.0) -> dict:
    """Carbon vs strength pooled vs within carbon & low-alloy steels (Simpson's paradox check)."""
    m = measured(grades)
    plain = m[m["family"].isin(PLAIN_STEEL_FAMILIES) & (m["C"] <= max_c)]
    carbon_only = m[(m["family"] == "carbon") & (m["C"] <= max_c)]
    slope = stats.theilslopes(carbon_only[TS], carbon_only["C"])
    return {
        "rho_all": float(stats.spearmanr(m["C"], m[TS])[0]), "n_all": int(len(m)),
        "rho_plain": float(stats.spearmanr(plain["C"], plain[TS])[0]), "n_plain": int(len(plain)),
        "rho_carbon_family": float(stats.spearmanr(carbon_only["C"], carbon_only[TS])[0]),
        "n_carbon_family": int(len(carbon_only)),
        "theil_sen_mpa_per_0p1C": float(slope.slope / 10),
        "theil_sen_ci_per_0p1C": (float(slope.low_slope / 10), float(slope.high_slope / 10)),
        "median_C_cast_iron": float(m.loc[m["family"].str.startswith("cast_iron"), "C"].median()),
        "median_TS_cast_iron": float(m.loc[m["family"].str.startswith("cast_iron"), TS].median()),
    }


# ------------------------------------------------------------------------------- Q3 stainless
def stainless_subgroup(df: pd.DataFrame) -> pd.Series:
    """Approximate composition-based stainless subgroups (Ni and Cr thresholds)."""
    return pd.Series(np.select(
        [df["Ni"] >= 8, (df["Ni"] >= 3) & (df["Cr"] >= 20), df["Ni"] >= 3],
        ["Austenitic (Ni ≥ 8)", "Duplex-type (Cr ≥ 20, Ni 3–8)", "Ni-bearing martensitic / PH (Ni 3–8, Cr < 20)"],
        "Ferritic / martensitic (Ni < 3)"), index=df.index)


def stainless_profile(grades: pd.DataFrame) -> pd.DataFrame:
    s = measured(grades)
    s = s[s["family"] == "stainless"].copy()
    s["subgroup"] = stainless_subgroup(s)
    t = s.groupby("subgroup").agg(n=(TS, "size"), median_ts=(TS, "median"), p25=(TS, lambda v: v.quantile(.25)),
                                  p75=(TS, lambda v: v.quantile(.75)), median_cr=("Cr", "median"),
                                  median_ni=("Ni", "median"), median_n=("N", "median"),
                                  median_alloying=("alloying_total", "median"))
    return t.sort_values("median_ts")


# ------------------------------------------------------------------------------------ Q4 CE
def ce_by_group(grades: pd.DataFrame) -> pd.DataFrame:
    m = measured(grades)
    rows = []
    for name, fams in FAMILY_GROUPS.items():
        s = subset(m, fams)
        r, p = stats.spearmanr(s["carbon_equivalent"], s[TS])
        rows.append({"group": name, "n": len(s), "rho_CE": r, "p_value": p,
                     "median_CE": s["carbon_equivalent"].median()})
    return pd.DataFrame(rows).set_index("group")


# ---------------------------------------------------------------------------- Q5 design space
def design_space_stats(grades: pd.DataFrame) -> dict:
    m = measured(grades)
    nd = m[~m["liquidus_is_default"]]
    return {
        "pearson_all": float(m[[TS, "liquidus_c"]].corr().iloc[0, 1]),
        "spearman_all": float(stats.spearmanr(m[TS], m["liquidus_c"])[0]),
        "n_all": int(len(m)),
        "pearson_non_default": float(nd[[TS, "liquidus_c"]].corr().iloc[0, 1]),
        "spearman_non_default": float(stats.spearmanr(nd[TS], nd["liquidus_c"])[0]),
        "n_non_default": int(len(nd)),
        "liquidus_range": (float(m["liquidus_c"].min()), float(m["liquidus_c"].max())),
        "ts_range": (float(m[TS].min()), float(m[TS].max())),
    }


def design_space_by_family(grades: pd.DataFrame) -> pd.DataFrame:
    m = measured(grades)
    return m.groupby("family_label").agg(
        n=(TS, "size"), ts_p10=(TS, lambda v: v.quantile(.1)), ts_p90=(TS, lambda v: v.quantile(.9)),
        liq_p10=("liquidus_c", lambda v: v.quantile(.1)), liq_p90=("liquidus_c", lambda v: v.quantile(.9)),
        share_default_liq=("liquidus_is_default", "mean")).sort_values("ts_p90")


def target_design_query(grades: pd.DataFrame, ts_min: float, ts_max: float, liq_min: float, liq_max: float,
                        exclude_default_liquidus: bool = False,
                        envelope_elements: tuple[str, ...] = ("C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu", "N")):
    """Grades achieving a strength band and liquidus range, the families that do it, and the composition
    envelope (P10/P50/P90 wt%) of the matching grades."""
    m = measured(grades)
    q = m[m[TS].between(ts_min, ts_max) & m["liquidus_c"].between(liq_min, liq_max)]
    if exclude_default_liquidus:
        q = q[~q["liquidus_is_default"]]
    fam = q["family_label"].value_counts().rename("n").to_frame()
    fam["share"] = fam["n"] / max(len(q), 1)
    cols = list(envelope_elements) + ["alloying_total", "carbon_equivalent"]
    env = q[cols].quantile([0.1, 0.5, 0.9]).T.rename(columns={0.1: "p10", 0.5: "p50", 0.9: "p90"})
    return q, fam, env


# ----------------------------------------------------------------------------- Q6 class drivers
# Schaeffler Cr/Ni equivalents are left out: for cast irons they are dominated by 30*C and mislead.
CLASS_FEATURES = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "N", "carbon_equivalent", "alloying_total"]


def class_separation(grades: pd.DataFrame, features: list[str] = CLASS_FEATURES) -> pd.DataFrame:
    """Kruskal-Wallis across the three classes for each feature, ranked by epsilon-squared effect size."""
    m = measured(grades)
    rows = []
    for f in features:
        samples = [g[f].values for _, g in m.groupby("strength_class")]
        h, p = stats.kruskal(*samples)
        n, k = len(m), len(samples)
        med = m.groupby("strength_class")[f].median()
        nz = m.groupby("strength_class")[f].apply(lambda v: (v > 0).mean())
        rows.append({"feature": f, "epsilon_sq": (h - k + 1) / (n - k), "H": h, "p_value": p,
                     "median_low": med.get(0), "median_medium": med.get(1), "median_high": med.get(2),
                     "share_nonzero_low": nz.get(0), "share_nonzero_medium": nz.get(1), "share_nonzero_high": nz.get(2)})
    return pd.DataFrame(rows).set_index("feature").sort_values("epsilon_sq", ascending=False)


def class_family_mix(grades: pd.DataFrame) -> pd.DataFrame:
    m = measured(grades)
    return pd.crosstab(m["family_label"], m["strength_class_label"])
