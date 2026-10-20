"""Statistics behind the visual-analytics notebook (03) and the Tableau / KNIME guides.

Every function returns plain DataFrames / dicts so the same numbers feed the figures, the Tableau helper
CSVs and the "expected values" quoted in the KNIME guide.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA

from .constants import ELEMENTS, RANDOM_STATE
from .features import FAMILY_GROUP_ORDER, PLAIN_STEEL_FAMILIES, family_group

TS = "tensile_strength_mpa"
SUMMARY_VARS = {
    TS: ("Tensile strength", "MPa"), "liquidus_c": ("Liquidus", "°C"),
    "carbon_equivalent": ("Carbon equivalent", "wt%"), "alloying_total": ("Alloying total", "wt%"),
    "C": ("Carbon", "wt%"), "Mn": ("Manganese", "wt%"), "Cr": ("Chromium", "wt%"),
    "Ni": ("Nickel", "wt%"), "Mo": ("Molybdenum", "wt%"),
}
CLASS_NAMES = {0: "Low (<300)", 1: "Medium (300-600)", 2: "High (>600)"}


def with_groups(grades: pd.DataFrame) -> pd.DataFrame:
    g = grades.copy()
    g["family_group"] = family_group(g["family"])
    return g


# ------------------------------------------------------------------------------- 1. summaries
def five_number_summary(df: pd.DataFrame, cols=tuple(SUMMARY_VARS)) -> pd.DataFrame:
    """Tukey five-number summary + IQR fences and outlier counts (NaNs ignored per column)."""
    rows = []
    for c in cols:
        s = df[c].dropna()
        q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        rows.append({"variable": c, "label": SUMMARY_VARS.get(c, (c, ""))[0], "unit": SUMMARY_VARS.get(c, ("", ""))[1],
                     "n": len(s), "min": s.min(), "Q1": q1, "median": med, "Q3": q3, "max": s.max(), "IQR": iqr,
                     "lower_fence": lo, "upper_fence": hi, "n_outliers": int(((s < lo) | (s > hi)).sum())})
    return pd.DataFrame(rows).set_index("variable")


def descriptive_stats(df: pd.DataFrame, cols=tuple(SUMMARY_VARS)) -> pd.DataFrame:
    rows = []
    for c in cols:
        s = df[c].dropna()
        rows.append({"variable": c, "n": len(s), "missing": int(df[c].isna().sum()), "mean": s.mean(), "sd": s.std(),
                     "cv_pct": 100 * s.std() / s.mean() if s.mean() else np.nan, "skewness": stats.skew(s),
                     "kurtosis_excess": stats.kurtosis(s), "mode": s.round(2).mode().iloc[0], "range": s.max() - s.min(),
                     "share_zero": float((s == 0).mean())})
    return pd.DataFrame(rows).set_index("variable")


def summary_by_group(df: pd.DataFrame, col: str = TS, by: str = "family_group") -> pd.DataFrame:
    g = df.dropna(subset=[col]).groupby(by)[col]
    out = g.describe()[["count", "min", "25%", "50%", "75%", "max", "mean", "std"]]
    return out.rename(columns={"25%": "Q1", "50%": "median", "75%": "Q3"}).sort_values("median")


# --------------------------------------------------------------------------------- 2. binning
CARBON_BANDS = ([-np.inf, 0.25, 0.60, 2.10, np.inf],
                ["Low carbon (≤0.25)", "Medium carbon (0.25–0.60)", "High carbon / tool (0.60–2.1)", "Cast-iron range (>2.1)"])
CE_BANDS = ([-np.inf, 0.40, 0.60, np.inf], ["Readily weldable (CE ≤0.40)", "Preheat advised (0.40–0.60)", "Difficult (CE >0.60)"])
ALLOY_BANDS = ([-np.inf, 5, 10, 30, np.inf], ["Lean (<5 %)", "Medium (5–10 %)", "High (10–30 %)", "Very high (>30 %)"])


def add_bins(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["carbon_band"] = pd.cut(out["C"], CARBON_BANDS[0], labels=CARBON_BANDS[1], right=True)
    out["ce_band"] = pd.cut(out["carbon_equivalent"], CE_BANDS[0], labels=CE_BANDS[1], right=True)
    out["alloy_band"] = pd.cut(out["alloying_total"], ALLOY_BANDS[0], labels=ALLOY_BANDS[1], right=False)
    ts = out[TS]
    out["ts_bin_equal_width"] = pd.cut(ts, bins=8)
    out["ts_bin_quintile"] = pd.qcut(ts, q=5)
    return out


def binning_comparison(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Equal-width vs equal-frequency binning of TS: same k, very different bins on a skewed variable."""
    ts = df[TS].dropna()
    ew = pd.cut(ts, bins=k)
    ef = pd.qcut(ts, q=k)
    a = ew.value_counts(sort=False).rename_axis("bin").reset_index(name="n")
    b = ef.value_counts(sort=False).rename_axis("bin").reset_index(name="n")
    a["method"], b["method"] = "equal width", "equal frequency (quantile)"
    out = pd.concat([a, b], ignore_index=True)
    out["low"] = [iv.left for iv in out["bin"]]
    out["high"] = [iv.right for iv in out["bin"]]
    out["bin"] = out["bin"].astype(str)
    return out


