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

# =============================================================================================
# 02 EDA
# =============================================================================================
NB02 = [
    ("md", r'''
# 02 · Exploratory analysis: questions, not chart spam

Each section asks one question an engineer or buyer would ask, answers it with a statistic and one figure,
and ends with the practical takeaway. Strength statistics use only grades with a **measured** tensile strength.
Statistics come from `src/analysis/eda.py`; figures from `src/analysis/viz_eda.py`.
'''),
    ("code", SETUP),
    ("code", r'''
from src.analysis.cleaning import load_clean_grades
from src.analysis.constants import CLEAN_LISTINGS_CSV
from src.analysis import eda as E, viz_eda as VE
grades = load_clean_grades()
listings = pd.read_csv(CLEAN_LISTINGS_CSV)
m = E.measured(grades)
print(f"{len(grades)} grades, {len(m)} with measured tensile strength")
m[E.TS].describe()
'''),
    ("md", "## Q1 · How much does family alone decide strength?"),
    ("code", r'''
fam = E.family_strength_table(grades)
display(fam.set_index("family_label").drop(columns="family"))
kw = E.kruskal_family(grades)
print("Kruskal-Wallis across families:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in kw.items()})
show(VE.strength_by_family(grades), "02_strength_by_family")
'''),
    ("md", r'''
**Takeaway.** Family is the first-order decision. Family medians run from grey cast iron at the bottom to spring
steel at the top, about a sevenfold spread. The Kruskal–Wallis ε² printed above is the share of the strength
*ranking* explained by family alone. Within most families the IQR is still a few hundred MPa, which is where
chemistry and processing come in. The baseline model in notebook 03 is exactly this: predict the family median.

## Q2 · Which elements drive strength, and does pooling families mislead?
'''),
    ("code", r'''
rho, pval, sizes = E.element_correlations(grades)
print("Spearman rho with tensile strength (NaN = element essentially absent in that group)")
display(rho.round(2))
ce = E.carbon_effect(grades)
pd.Series(ce)
'''),
    ("code", r'''
show(VE.carbon_paradox(grades, ce), "02_carbon_simpsons_paradox")
show(VE.correlation_heatmap(rho, sizes), "02_element_correlations")
'''),
    ("md", r'''
**Takeaway.** Pooled across all grades, carbon looks irrelevant to strength. That is a **Simpson's paradox**:
cast irons hold 2–4 % carbon (as graphite) yet are mostly weak, which cancels the steel trend. Within carbon &
low-alloy steels, carbon is the dominant strengthener (Theil–Sen slope above, per 0.1 % C). The heatmap shows
the same thing for other elements: V, Co, Mo and W matter strongly in tool & high-speed steels; in stainless,
nitrogen and molybdenum help while the bulk Cr/Ni amount does not. **Any element-to-strength claim must be
made within a family.** That is also why the models include family as a feature.

## Q3 · Stainless steels: does more alloy mean more strength?
'''),
    ("code", r'''
prof = E.stainless_profile(grades)
display(prof)
s = m[m.family == "stainless"]
from scipy import stats
print("within stainless, Spearman rho(alloying_total, TS) =", round(stats.spearmanr(s.alloying_total, s[E.TS])[0], 3))
show(VE.cr_ni_map(grades, prof), "02_cr_ni_map")
'''),
    ("md", r'''
**Takeaway.** Inside the stainless family, total alloy content is essentially uncorrelated with strength.
What matters is **which microstructure** the Cr–Ni balance produces: duplex-type and Ni-bearing martensitic /
precipitation-hardening grades sit well above fully austenitic grades, despite austenitic grades carrying the
most nickel. For procurement this is the expensive mistake to avoid: a high-Ni austenitic grade is *not* the
strong option. You pay for nickel to get corrosion resistance and toughness, not strength.

## Q4 · Is carbon equivalent a useful strength index?
'''),
    ("code", r'''
ce_tab = E.ce_by_group(grades)
display(ce_tab)
show(VE.ce_small_multiples(grades, ce_tab), "02_ce_vs_strength")
'''),
    ("md", r'''
**Takeaway.** The IIW carbon equivalent is a decent single-number strength proxy for carbon/low-alloy and
tool steels, and meaningless for stainless (its Cr term counts corrosion-resisting chromium as if it were
hardenability) and for cast irons. Use CE to screen plain steels; do not carry it across families.

## Q5 · Strength vs liquidus: one trade-off or two independent axes?
'''),
    ("code", r'''
ds = E.design_space_stats(grades)
display(pd.Series(ds))
display(E.design_space_by_family(grades))
show(VE.design_space(grades, ds), "02_design_space")
'''),
    ("md", r'''
**Takeaway.** Tensile strength and liquidus are at most weakly related: no correlation across all grades, and
only a weak one once the default 1460 °C values are removed (coefficients above). They are **near-independent
design axes**: picking a strength band barely constrains the melting range, and vice versa. That justifies the
app's Target Designer, which filters on both axes at once. Liquidus mostly separates *families* (cast irons sit
at the low end, high-speed steels at the top; see the P10–P90 table), not grades within a family.

Example query, as the Target Designer runs it: **800–1000 MPa with a liquidus of 1420–1470 °C**, with and
without the default-liquidus grades.
'''),
    ("code", r'''
q, fam_q, env = E.target_design_query(grades, 800, 1000, 1420, 1470)
print(f"{len(q)} grades match"); display(fam_q.head(8)); display(env.round(3))
q2, fam_q2, _ = E.target_design_query(grades, 800, 1000, 1420, 1470, exclude_default_liquidus=True)
print(f"excluding default liquidus: {len(q2)} grades"); display(fam_q2.head(8))
'''),
    ("md", "## Q6 · What separates the strength classes?"),
    ("code", r'''
sep = E.class_separation(grades)
display(sep.round(3))
display(E.class_family_mix(grades))
show(VE.class_drivers(sep, grades), "02_class_drivers")
'''),
    ("md", r'''
**Takeaway.** No single element separates the classes strongly: even the largest effect size (Mo) is small.
The classes are separated mainly by **family**. The low class (< 300 MPa) is almost entirely cast iron (grey
and Ni-Resist), which is why its carbon median is high. Every high-speed, maraging, spring and nitriding grade
is high-class, and the high class carries several times more alloy than the medium class (alloying-total medians
above). The low class is tiny (see n), so the classifier in notebook 03 must be class-balanced and judged on
macro-F1, not accuracy.

## Q7 · How do conclusions change with vs without the imputed rows?
'''),
    ("code", r'''
from src.analysis.quality import imputation_sensitivity
sens = imputation_sensitivity(listings, grades)
display(sens.T.round(3))
show(VE.imputation_sensitivity(listings, grades, sens), "02_imputation_sensitivity")
'''),
    ("md", r'''
**Takeaway.** Treating the imputed constant as data would:

* create a fake mode at 652 MPa and overstate the share of high-strength grades;
* set the **median of whole families** (stainless, tool) to exactly the imputed value;
* weaken the true element–strength correlations (e.g. Ni, Mo, V), because a constant was mixed into the target.

Dropping imputed rows *but keeping twin listings* (scenario B) fixes the values, but still double-counts most
grades, so every grade listed twice gets twice the weight. Scenario C (one row per grade, measured TS) is used
everywhere else in this project.
'''),
]

