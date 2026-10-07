# SteelScope: Project Journey

A running log of the project, updated after every phase. Every number here is printed by code in this repository. Where a number appears, the script or notebook that produces it is named next to it.

---

## 0. Problem statement

Engineers and procurement teams pick steel grades from thousands of standard designations (EN, SAE-AISI, ASTM, UNS, AWS, ACI). Three questions come up again and again:

1. **Drivers**: which alloying elements drive tensile strength and melting (liquidus) behaviour?
2. **Substitution**: if a grade is unavailable or expensive, which other grades have a similar composition and performance, ideally with less alloy content?
3. **Target-driven design**: for a required tensile-strength band and liquidus range, which families and composition envelopes have historically achieved it?

SteelScope answers these with an analytics-first pipeline (Python), a Tableau dashboard, a KNIME workflow that cross-checks the Python models, and a small FastAPI + vanilla-JS application.

## 1. Dataset

`data/raw/Alloys.csv`: 2672 rows × 34 columns, no nulls.

- `Alloy` (grade name), `Tensile Strength` (MPa), `Melting Completion (Liquidus)` (°C), `Class` (0/1/2)
- 30 element columns in wt%: Al, As, B, C, Ca, Ce, Co, Cr, Cu, Fe, La, Mg, Mn, Mo, N, Nb, Ni, O, P, Pb, S, Se, Si, Sn, Ta, Ti, V, W, Zn, Zr

Every row is iron-based (minimum Fe = 29.3 wt%). The domain is **steels & iron alloys**: carbon, alloy, stainless, tool and high-speed, maraging, cast iron, weld metal and a few Fe-Ni special alloys.

---

## Phase 1 plan: data cleaning and features

**Goal:** a reusable, logged cleaning pipeline (`src/analysis/`), not notebook-only logic. The notebook `notebooks/01_cleaning.ipynb` only calls the pipeline and displays what it did.

Pre-coding profiling (scratch scripts, findings re-derived inside the pipeline and notebook) showed:

| Observation | Count | Planned decision |
|---|---|---|
| Exact full-row duplicates | 62 | Drop |
| Rows with TS = 652.482978 (= column mean) | 469 | Flag `is_imputed_ts` |
| Same grade under two name formats ("EN 1.0420 (GE200) …" vs "EN-1.0420-GE200-…") | 2610 rows → 1389 canonical grades | Build `canonical_grade` and collapse to one row per grade |
| Imputed rows whose twin listing carries a measured TS | 459 of 469 | Use the twin's measured value (it is the same record; all 759 twin pairs where both TS are measured agree exactly) |
| Grades with no measured TS in any listing | 7 | Keep for composition/family work; exclude from strength stats and models |
| Liquidus = 1460 °C | 1039 rows | Investigate as a family default; flag `liquidus_is_default` |
| Composition groups with >1 TS for identical chemistry | 476 at row level, 28 using measured TS | Quantify as irreducible (processing) error |

Planned steps (each logs rows before/after):

1. Load and validate the schema (34 columns, no nulls, numeric elements).
2. Drop exact duplicates.
3. Flag imputed TS.
4. Build `canonical_grade` (lowercase, collapse every non-alphanumeric run to one separator). Assert one composition and one liquidus per key.
5. Collapse listings into grades. TS = a measured value from any listing; NaN if none.
6. Recompute `strength_class` from measured TS only (bins 0: <300, 1: 300–600, 2: >600 MPa). Assert it matches the original `Class` on measured rows.
7. Flag the default liquidus.
8. Group rare elements (non-zero in <30 deduplicated rows) into `trace_total`.
9. Features: `family` (ordered name regex, EN 10020 composition fallback), `naming_source`, `product_form` (wrought/cast/weld), `condition_in_name`, `alloying_total = 100 − Fe`, `carbon_equivalent` (IIW), `cr_plus_ni`, Schaeffler `cr_eq`/`ni_eq`, `is_stainless_comp`, `composition_group_id`.
10. Save `data/processed/steels_clean.csv` (one row per grade), `data/processed/steels_listings.csv` (row level, for the with/without-imputation sensitivity check), the cleaning log and a generated data dictionary.

## Phase 1 results: what the pipeline found

Source of every number: `python -m src.analysis.cleaning` → `reports/cleaning_log.md`, and `notebooks/01_cleaning.ipynb`.

### Data issues and decisions