# ------------------------------------------------------------------------------ 3. chi-square
@dataclass
class ChiSquareResult:
    name: str
    row: str
    col: str
    observed: pd.DataFrame
    expected: pd.DataFrame
    std_residuals: pd.DataFrame
    chi2: float
    dof: int
    p_value: float
    cramers_v: float
    share_expected_lt5: float
    n: int
    p_permutation: float
    n_permutations: int

    @property
    def asymptotic_valid(self) -> bool:
        """Cochran's rule: at most 20 % of cells with expected count < 5."""
        return self.share_expected_lt5 <= 0.20

    def as_row(self) -> dict:
        return {"test": self.name, "rows": self.row, "columns": self.col, "n": self.n, "chi2": self.chi2, "dof": self.dof,
                "p_value": self.p_value, "p_permutation": self.p_permutation, "cramers_v": self.cramers_v,
                "share_expected_lt5": self.share_expected_lt5, "asymptotic_valid": self.asymptotic_valid}


def chi_square(df: pd.DataFrame, row: str, col: str, name: str, n_perm: int = 2000) -> ChiSquareResult:
    """Pearson chi-square test of independence + Cramér's V + a Monte-Carlo permutation p-value, which stays
    valid when many expected counts are small (the low strength class has only a few grades)."""
    d = df[[row, col]].dropna()
    obs = pd.crosstab(d[row], d[col])
    obs = obs.loc[obs.sum(axis=1) > 0, obs.sum(axis=0) > 0]
    ordered = [c for c in CLASS_NAMES.values() if c in obs.columns]
    if len(ordered) == obs.shape[1]:          # strength classes read low -> high, not alphabetically
        obs = obs[ordered]
    chi2, p, dof, exp = stats.chi2_contingency(obs.values, correction=False)
    exp = pd.DataFrame(exp, index=obs.index, columns=obs.columns)
    n = int(obs.values.sum())
    v = float(np.sqrt(chi2 / (n * (min(obs.shape) - 1))))
    rng = np.random.default_rng(RANDOM_STATE)
    r_codes = pd.Categorical(d[row], categories=obs.index).codes
    c_codes = pd.Categorical(d[col], categories=obs.columns).codes
    keep = (r_codes >= 0) & (c_codes >= 0)
    r_codes, c_codes = r_codes[keep], c_codes[keep]
    ev = exp.to_numpy()
    exceed = 0
    for _ in range(n_perm):
        perm = np.zeros_like(ev)
        np.add.at(perm, (r_codes, rng.permutation(c_codes)), 1)
        exceed += ((perm - ev) ** 2 / ev).sum() >= chi2
    return ChiSquareResult(name, row, col, obs, exp, (obs - exp) / np.sqrt(exp), float(chi2), int(dof), float(p), v,
                           float((exp.values < 5).mean()), n, (exceed + 1) / (n_perm + 1), n_perm)


