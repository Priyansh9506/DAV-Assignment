"""Cell definitions for the project notebooks (consumed by build_notebooks.py).

Markdown cells explain reasoning; every number shown in a notebook is printed by a code cell.
"""

SETUP = r'''
import sys, warnings
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 80)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")

from src.analysis import plotting as P
P.apply_theme()

def show(fig, name):
    path = P.save(fig, name)
    display(Image(filename=str(path)))
'''

# =============================================================================================
# 01 Cleaning
# =============================================================================================
NB01 = [
    ("md", r'''
# 01 · Data cleaning & feature engineering

**SteelScope**: composition-to-performance intelligence for steels & iron alloys.

This notebook runs the reusable pipeline in `src/analysis/cleaning.py` and shows the evidence behind
each decision. No cleaning logic lives here: if a number below changes, it changed in the pipeline.

**Unit of analysis.** The raw file lists each grade up to twice (a spaced and a hyphenated name).
After the investigation below, the analysis unit is the **canonical grade**: one row per grade, with
tensile strength taken only from measured listings.
'''),
    ("code", SETUP),
    ("md", "## 1 · Run the pipeline\n\nEvery step records the row count before and after."),
    ("code", r'''
from src.analysis.cleaning import run_cleaning, save_outputs, canonical_key
from src.analysis.constants import ELEMENTS, RAW_TS, IMPUTED_TS_VALUE
result = run_cleaning()
grades, listings, log = result.grades, result.listings, result.log
log.to_frame()
'''),
    ("md", "## 2 · Raw data at a glance"),
    ("code", r'''
raw = pd.read_csv(ROOT / "data/raw/Alloys.csv")
print("shape:", raw.shape, "| nulls:", int(raw.isna().sum().sum()), "| Fe min/max:", raw["Fe"].min(), raw["Fe"].max())
raw.head(3)
'''),
    ("md", r'''
Every row is iron-based, so the domain is **steels & iron alloys**: carbon, alloy, stainless, tool,
high-speed, maraging, cast iron, weld metal and a few Fe-Ni special alloys. It is not "alloys" in general.

## 3 · Exact duplicates

Full-row duplicates carry no information and would leak across cross-validation folds. **Decision: drop.**
'''),
    ("code", r'''
print("exact duplicate rows:", int(raw.duplicated().sum()))
log.get("drop_exact_duplicates")
'''),
    ("md", r'''
## 4 · Imputed tensile strength

One value appears far more often than any real measurement and equals the column mean to six decimals.
It was mean-imputed upstream, not measured.
'''),
    ("code", r'''
dedup = raw.drop_duplicates()
print("raw TS column mean:", raw[RAW_TS].mean())
print(dedup[RAW_TS].value_counts().head(4))
print("\nimputed rows (de-duplicated):", int(listings["is_imputed_ts"].sum()),
      f"= {listings['is_imputed_ts'].mean():.1%} of {len(listings)} rows;",
      f"{np.isclose(raw[RAW_TS], IMPUTED_TS_VALUE, atol=1e-4).mean():.1%} of the {len(raw)} raw rows")
print("original Class of imputed rows:", listings.loc[listings.is_imputed_ts, "class_original"].value_counts().to_dict())
'''),
    ("md", r'''
Every imputed row landed in Class 2, because the original `Class` is just binned TS and 652 MPa falls in
the top bin. Two consequences:

* **Never** use TS as a feature to predict `Class` (it *is* the class, so that is leakage).
* `Class` must be recomputed from measured TS only (section 7).

## 5 · Twin listings → canonical grade

The same grade appears under two naming formats. Normalising the name (lowercase, every
non-alphanumeric run → one separator) merges them:
'''),
    ("code", r'''
for n in ["EN 1.0420 (GE200) Cast Non-Alloy Steel", "EN-1.0420-GE200-Cast-Non-Alloy-Steel"]:
    print(f"{n:45s} -> {canonical_key(n)}")
pair = listings[listings.canonical_grade == canonical_key("AISI 201 (S20100) Stainless Steel")]
pair[["raw_name", "name_format", "tensile_strength_raw", "is_imputed_ts", "liquidus_c", "C", "Cr", "Ni"]]
'''),
    ("code", r'''
m = log.get("add_canonical_grade").metrics
print({k: m[k] for k in ["n_canonical", "n_listed_twice", "n_listed_once", "twin_pairs_both_measured",
                         "twin_pairs_with_conflicting_measured_ts"]})
print("name formats:", m["name_format_counts"])
# within each canonical grade, composition and liquidus are identical (asserted by the pipeline)
print("max distinct compositions per canonical grade:",
      int(listings.groupby("canonical_grade")[ELEMENTS].nunique().max(axis=1).max()))
'''),
    ("md", r'''
Every twin pair where both listings are measured agrees **exactly** on tensile strength, composition and
liquidus. The two formats are two copies of the same source record. Imputation hit the hyphenated copy
almost exclusively:
'''),
    ("code", r'''
pv = listings.pivot_table(index="canonical_grade", columns="name_format", values="is_imputed_ts", aggfunc="first").dropna()
print(pd.crosstab(pv["spaced"], pv["hyphenated"], rownames=["spaced imputed"], colnames=["hyphenated imputed"]))
from src.analysis import viz_quality as VQ
show(VQ.twin_breakdown(listings), "01_twin_listings_imputation")
'''),
    ("md", r'''
**Decision.** Collapse twins into one grade. Take TS from a measured listing whenever one exists. That is
not imputation: it is the same record's own value, and the twins never disagree. Grades with **no**
measured listing keep `is_imputed_ts = True`, have `tensile_strength_mpa = NaN`, and are excluded from every
strength statistic and model. They are kept for composition and family analysis.
'''),
    ("code", r'''
m = log.get("collapse_to_grades").metrics
print("grades:", m["n_grades"], "| TS recovered from measured twin:", m["n_recovered_from_twin"],
      "| grades without any measured TS:", m["n_grades_without_measured_ts"])
grades.loc[grades.is_imputed_ts, ["display_name", "family", "n_listings"]]
'''),
    ("code", r'''
show(VQ.cleaning_funnel(log, int(grades.tensile_strength_mpa.notna().sum())), "01_cleaning_funnel")
'''),
    ("md", r'''
## 6 · Identical composition, different strength: the irreducible error

Some compositions are listed with several strengths: maraging steel aged vs annealed, CB7Cu in H900…H1150
tempers, cast-iron grades poured from the same nominal chemistry. Strength there depends on
**processing / heat treatment, which the data does not record**. No composition-only model can separate
them, so their spread is the ceiling for every model in notebook 03.

First, how many such groups are real and how many are an artefact of imputation?
'''),
    ("code", r'''
log.get("audit_processing_variants").metrics
'''),
    ("code", r'''
from src.analysis.quality import irreducible_error
ie = irreducible_error(grades)
pd.Series(ie.as_dict())
'''),
    ("md", r'''
How to read the ceiling:

* **Whole-dataset oracle** (predict every grade with its composition-group mean, in-sample) gives the
  best MAE/RMSE/R² any composition-only model could reach. It is optimistic: singletons contribute zero
  error because their processing spread is simply unobserved.
* **Within multi-member groups** the floor is far higher. For grades sold in several tempers, chemistry
  alone cannot pin strength down to better than roughly this MAE.
'''),
    ("code", r'''
display(ie.groups[ie.groups.ts_range > 0][["n", "ts_min", "ts_max", "ts_range", "family", "example"]].head(12))
show(VQ.processing_variants(ie), "01_processing_variants")
print("names stating a heat-treatment condition:", grades.condition_in_name.value_counts().drop("none").to_dict())
'''),
    ("md", r'''
## 7 · Strength class recomputed from measured TS

`Class` is binned TS (0 = 140–290, 1 = 300–600, 2 = 610–2450 MPa). We rebuild it from measured TS with the
same edges, check it reproduces the original on every measured listing, and leave it empty for unmeasured grades.
'''),
    ("code", r'''
m = log.get("recompute_strength_class").metrics
print("agreement with original Class on measured listings:", m["agreement_on_measured_listings"])
print("grade-level class counts:", m["grade_class_counts"])
print("original listing-level class counts:", m["original_listing_class_counts"])
'''),
    ("md", r'''
## 8 · Is liquidus = 1460 °C a placeholder?

1460 °C is by far the most common liquidus. If it were measured, it should (a) fall as carbon rises in
plain steels (carbon depresses the liquidus), and (b) appear evenly across naming sources and name formats.
'''),
    ("code", r'''
from src.analysis.quality import liquidus_default_evidence
ev = liquidus_default_evidence(grades, listings)
print("by name format (listings):"); display(ev.by_name_format)
print("by naming source (grades):"); display(ev.by_naming_source)
'''),
    ("code", r'''
print("by family (grades):"); display(ev.by_family)
print("carbon & low-alloy families, C <= 1 wt%: recorded vs empirical liquidus by carbon band")
display(ev.carbon_bins)
pd.Series(ev.summary)
'''),
    ("code", r'''
show(VQ.liquidus_default(ev), "01_liquidus_default")
'''),
    ("md", r'''
**Findings.**

* The share of 1460 is the same in both name formats, so it is not a scrape artefact. It varies by
  naming source only because families vary by source.
* It is concentrated in plain carbon / low-alloy steels and never used for cast irons, high-speed steels
  or Fe-Ni alloys, whose liquidus values are clearly grade-specific.
* Within carbon & low-alloy steels the recorded liquidus barely moves across the carbon range, while the
  empirical liquidus correlation (and the Fe–C phase diagram) predicts a steady drop of tens of °C.
  Even the non-1460 values in these families show almost no correlation with carbon or with the empirical
  estimate (see `corr_*` above).

**Decision.** 1460 °C is a **family-typical default** assigned by the source, not a grade-specific
measurement. We **keep** it (it is a sensible typical value for plain steels), **flag** it as
`liquidus_is_default`, and treat liquidus as reliable only at family level for plain steels. Consequences:
no grade-level liquidus regression is claimed; the design-space analysis and the app's Target Designer show
default values distinctly and let the user exclude them.

## 9 · Composition sums and trace elements
'''),
    ("code", r'''
from src.analysis.quality import composition_sum_summary
print("composition sum:", composition_sum_summary(grades))
print(log.get("group_trace_elements").detail)
nonzero = (grades[ELEMENTS] > 0).sum().sort_values()
nonzero.to_frame("grades_nonzero").T
'''),
    ("md", r'''
Sums of 95–105 wt% are expected: compositions are **specification midpoints**, rounded, with residual
elements omitted, not chemical analyses of a heat. We do not renormalise: renormalising would distort the
specified values engineers actually work with. Rare elements are kept as columns but summed into
`trace_total` for modelling, so a handful of non-zero values cannot dominate distances or splits.

## 10 · Engineered features
'''),
    ("code", r'''
print(log.get("add_features").detail)
display(grades.groupby("family_label").agg(grades=("grade_id", "size"),
        measured_ts=("tensile_strength_mpa", "count"), median_ts=("tensile_strength_mpa", "median"),
        median_alloying=("alloying_total", "median"), median_CE=("carbon_equivalent", "median"))
        .sort_values("grades", ascending=False))
print("family assigned by:", grades.family_source.value_counts().to_dict())
print("naming source:", grades.naming_source.value_counts().to_dict())
print("product form:", grades.product_form.value_counts().to_dict())
'''),
    ("md", r'''
| Feature | Definition | Why |
|---|---|---|
| `family` | Ordered name regex (weld metal, maraging and cast irons first), EN 10020 composition fallback | Engineers think in families; the baseline model is a family median |
| `naming_source` | EN / SAE-AISI / ASTM / UNS / AWS / ACI / Other | Checks that defaults/imputation are not source artefacts |
| `product_form` | wrought / cast / weld | Cast and weld products have systematically different strength |
| `alloying_total` | 100 − Fe | "Leaner" substitutes = lower alloy content |
| `carbon_equivalent` | IIW: C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15 | Classic hardenability / weldability index |
| `cr_plus_ni`, `cr_eq`, `ni_eq` | Cr+Ni; Schaeffler equivalents | Stainless map and microstructure |
| `is_stainless_comp` | Cr ≥ 10.5 | Composition view of "stainless", independent of the name |
| `composition_group_id` | Identical 30-element vector | **GroupKFold key**: identical chemistry never straddles folds |

## 11 · Save
'''),
    ("code", r'''
save_outputs(result)
for p in ["data/processed/steels_clean.csv", "data/processed/steels_listings.csv",
          "data/processed/DATA_DICTIONARY.md", "reports/cleaning_log.md"]:
    print(f"{p:42s} {(ROOT / p).stat().st_size / 1024:8.1f} KB")
grades.head(3)
'''),
]

NOTEBOOKS = {
    "01": ("01_cleaning.ipynb", NB01),
}