| # | Issue | Evidence (code output) | Decision |
|---|---|---|---|
| 1 | Exact duplicates | 62 rows | Dropped: 2672 → 2610 |
| 2 | Mean-imputed TS (652.482978 MPa = raw column mean) | 469 rows (17.6% of raw, 18.0% after dedupe); all in original Class 2 | Flagged `is_imputed_ts`. Never used as a strength value |
| 3 | Twin listings (spaced vs hyphenated name) | 1389 canonical grades: 1221 listed twice, 168 once. 0 grades with more than one composition or liquidus. 759 twin pairs where both TS are measured agree exactly | Collapsed to one row per grade: 2610 → 1389 |
| 4 | Imputation sits on the hyphenated twin | 459 pairs: spaced measured, hyphenated imputed; 3 pairs both imputed; 0 the other way | TS taken from the measured twin (same record, not imputation). **Only 7 grades have no measured TS**: kept for composition work, excluded from strength stats and models |
| 5 | Same composition, different TS | 476 composition groups at listing level, but only **28** with measured TS. The other 448 are the imputed constant disagreeing with the measured twin | The 28 are real processing variants (maraging aged/annealed, CB7Cu H900–H1150, cast-iron grades). Quantified as the irreducible error (below) |
| 6 | `Class` is binned TS | Recomputed class matches the original on 100% of measured listings | `strength_class` rebuilt from measured TS: 23 / 648 / 711 grades (low/medium/high), 7 without class. TS is never a feature for class |
| 7 | Liquidus = 1460 °C | 1037 listings / 524 grades (37.7%). Same share in both name formats (39.4% spaced, 40.1% hyphenated). 76.8% of carbon & low-alloy grades (C ≤ 1%) vs 0% of cast irons, high-speed steels and Fe-Ni alloys. Within C ≤ 0.6% the recorded mean only moves 1462.6 → 1453.1 °C while the empirical correlation predicts 1519 → 1485 °C | **Family-typical default, not a measurement.** Kept, flagged `liquidus_is_default`. Liquidus treated as reliable only at family level for plain steels; no grade-level liquidus model is claimed; the app shows default values distinctly and can exclude them |
| 8 | Composition sums 95.01–105.23 wt% | 98.7% of grades within 99–101 wt%; 18 outside | Not renormalised: these are specification midpoints and should stay as specified |
| 9 | Rare elements | As, Ca, Ce, La, Mg, Pb, Se, Sn, Ta, Zn non-zero in < 30 de-duplicated rows | Summed into `trace_total` for modelling |

### Irreducible error (the model ceiling)

From `src/analysis/quality.py::irreducible_error` over 1382 measured grades in 1296 composition groups:

- **Whole-dataset oracle** (predict each grade with its composition-group mean, in-sample): MAE 9.9 MPa, RMSE 54.4 MPa, **R² 0.950**. No composition-only model can beat this. It is optimistic, because singletons contribute zero error.
- **Where processing variants are observable** (37 multi-member groups, 123 grades, 28 with different TS): within-group MAE **111.3 MPa**, RMSE 182.2 MPa.

### Features built

`family` (17 families: 1284 grades by name rule, 105 by the EN 10020 composition fallback), `family_label`, `naming_source` (EN 606, SAE-AISI 318, UNS 146, ASTM 145, AWS 83, Other 46, ACI 45), `product_form` (wrought 1049, cast 257, weld 83), `condition_in_name`, `alloying_total`, `carbon_equivalent` (IIW), `cr_plus_ni`, `cr_eq`, `ni_eq`, `is_stainless_comp`, `trace_total`, `comp_sum`, `composition_group_id` (1299 groups), `composition_group_size`, `composition_group_n_measured`.

### Outputs

- `data/processed/steels_clean.csv`: 1389 grades × 59 columns (analysis table)
- `data/processed/steels_listings.csv`: 2610 de-duplicated listings (for the with/without-imputation sensitivity check)
- `data/processed/DATA_DICTIONARY.md`: generated from the data
- `reports/cleaning_log.md|json`: step-by-step row counts
- Figures: `reports/figures/01_cleaning_funnel.png`, `01_twin_listings_imputation.png`, `01_processing_variants.png`, `01_liquidus_default.png`
- Tests: `tests/unit/test_features.py`, `tests/unit/test_cleaning.py` (synthetic data with every issue planted), `tests/integration/test_pipeline_real_data.py` (pins the counts above)

### Status after Phase 1

Done: cleaning pipeline, features, data dictionary, notebook 01, 51 passing tests.
Pending: EDA, models, findings (Phase 2); exports (Phase 3); app (Phase 4); Tableau/KNIME instructions (Phase 5).