def chi_square_suite(grades: pd.DataFrame) -> list[ChiSquareResult]:
    g = add_bins(with_groups(grades))
    m = g.dropna(subset=[TS]).copy()
    m["strength_class_name"] = m["strength_class"].astype(int).map(CLASS_NAMES)
    plain = m[m["family"].isin(PLAIN_STEEL_FAMILIES)]
    return [
        chi_square(m, "family_group", "strength_class_name", "Family group × strength class"),
        chi_square(m, "product_form", "strength_class_name", "Product form × strength class"),
        chi_square(m, "carbon_band", "strength_class_name", "Carbon band × strength class"),
        chi_square(plain, "ce_band", "strength_class_name", "CE weldability band × strength class (plain steels)"),
        chi_square(g, "family_group", "liquidus_is_default", "Family group × default liquidus"),
    ]


# ------------------------------------------------------------------------------ 4. regression
@dataclass
class OLSResult:
    terms: list[str]
    coef: np.ndarray
    se: np.ndarray
    t: np.ndarray
    p: np.ndarray
    ci_low: np.ndarray
    ci_high: np.ndarray
    r2: float
    adj_r2: float
    f_stat: float
    f_p: float
    n: int
    fitted: np.ndarray
    resid: np.ndarray
    sigma: float
    XtX_inv: np.ndarray

    def table(self) -> pd.DataFrame:
        return pd.DataFrame({"coef": self.coef, "std_err": self.se, "t": self.t, "p_value": self.p,
                             "ci95_low": self.ci_low, "ci95_high": self.ci_high}, index=self.terms)


