"""Exports for Tableau and KNIME (machine learning itself is done in KNIME, not here).

    python -m src.analysis.exports
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from .cleaning import load_clean_grades, load_pipeline_meta
from .constants import ELEMENTS, EXPORTS_KNIME, EXPORTS_TABLEAU, RANDOM_STATE
from .features import family_group

logger = logging.getLogger("steelscope.exports")
TS = "tensile_strength_mpa"


# ------------------------------------------------------------------------------------- Tableau
def steels_wide(grades: pd.DataFrame) -> pd.DataFrame:
    w = grades.copy()
    w.insert(w.columns.get_loc("family_label") + 1, "family_group", family_group(w["family"]))
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
              share_shared_composition=("shares_composition", "mean"))
    return s.reset_index().sort_values("ts_median")


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
    """Model-ready table for KNIME. Rows are ordered train -> test -> unmeasured so that, after KNIME's Row Filter
    drops the imputed rows, Partitioning with 'Take from top' reproduces the group-safe `split` column exactly."""
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


# ---------------------------------------------------------------------------------- orchestration
def build_all() -> dict:
    grades = load_clean_grades()
    rare = load_pipeline_meta()["rare_elements"]
    EXPORTS_TABLEAU.mkdir(parents=True, exist_ok=True)
    EXPORTS_KNIME.mkdir(parents=True, exist_ok=True)
    wide = steels_wide(grades)
    files = {
        EXPORTS_TABLEAU / "steels_wide.csv": wide,
        EXPORTS_TABLEAU / "steels_long.csv": steels_long(grades, rare),
        EXPORTS_TABLEAU / "family_summary.csv": family_summary(wide),
        EXPORTS_KNIME / "knime_input.csv": knime_input(grades, rare),
    }
    for path, df in files.items():
        df.to_csv(path, index=False)
        logger.info("%-40s %6d rows x %3d cols", f"{path.parent.name}/{path.name}", len(df), df.shape[1])
    return {p.name: df for p, df in files.items()}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_all()


if __name__ == "__main__":
    main()