# =============================================================================================
# 03 Models
# =============================================================================================
NB03 = [
    ("md", r"""
# 03 · Models: honest evaluation against a baseline and a ceiling

All models are evaluated with **GroupKFold by `composition_group_id`** (5 folds × 3 seeds): grades with identical
chemistry never sit on both sides of a split. Every score is compared with

* the **family-median baseline** (what an engineer gets from a handbook table), and
* the **irreducible-error ceiling** from notebook 01 (processing is not in the data).

Logic: `src/analysis/modeling.py`, `evaluation.py`, `clustering.py`, `substitutes.py`, `train.py`.
"""),
    ("code", SETUP),
    ("code", r"""
import logging; logging.basicConfig(level=logging.WARNING)
from src.analysis.cleaning import load_clean_grades, load_pipeline_meta
from src.analysis.constants import CLEAN_LISTINGS_CSV
from src.analysis import evaluation as EV, modeling as M, viz_models as VM
grades = load_clean_grades(); listings = pd.read_csv(CLEAN_LISTINGS_CSV)
rare = load_pipeline_meta()["rare_elements"]
ev = EV.run_evaluation(grades, listings, rare)      # every CV experiment, run once
EV.save_evaluation(ev)
m = ev.measured
print("measured grades:", len(m), "| composition groups:", m.composition_group_id.nunique())
pd.Series(ev.ceiling.as_dict())
"""),
    ("md", "## 1 · Tensile-strength regression"),
    ("code", r"""
cols = ["model", "features", "MAE_mean", "MAE_std", "RMSE_mean", "R2_mean", "R2_std", "oof_MAE", "oof_R2"]
display(ev.reg_table[cols].sort_values("MAE_mean"))
show(VM.model_comparison(ev.reg_table, ev.baseline_mae, ev.ceiling, EV.CHOSEN_REGRESSOR), "03_model_comparison")
"""),
    ("md", r"""
**Reading the table.**

* The **family-median baseline** is the bar to beat. **Ridge does not beat it**: element effects change sign
  between families (notebook 02, Q2), and a pooled linear model cannot express that.
* Tree ensembles learn those family-conditional, non-linear effects and roughly **halve the baseline MAE**.
  Adding family and product form to composition helps every model.
* Nested GroupKFold tuning of the GBM (last row) gives no gain over the fixed settings, so the simpler fixed
  configuration is deployed.
* The gap to the ceiling is real but bounded. Most of it sits in grades whose chemistry is shared with other
  tempers (section 3).

## 2 · Why GroupKFold: the leakage demonstration
"""),
    ("code", r"""
display(ev.leakage)
show(VM.leakage_demo(ev.leakage), "03_leakage_demo")
"""),
    ("md", r"""
The same model looks far better on random splits of the listing rows, because a grade's twin listing sits in
the training fold. Keeping the imputed targets instead adds noise. Even at grade level, a random split lets
processing variants of one chemistry leak across folds. **Only the last row is an honest estimate** of how the
model does on a chemistry it has not seen.

## 3 · Where the model errs
"""),
    ("code", r"""
err = (ev.chosen_oof - m[M.TARGET]).abs()
shared = m.composition_group_n_measured > 1
print(f"OOF MAE: unique composition {err[~shared].mean():.1f} MPa (n={(~shared).sum()}), "
      f"shared composition {err[shared].mean():.1f} MPa (n={shared.sum()}); median AE {err.median():.1f} MPa")
show(VM.pred_vs_actual(m, ev.chosen_oof), "03_pred_vs_actual")
show(VM.error_by_family(m, ev.chosen_oof), "03_error_by_family")
"""),
    ("md", "## 4 · Strength-class classifier (TS never used as a feature)"),
    ("code", r"""
display(ev.clf_table.round(3))
cm = M.confusion(ev.y_class, ev.clf_results["Gradient boosting (balanced)"].oof.astype(int))
display(cm)
show(VM.classifier_results(ev.clf_table, cm), "03_classifier")
"""),
    ("md", r"""
Class-balanced gradient boosting clearly beats the family-majority baseline on macro-F1 and recovers almost
the whole low class. Errors concentrate at the medium/high boundary (600 MPa), where a few MPa decide the
label. Thresholding the regressor's prediction is nearly as good, a useful consistency check between the
two models.

## 5 · What drives the predictions
"""),
    ("code", r"""
display(ev.perm_importance.round(2).head(15))
import shap
spec = M.feature_specs(rare)["composition+family"]; levels = M.category_levels(grades)
X = M.build_X(m, spec, levels, rare)
est = M.make_regressor("Gradient boosting", spec).fit(X, m[M.TARGET])
codes = X.copy()
for c in spec.categorical: codes[c] = X[c].cat.codes.astype(float)
cols_ = list(X.columns)
def f(a):
    d = pd.DataFrame(a, columns=cols_)
    for c in spec.categorical: d[c] = pd.Categorical.from_codes(d[c].astype(int), categories=levels[c])
    return est.predict(d)
sample = codes.sample(250, random_state=0)
background = shap.maskers.Independent(shap.utils.sample(codes, 100, random_state=0), max_samples=100)
sv = shap.PermutationExplainer(f, background, seed=0)(sample, silent=True)
print("SHAP additivity max error:", float(np.abs(sv.values.sum(1) + sv.base_values - f(sample.values)).max()))
shap_mean = pd.Series(np.abs(sv.values).mean(0), index=cols_).sort_values(ascending=False)
shap_mean.rename("mean_abs_shap_mpa").to_csv(ROOT / "reports/tables/shap_importance.csv")
display(shap_mean.round(1).head(12))
show(VM.importance(ev.perm_importance, shap_mean), "03_feature_importance")
show(VM.shap_dependence(X.loc[sample.index].reset_index(drop=True), sv.values, cols_, m.loc[sample.index, "family"]),
     "03_shap_dependence")
"""),
    ("md", r"""
Permutation importance (held-out folds) and SHAP (deployed model) agree on the top of the ranking: **family**
first, then carbon equivalent, nickel and carbon. The dependence plots show *why* one global coefficient fails:
the same carbon or nickel content pushes the prediction differently depending on the family.

## 6 · Prediction intervals for the Strength Estimator
"""),
    ("code", r"""
iv = ev.intervals
print({k: round(v, 3) for k, v in [("nominal", iv.nominal), ("coverage_raw", iv.coverage_raw),
       ("coverage_calibrated", iv.coverage_calibrated), ("mean_width_calibrated", iv.mean_width_calibrated),
       ("q_hat_final", iv.q_hat_final)]})
display(iv.by_group_type)
show(VM.interval_coverage(iv, m, ev.chosen_oof), "03_interval_coverage")
"""),
    ("md", r"""
Raw quantile GBMs under-cover. A cross-conformal correction brings coverage to the 80 % target **without
looking at the fold being scored**. Coverage is lower for grades whose chemistry is shared with other tempers,
which is the processing ceiling again. The app therefore shows the range together with a
"processing / heat treatment not modelled" warning.

## 7 · Clustering: does chemistry recover the named families?
"""),
    ("code", r"""
cl = ev.clustering
display(cl.agreement.round(3))
display(cl.profiles)
print("PCA explained variance (2 comps):", cl.pca_explained.round(3))
show(VM.clustering_overview(cl, grades), "03_clusters_vs_families")
show(VM.umap_small_multiples(cl.umap_xy, grades), "03_umap_family_groups")
"""),
    ("md", r"""
Composition clusters recover the chemically distinct families (stainless sub-types, grey cast iron,
high-speed and bearing steels), but **most carbon, alloy, boron, spring, nitriding and weathering grades merge
into one lean cluster**. Those names describe application and heat treatment more than chemistry. Agreement
metrics (ARI/NMI) are moderate, and higher against the coarser family groups. HDBSCAN leaves a large share as
noise: composition space is a continuum with dense islands (standard series), not separated blobs.

## 8 · Substitute engine
"""),
    ("code", r"""
display(ev.substitute_eval.round(3))
show(VM.substitute_eval(ev.substitute_eval, EV.CHOSEN_TRANSFORM), "03_substitute_eval")
from src.analysis.substitutes import SubstituteIndex, substitute_features, find_substitutes
idx = SubstituteIndex.fit(grades, substitute_features(rare), EV.CHOSEN_TRANSFORM)
for name in ["AISI 316 (S31600) Stainless Steel", "SAE-AISI 4140 (SCM440,G41400) Cr-Mo Steel"]:
    gid = grades.loc[grades.display_name == name, "grade_id"].iloc[0]
    print(name); display(find_substitutes(idx, grades, gid, k=5).round(2))
print("SAE-AISI 4140, leaner substitutes only:")
display(find_substitutes(idx, grades, gid, k=5, leaner_only=True).round(2))
"""),
    ("md", "## 9 · Fit and save the deployed models"),
    ("code", r"""
from src.analysis.train import train_and_save
out = train_and_save(grades, rare, ev)
print(sorted(p.name for p in (ROOT / "models").iterdir()))
out.head()
"""),
]