def ols(X: pd.DataFrame, y: pd.Series) -> OLSResult:
    """Ordinary least squares with an intercept; classical (homoscedastic) standard errors."""
    Xm = np.column_stack([np.ones(len(X)), X.to_numpy(float)])
    yv = y.to_numpy(float)
    XtX_inv = np.linalg.pinv(Xm.T @ Xm)
    beta = XtX_inv @ Xm.T @ yv
    fitted = Xm @ beta
    resid = yv - fitted
    n, p = Xm.shape
    dof = n - p
    sigma2 = resid @ resid / dof
    se = np.sqrt(np.diag(XtX_inv) * sigma2)
    t = beta / se
    pv = 2 * stats.t.sf(np.abs(t), dof)
    tcrit = stats.t.ppf(0.975, dof)
    sst = ((yv - yv.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / sst
    adj = 1 - (1 - r2) * (n - 1) / dof
    f = (r2 / (p - 1)) / ((1 - r2) / dof)
    return OLSResult(["Intercept", *X.columns], beta, se, t, pv, beta - tcrit * se, beta + tcrit * se, float(r2),
                     float(adj), float(f), float(stats.f.sf(f, p - 1, dof)), n, fitted, resid, float(np.sqrt(sigma2)), XtX_inv)


def simple_regression_bands(res: OLSResult, xgrid: np.ndarray) -> pd.DataFrame:
    """95 % confidence band for the mean and 95 % prediction band for a single new grade."""
    Xg = np.column_stack([np.ones(len(xgrid)), xgrid])
    yhat = Xg @ res.coef
    h = np.einsum("ij,jk,ik->i", Xg, res.XtX_inv, Xg)
    tcrit = stats.t.ppf(0.975, res.n - 2)
    return pd.DataFrame({"x": xgrid, "fit": yhat,
                         "ci_low": yhat - tcrit * res.sigma * np.sqrt(h), "ci_high": yhat + tcrit * res.sigma * np.sqrt(h),
                         "pi_low": yhat - tcrit * res.sigma * np.sqrt(1 + h), "pi_high": yhat + tcrit * res.sigma * np.sqrt(1 + h)})


REG_ELEMENTS = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V"]


def regression_suite(grades: pd.DataFrame) -> dict:
    m = grades.dropna(subset=[TS])
    carbon = m[(m["family"] == "carbon") & (m["C"] <= 1.0)]
    simple = ols(carbon[["C"]], carbon[TS])
    plain = m[m["family"].isin(PLAIN_STEEL_FAMILIES) & (m["C"] <= 1.0)]
    multi = ols(plain[REG_ELEMENTS], plain[TS])
    z = (plain[REG_ELEMENTS] - plain[REG_ELEMENTS].mean()) / plain[REG_ELEMENTS].std()
    std_multi = ols(z, (plain[TS] - plain[TS].mean()) / plain[TS].std())
    return {"carbon": carbon, "simple": simple, "plain": plain, "multi": multi, "std_multi": std_multi}


# ------------------------------------------------------------------------------------- 5. PCA
def composition_space(grades: pd.DataFrame, rare: list[str]) -> tuple[np.ndarray, list[str]]:
    """log1p + z-score of every non-rare element except Fe (redundant with the others) plus summed trace elements."""
    feats = [el for el in ELEMENTS if el not in rare and el != "Fe"] + ["trace_total"]
    T = np.log1p(grades[feats].to_numpy(dtype=float))
    sd = T.std(axis=0)
    return (T - T.mean(axis=0)) / np.where(sd > 0, sd, 1.0), feats


def pca_analysis(X: np.ndarray, feats: list[str]) -> dict:
    pca = PCA(random_state=RANDOM_STATE).fit(X)
    scores = pca.transform(X)
    loadings = pd.DataFrame(pca.components_.T * np.sqrt(pca.explained_variance_), index=feats,
                            columns=[f"PC{i + 1}" for i in range(len(feats))])
    ev = pd.DataFrame({"component": [f"PC{i + 1}" for i in range(len(feats))],
                       "explained_variance_ratio": pca.explained_variance_ratio_,
                       "cumulative": np.cumsum(pca.explained_variance_ratio_), "eigenvalue": pca.explained_variance_})
    return {"scores": scores, "loadings": loadings, "explained": ev,
            "n_for_80pct": int(np.searchsorted(ev["cumulative"].to_numpy(), 0.80) + 1),
            "n_kaiser": int((pca.explained_variance_ > 1).sum())}


# ------------------------------------------------------------------------- 6. migration flow
def flow_raw_class_to_outcome(raw: pd.DataFrame, listings: pd.DataFrame, grades: pd.DataFrame) -> pd.DataFrame:
    """Where every raw row's Class ends up after cleaning: a 'migration' from raw label to cleaned outcome."""
    dup = raw.duplicated()
    rows = [{"source": f"Raw class {c}", "target": "Dropped: exact duplicate", "value": int(n)}
            for c, n in raw.loc[dup, "Class"].value_counts().items()]
    lst = listings.copy()
    lst["_rank"] = (lst["name_format"] != "spaced").astype(int)
    lst = lst.sort_values(["canonical_grade", "_rank", "raw_name"])
    rep = ~lst.duplicated("canonical_grade")
    gcls = grades.set_index("grade_id")["strength_class"]
    tgt = np.where(~rep, "Merged into twin listing",
                   lst["grade_id"].map(gcls).map(lambda c: "Unmeasured TS (excluded)" if pd.isna(c) else f"Grade class {int(c)}"))
    f = pd.DataFrame({"source": "Raw class " + lst["class_original"].astype(str), "target": tgt})
    rows += f.groupby(["source", "target"]).size().rename("value").reset_index().to_dict("records")
    return pd.DataFrame(rows).groupby(["source", "target"], as_index=False)["value"].sum()


# ----------------------------------------------------------------------------- 7. radar data
RADAR_ELEMENTS = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu"]
RADAR_PROPERTIES = {TS: "Tensile strength", "liquidus_c": "Liquidus", "carbon_equivalent": "Carbon eq.",
                    "alloying_total": "Alloy content", "C": "C", "Cr": "Cr", "Ni": "Ni", "Mo": "Mo"}
SHOWCASE_GRADES = {   # short name -> display-name prefix (one radar panel each)
    "AISI 1018": "SAE-AISI 1018 (G10180)",
    "AISI 1045": "SAE-AISI 1045 (S45C,G10450)",
    "AISI 4140": "SAE-AISI 4140 (SCM440,G41400)",
    "AISI 304": "AISI 304 (S30400)",
    "AISI 316": "AISI 316 (S31600)",
    "17-4 PH": "UNS S17400 (17-4 PH,Alloy 630)",
    "M2 high-speed": "SAE-AISI M2 (T11302)",
    "Grey iron 250": "ASTM Grade 35 or 250",
    "Maraging 300 (aged)": "Aged Grade 300 Maraging",
}


def radar_family_composition(grades: pd.DataFrame) -> pd.DataFrame:
    """Median composition per family group, log1p-scaled then min-max per element across groups (0-1)."""
    g = with_groups(grades)
    med = g.groupby("family_group")[RADAR_ELEMENTS].median().reindex([x for x in FAMILY_GROUP_ORDER if x in set(g["family_group"])])
    lg = np.log1p(med)
    rng = (lg.max() - lg.min()).replace(0, 1)
    return (lg - lg.min()) / rng, med


def showcase_grades(grades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for short, prefix in SHOWCASE_GRADES.items():
        hit = grades[grades["display_name"].str.startswith(prefix)]
        if len(hit):
            rows.append(hit.iloc[0].to_dict() | {"short_name": short})
    return pd.DataFrame(rows)


def radar_grade_percentiles(grades: pd.DataFrame, picks: pd.DataFrame) -> pd.DataFrame:
    """Each property as the grade's percentile rank among all grades (0-100), so different units share an axis."""
    out = {}
    for _, r in picks.iterrows():
        vals = {}
        for col, label in RADAR_PROPERTIES.items():
            s = grades[col].dropna()
            vals[label] = float(100 * (s <= r[col]).mean()) if pd.notna(r[col]) else np.nan
        out[r["short_name"]] = vals
    return pd.DataFrame(out).T


# ------------------------------------------------------------------------------- 8. waterfalls
def waterfall_cleaning(log_counts: dict) -> pd.DataFrame:
    return pd.DataFrame([
        {"step": "Raw rows", "value": log_counts["raw"], "kind": "total"},
        {"step": "Exact duplicates", "value": -log_counts["duplicates"], "kind": "delta"},
        {"step": "Twin listings merged", "value": -log_counts["twins"], "kind": "delta"},
        {"step": "Canonical grades", "value": log_counts["grades"], "kind": "total"},
        {"step": "No measured TS", "value": -log_counts["unmeasured"], "kind": "delta"},
        {"step": "Modelled grades", "value": log_counts["measured"], "kind": "total"},
    ])


def waterfall_ce(row: pd.Series) -> pd.DataFrame:
    """IIW carbon equivalent built up term by term for one grade."""
    terms = [("C", row["C"]), ("Mn / 6", row["Mn"] / 6), ("Cr / 5", row["Cr"] / 5), ("Mo / 5", row["Mo"] / 5),
             ("V / 5", row["V"] / 5), ("Ni / 15", row["Ni"] / 15), ("Cu / 15", row["Cu"] / 15)]
    df = pd.DataFrame([{"step": s, "value": v, "kind": "delta"} for s, v in terms])
    total = pd.DataFrame([{"step": "Carbon equivalent", "value": float(df["value"].sum()), "kind": "total"}])
    return pd.concat([df, total], ignore_index=True)


def waterfall_layout(wf: pd.DataFrame) -> pd.DataFrame:
    """Bar bottoms/tops for drawing: totals start at 0, deltas start where the running total stands."""
    out = wf.copy()
    run, bottoms, tops = 0.0, [], []
    for _, r in out.iterrows():
        if r["kind"] == "total":
            run = r["value"]
            bottoms.append(0.0)
            tops.append(run)
        else:
            bottoms.append(run)
            run += r["value"]
            tops.append(run)
    out["start"], out["end"] = bottoms, tops
    out["running_total"] = out["end"]
    return out