# =============================================================================================
# 04 Visual analytics
# =============================================================================================
NB04 = [
    ("md", r"""
# 04 · The Secret Lives of 1,389 Steels
### A visual story in a prologue, seven acts and an epilogue

Every steel on a datasheet hides a biography: what it is made of, how strong it gets, how hot it must be
before it melts, and which "family" it was born into. This notebook tells that story with one rule:
**every claim on screen is printed by the code above it.**

| Part | Story beat | Techniques & charts |
|---|---|---|
| Prologue | *The dataset had a secret* | waterfall, circular migration (chord) plot |
| Act I | *Meet the cast* | ring diagram, treemap, five-number summary, distributions |
| Act II | *Every family has a signature* | ridgeline, ECDF race, violins, circular columns |
| Act III | *Slicing and testing the evidence* | binning, chi-square tests, Cramér's V |
| Act IV | *What actually drives strength* | correlation clustermap, simple and multiple regression, hexbin, pair plot |
| Act V | *The chemistry map* | PCA, k-means, silhouettes, fingerprints, chord: names vs chemistry |
| Act VI | *Portraits* | radar charts, parallel coordinates |
| Act VII | *The verdict* | carbon-equivalent and model-prediction waterfalls |
| Epilogue | *What an engineer should remember* | plus helper exports for Tableau and KNIME |

Theme: **Neon Forge** (midnight canvas, validated colour-blind-safe neon palette, plasma ramps, gold story
callouts). Statistics: `src/analysis/visual_stats.py` · Figures: `src/analysis/viz_suite.py`.
"""),
    ("code", SETUP),
    ("code", r"""
import seaborn as sns
from src.analysis.cleaning import load_clean_grades, load_pipeline_meta
from src.analysis.constants import CLEAN_LISTINGS_CSV, DATA_RAW
from src.analysis import visual_stats as V, viz_suite as VS
from src.analysis.features import family_group
grades = load_clean_grades(); rare = load_pipeline_meta()["rare_elements"]
g = V.with_groups(grades)
m = g.dropna(subset=[V.TS])
raw = pd.read_csv(DATA_RAW); listings = pd.read_csv(CLEAN_LISTINGS_CSV)
print(f"{len(raw):,} raw rows -> {len(g):,} grades -> {len(m):,} with a measured tensile strength")
"""),

    # ------------------------------------------------------------------------------- PROLOGUE
    ("md", r"""
---
## Prologue · The dataset had a secret

It arrived as a spreadsheet of 2,672 rows. It looked complete: no blanks, a strength for every row.
But one strength value repeated hundreds of times, and it was exactly the column average. Many rows were
the *same steel* written twice, once with spaces ("EN 1.0420 (GE200)…") and once with hyphens
("EN-1.0420-GE200-…"). The first chart follows the rows as the truth comes out.
"""),
    ("code", r"""
counts = {"raw": len(raw), "duplicates": int(raw.duplicated().sum()), "twins": int(len(listings) - len(grades)),
          "grades": len(grades), "unmeasured": int(grades[V.TS].isna().sum()), "measured": int(grades[V.TS].notna().sum())}
wf1 = V.waterfall_cleaning(counts); display(V.waterfall_layout(wf1))
show(VS.waterfall(wf1, "The great disappearing act: 2,672 rows become 1,382 honest grades",
                  "Waterfall of the cleaning pipeline; blue = totals, pink = rows removed",
                  story=("Twin listings merged", f"The big secret: {counts['twins']:,} rows were\nthe same steel written twice")),
     "04_31_waterfall_cleaning")
"""),
    ("code", r"""
f1 = V.flow_raw_class_to_outcome(raw, listings, grades)
display(f1)
src1 = sorted(f1.source.unique())
tgt1 = ["Grade class 0", "Grade class 1", "Grade class 2", "Unmeasured TS (excluded)", "Merged into twin listing", "Dropped: exact duplicate"]
show(VS.circular_migration(f1, src1, tgt1, dict(zip(src1, [P.SEQ(0.18), P.SEQ(0.55), P.SEQ(0.92)])),
                           "Where did every row go? A circular migration of the original classes",
                           f"{f1.value.sum():,} raw rows flow from their original strength class (left) to their fate after cleaning (right)",
                           min_label_share=0.0), "04_22_chord_raw_class_migration")
"""),
    ("md", r"""
**What the prologue reveals.** The biggest ribbon is not a data error being deleted. It is the duplicated
listing folding back into its twin, and it carries almost all of the suspicious 652 MPa values with it. Only 7
grades genuinely never had a measured strength. No row changes class: once the fake values are gone, every
grade keeps the class its real strength deserves. The cast of our story is **1,389 real steels**.

---
## Act I · Meet the cast
"""),
    ("code", r"""
show(VS.ring_chart(g), "04_24_ring_families")
show(VS.treemap(g), "04_27_treemap_families")
"""),
    ("md", r"""
Two big tribes dominate: **stainless** (about four grades in ten) and **carbon & low-alloy** steels. The rest
are specialists: cast irons, tool and high-speed steels, weld metals, and a handful of exotic maraging and Fe-Ni
alloys. The treemap adds the plot twist: the *small* tiles glow brightest. Spring, maraging and nitriding steels
are rare, but they are the strongest characters in the story.
"""),
    ("code", r"""
fns = V.five_number_summary(g)
display(fns.round(3)); display(V.descriptive_stats(g).round(3))
show(VS.five_number_boxes(g, fns), "04_01_five_number_summary")
show(VS.distribution_grid(g), "04_02_distributions")
"""),
    ("md", r"""
**The typical steel** has a tensile strength of 610 MPa, and half of all grades sit between 510 and 720 MPa
(table above). Above that, 75 grades break past the upper whisker as outliers: the heavyweights. Liquidus is
squeezed into a narrow 30 °C box because so many plain steels carry the 1460 °C default. Every chemistry variable
is lopsided: most grades use a little of an element and a few use a lot. That is why this story speaks in
**medians**, not averages.

---
## Act II · Every family has a signature
"""),
    ("code", r"""
display(V.summary_by_group(g).round(1))
show(VS.ridgeline(g), "04_03_ridgeline_families")
show(VS.ecdf_by_group(g), "04_04_ecdf_groups")
show(VS.violin_strip(g), "04_05_violin_groups")
"""),
    ("code", r"""
fam_med = m.groupby("family_label")[V.TS].median().sort_values(ascending=False)
grp_of = g.drop_duplicates("family_label").set_index("family_label")["family_group"]
show(VS.circular_columns(fam_med, [VS.GROUP_COLOR[grp_of[f]] for f in fam_med.index],
                         "The strength podium, wrapped into a circle",
                         "Circular column chart of median tensile strength by family; colour = family group", " MPa",
                         "Median TS\nby family",
                         champion_note=f"Champion: {fam_med.index[0]}\n{fam_med.iloc[0]:,.0f} MPa median"),
     "04_25_circular_columns_strength")
"""),
    ("md", r"""
**The signatures.** Each family's ridge is a fingerprint: grey cast iron hugs the low end, high-speed steel is a
tight spike around 800 MPa, maraging steel sprawls across a huge range (its strength depends on heat treatment),
and spring steel stands alone at the top. In the ECDF "race", the curve that climbs latest is the strongest group.
Family alone already tells you roughly where a steel will land. Chemistry fine-tunes the answer.

---
## Act III · Slicing and testing the evidence
"""),
    ("code", r"""
comp = V.binning_comparison(g)
display(comp)
show(VS.binning_comparison(g, comp), "04_06_binning_width_vs_frequency")
b = V.add_bins(g)
display(pd.crosstab(b.carbon_band, b.family_group, margins=True))
show(VS.band_stacks(g), "04_07_domain_bins")
"""),
    ("md", r"""
**How you slice it changes the story.** Five equal-width bins put almost every grade into the first two boxes and
leave the top bin nearly empty; five equal-frequency bins balance the counts but stretch the top bin over a
1,700 MPa range. Metallurgists slice differently: by carbon band and by alloy content. Their bins tell a clean
story: the ">2.1 % carbon" band is cast-iron territory, and the share of high-strength grades climbs with every
step up in alloy content.

Are these patterns real, or coincidences of counting? The chi-square test is the courtroom.
"""),
    ("code", r"""
chi = V.chi_square_suite(grades)
display(pd.DataFrame([r.as_row() for r in chi]).round(4))
show(VS.chi_square_panels(chi), "04_08_chi_square_residuals")
show(VS.cramers_lollipop(chi), "04_09_cramers_v")
"""),
    ("md", r"""
**The verdict on independence: guilty, every time.** All five null hypotheses ("these two things are unrelated")
are rejected. Because the low-strength class has only 23 grades, four tables break Cochran's rule (too many
small expected counts), so we also ran a **permutation test**: shuffle the labels thousands of times and see how
often chance alone produces such a pattern. The answer is never. The gold frames mark the most surprising cell
in each table: cast irons crowd into the low class far beyond chance. Cramér's V ranks the links: family ↔
default liquidus is the tightest (0.67), confirming that 1460 °C is a family habit, not a measurement.

---
## Act IV · What actually drives strength?
"""),
    ("code", r"""
show(VS.correlation_clustermap(g), "04_10_correlation_clustermap")
reg = V.regression_suite(grades)
display(reg["simple"].table().round(3)); print(f"R2 = {reg['simple'].r2:.3f}, n = {reg['simple'].n}")
show(VS.simple_regression(reg), "04_11_simple_regression")
"""),
    ("md", r"""
**Elements travel in gangs**: chromium, nickel and nitrogen (the stainless gang); tungsten, vanadium, molybdenum
and cobalt (the tool-steel gang). In plain carbon steel, one element is in charge: a straight line in carbon
alone explains about half the strength variation, and each extra 0.1 % carbon buys roughly 43 MPa. The tight
inner band says the trend is certain; the wide outer band says any single grade can still surprise you.
"""),
    ("code", r"""
display(reg["multi"].table().round(2))
print(f"R2 = {reg['multi'].r2:.3f}, adj R2 = {reg['multi'].adj_r2:.3f}, F = {reg['multi'].f_stat:.1f}, n = {reg['multi'].n}")
show(VS.multiple_regression(reg), "04_12_multiple_regression")
show(VS.joint_hex(g), "04_13_hexbin_ce_strength")
show(VS.pairplot(g), "04_14_pairplot")
"""),
    ("md", r"""
**Add more suspects and the plot thickens.** Across all carbon & low-alloy steels, C, Si, V, Ni and Cr all push
strength up (Mo is borderline negative, Mn not significant), yet the straight-line model explains only about a
third of the variance. The residual plots show why: a fan that widens with strength and a heavy tail of
heat-treated heavyweights. Strength is not a simple sum of elements. That is the cue for a map instead of a
formula.

---
## Act V · The chemistry map
"""),
    ("code", r"""
X, feats = V.composition_space(grades, rare)
pca = V.pca_analysis(X, feats)
display(pca["explained"].head(8).round(3)); print("components for 80 %:", pca["n_for_80pct"], "| Kaiser:", pca["n_kaiser"])
show(VS.pca_scree(pca), "04_15_pca_scree_loadings")
show(VS.pca_biplot(g, pca), "04_16_pca_biplot")
"""),
    ("md", r"""
**Compress twenty elements into two dimensions** and a map appears. Three arms pull the steels apart: the
**stainless arm** (Cr, Ni, N) to one side, the **tool-steel arm** (V, W, Co) upward, and the **cast-iron pull**
(C) the other way. Plain steels huddle at the centre. The scree plot keeps us honest: two axes hold only about a
quarter of the information, and steel chemistry genuinely needs many dimensions.
"""),
    ("code", r"""
scan = V.kmeans_scan(X)
k, labels = V.kmeans_visual(X, scan)
names = V.cluster_names(grades, labels)
display(scan.round(3)); print("k used for the visuals:", k); print(names)
show(VS.kmeans_elbow(scan, k), "04_17_kmeans_elbow_silhouette")
show(VS.silhouette_plot(X, labels, names), "04_18_kmeans_silhouette_blades")
show(VS.kmeans_small_multiples(pca["scores"], labels, names), "04_19_kmeans_pca_panels")
show(VS.cluster_heatmap(g, labels, names, X, feats), "04_20_cluster_fingerprints")
radar_c = V.radar_cluster_composition(grades, labels, names)
show(VS.radar_small_multiples(radar_c, {n: P.SERIES[i % 8] for i, n in enumerate(radar_c.index)},
                              "Eight tribes, eight chemical shapes",
                              "Cluster radar: log-scaled median composition, min-max across clusters", cols=4), "04_21_cluster_radar")
"""),
    ("md", r"""
**Let the data choose its own tribes.** K-means finds clusters by chemistry alone, without being told any names.
There is no sharp elbow (steel chemistry is a continuum with dense islands), so we take the best silhouette that
still gives every tribe its own colour. The fingerprints read like a metallurgy textbook. Now the climax: do the
tribes that chemistry finds match the names people gave?
"""),
    ("code", r"""
f2 = V.flow_family_to_cluster(grades, labels, names)
src2 = [s for s in VS.FAMILY_GROUP_ORDER if s in set(f2.source)]
tgt2 = [names[i] for i in sorted(names)]
display(f2.pivot(index="source", columns="target", values="value").fillna(0).astype(int))
show(VS.circular_migration(f2, src2, tgt2, VS.GROUP_COLOR, "Names vs chemistry: where each named family really belongs",
                           "Circular migration from named family group (left) to chemistry cluster (right); ribbon width = grades"),
     "04_23_chord_family_to_cluster")
presence = (g[["C","Mn","Si","P","S","Cr","Ni","Mo","Cu","N","V","Nb","Ti","Al","W","Co","B","Zr","O"]] > 0).mean().sort_values(ascending=False) * 100
show(VS.circular_columns(presence, [P.SEQ(0.25 + 0.7 * v / 100) for v in presence], "The element roll-call",
                         "Circular column chart: share of all grades that specify each element (colour follows the share)", " %",
                         "Element\npresence"), "04_26_circular_columns_elements")
"""),
    ("md", r"""
**The twist.** "Stainless" is not one chemistry: its ribbon splits into several clusters (Cr-Ni austenitic,
nitrogen/manganese-rich, ferritic). Meanwhile carbon, alloy, boron and spring steels, proudly different names,
pour into the *same* lean cluster. Their names describe how they are used and heat-treated, not what they are made
of. For a buyer that is good news: chemically, many "different" plain steels are close substitutes. The roll-call
confirms the base recipe: C, Mn, Si, P and S appear in nearly every grade, while W, Co, B and Zr are rare specialists.

---
## Act VI · Portraits
"""),
    ("code", r"""
comp_scaled, comp_raw = V.radar_family_composition(grades)
display(comp_raw.round(3))
show(VS.radar_small_multiples(comp_scaled, VS.GROUP_COLOR, "Family portraits: each group's composition fingerprint",
                              "Radar of log-scaled median wt%, min-max across groups (outer ring = highest group)", cols=3),
     "04_28_radar_family_composition")
picks = V.showcase_grades(grades)
pick_colors = dict(zip(picks["short_name"], family_group(picks["family"]).map(VS.GROUP_COLOR)))
pct = V.radar_grade_percentiles(grades, picks)
display(picks[["short_name", "display_name", "tensile_strength_mpa", "liquidus_c", "carbon_equivalent"]]); display(pct.round(0))
show(VS.radar_small_multiples(pct, pick_colors, "Nine famous steels, nine personalities",
                              "Each spoke = the grade's percentile among all 1,389 grades (0–100); colour = family group",
                              scale_max=100.0, reference=pd.Series(50.0, index=pct.columns),
                              ref_label="the median steel (50th percentile)", ring_labels=["25", "50", "75", "100"]),
     "04_29_radar_showcase_alloys")
show(VS.radar_overlay(pct.loc[["AISI 304", "AISI 316", "17-4 PH"]], [P.SKY, P.PINK, P.FLAME],
                      "Three stainless siblings, three strategies",
                      "AISI 304 vs 316 vs 17-4 PH: Mo for corrosion (316) vs precipitation hardening for strength (17-4 PH)",
                      ring_labels=["25", "50", "75", "100"]), "04_30_radar_overlay_stainless")
show(VS.parallel_coordinates(g), "04_34_parallel_coordinates")
"""),
    ("md", r"""
**Portraits make chemistry personal.** AISI 1018 is a slim, modest shape: almost no alloy, a low carbon equivalent
and low strength (its carbon is only mid-pack, because so many grades are low-carbon stainless).
M2 high-speed steel bursts outward on carbon, molybdenum and liquidus. Grey cast iron is all carbon and little
else. The stainless siblings are the best lesson: 304 and 316 share a silhouette, but 316 reaches out on
molybdenum (for corrosion resistance), while 17-4 PH, with *less* nickel, shoots past both on strength.
Strength comes from how the alloy is built and hardened, not from how much expensive metal goes in.

---
## Act VII · The verdict
"""),
    ("code", r"""
r4140 = grades[grades.display_name.str.startswith(V.SHOWCASE_GRADES["AISI 4140"])].iloc[0]
wf2 = V.waterfall_ce(r4140); display(wf2.round(4))
show(VS.waterfall(wf2, f"Building a weldability score, one element at a time: {r4140.display_name}",
                  "IIW carbon equivalent CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15", fmt="{:.3f}",
                  story=("C", "Carbon alone supplies\nhalf of the score")), "04_32_waterfall_ce_4140")
wf3, info = V.prediction_waterfall(grades, V.SHOWCASE_GRADES["AISI 4140"])
display(wf3.round(1)); print(info)
show(VS.waterfall(wf3, "Inside the model's head: how it predicts AISI 4140",
                  f"SHAP contributions on the deployed model; measured TS = {info['measured']:.0f} MPa", unit=" MPa",
                  xlabel_rot=25, zero_based=False), "04_33_waterfall_prediction_4140")
"""),
    ("md", r"""
**The verdict, told as a waterfall.** For AISI 4140 the weldability score lands in the "difficult" band (above
0.60): carbon and chromium make up most of it, so welders must preheat. The last waterfall opens the model's
mind: it starts from the average steel, lets carbon equivalent, nickel equivalent, chromium and carbon each push
the estimate up or down, and lands close to (but not exactly on) the measured value. That gap is the honest
reminder of the whole project: **composition tells most of the story, and processing writes the final chapter.**

---
## Epilogue · What an engineer should remember

1. **Clean before you count.** 2,672 rows were really 1,389 steels; the fake 652 MPa values hid inside
   duplicate listings.
2. **Think in medians.** Steel data is lopsided; the typical grade is 610 MPa, not the mean.
3. **Family first, chemistry second.** The family sets the strength range; elements fine-tune it.
4. **Carbon is the plain steel's dial,** about +43 MPa per 0.1 %, but only inside plain steels.
5. **Associations are real and measurable:** chi-square plus Cramér's V, with permutation tests when counts are thin.
6. **Names ≠ chemistry.** Many differently-named plain steels share one chemical neighbourhood: good substitutes.
7. **Strength isn't bought by the kilo.** 17-4 PH beats nickel-rich 304/316 on strength with less nickel.

## Appendix · Exports for Tableau and KNIME
"""),
    ("code", r"""
from src.analysis import viz_exports as VX
res = VX.build_viz_exports(grades); VX.save(res)
print(sorted(res["tableau"]))
res["knime"].head(12)
"""),
]


NOTEBOOKS = {
    "01": ("01_cleaning.ipynb", NB01),
    "02": ("02_eda.ipynb", NB02),
    "03": ("03_models.ipynb", NB03),
    "04": ("04_visual_analytics.ipynb", NB04),
}
