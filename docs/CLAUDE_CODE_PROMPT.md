# Prompt for Claude Code: visualization-intensive Innovative Assignment

Copy everything inside the box below into Claude Code, after filling in the five `<<...>>` placeholders.
The prompt is dataset-agnostic: it works for the alloys dataset used in SteelScope or for any other tabular
dataset you are given. It makes Claude **plan first, wait for your approval, then build**. Everything goes on a
separate git branch.

---

```text
ROLE
You are a senior data-analytics engineer helping a student group build a college "Innovative Assignment"
(Data Analytics & Visualization course). The faculty has approved the topic. The deliverable must be
VISUALIZATION-INTENSIVE across Python, Tableau and KNIME, analytically honest, and reproducible.

INPUTS (filled in by the student)
- Dataset file: <<path, e.g. data/raw/Alloys.csv>>
- Domain: <<e.g. Materials / Manufacturing>>
- Problem statement: <<one or two sentences, the real-world question>>
- Target / key variable(s): <<e.g. Tensile Strength (MPa)>>
- Application idea: <<e.g. web app to explore grades and find substitutes>>

GIT
- Work on a NEW branch named feature/visual-analytics (create it from the current branch; never commit to main).
- Commit in logical steps (plan, cleaning, each analysis section, exports, each guide), with clear messages.

STEP 0 - PROFILE, THEN PLAN (STOP AND WAIT FOR APPROVAL)
1. Profile the dataset with code: shape, dtypes, nulls, duplicates (exact and near-duplicate/differently
   named rows), suspicious constants (e.g. a value equal to the column mean = imputed), placeholder/default
   values, impossible values, category cardinalities, skewness, outliers.
2. Write docs/PLAN.md: data issues found (with counts printed by code), cleaning decisions, the analysis unit,
   the list of questions the visuals will answer, the full chart list below mapped to those questions,
   the Tableau sheets/dashboards and the KNIME workflow outline.
3. Show me the plan and wait for "approved" before writing analysis code.

STEP 1 - CLEANING PIPELINE (reusable module, not notebook-only code)
- src/analysis/cleaning.py: each step is a function that logs rows before/after; save data/processed/*.csv,
  a generated data dictionary and a cleaning log. Unit tests for every rule (pytest, synthetic data).
- Flag (do not silently drop) imputed or default values; report how key statistics change with vs without them.

STEP 2 - VISUAL-ANALYTICS NOTEBOOK (notebooks/04_visual_analytics.ipynb, logic in src/analysis/*.py)
Use matplotlib + seaborn with ONE eye-candy theme that makes viewers stop scrolling: a deep midnight canvas
with a soft radial glow, MAXIMUM-CHROMA neon categorical hues (hot pink, electric sky, electric orange, violet,
lime, magenta: never plain default blue), plasma-style ramps (indigo -> magenta -> orange -> gold) for magnitudes,
a two-pole neon diverging map with a dark neutral midpoint, glow on key lines, and gold callout boxes/arrows for
story beats. Beauty must not break readability: validate the categorical palette for colour-blind separation and
contrast (keep hues inside an equal-lightness band; reach "pop" through chroma), use at most 3 hues + a dim
"Other" on scatter plots, and keep text in neutral ink colours.
STORYTELLING: structure the notebook as a narrative (Prologue -> Acts -> Epilogue), give every chart a
headline-style title that states its story beat (e.g. "The great disappearing act: 2,672 rows become 1,382
honest grades"), pin 1-2 gold callouts on the exact data points the story is about, and end with an epilogue of
"what to remember" lessons. Every chart has a subtitle, axis labels with units and a source note, and is saved
to reports/figures/. Each chart is followed by a 2-4 sentence takeaway written ONLY from numbers the code printed.
Mandatory techniques and charts:
 A. Five-number summary (min, Q1, median, Q3, max + IQR, Tukey fences, outlier count) as a table AND as
    annotated box plots; full descriptive statistics (mean, sd, CV, skewness, kurtosis, mode, % zeros).
 B. Distributions: histogram + KDE grid with mean/median lines, ridgeline (joy) plot per category,
    ECDF per group, violin + strip + box combo.
 C. Binning: equal-width vs equal-frequency (quantile) side by side with counts; domain-meaningful bins
    (e.g. metallurgical bands) as 100 % stacked bars.
 D. Chi-square tests of independence (at least 4 pairs): chi2, df, p, Cramer's V, % expected < 5;
    add a Monte-Carlo permutation p-value when Cochran's rule fails; standardized-residual heatmaps and a
    Cramer's V lollipop chart.
 E. Correlation: Spearman clustermap. Regression: simple OLS with 95 % confidence AND prediction bands,
    multiple OLS with coefficient forest plot (standardized betas + 95 % CI), residual-vs-fitted and Q-Q plots,
    hexbin joint plot, seaborn pair plot.
 F. PCA: scree + cumulative variance, loadings heatmap, biplot (scores + loading arrows).
 G. K-means: elbow (inertia) + silhouette scan, silhouette blade plot, clusters on the PCA plane as small
    multiples, cluster fingerprint heatmap, cluster radar.
 H. Circular migration plot (chord / ring diagram): ribbons from source categories (left) to target
    categories (right), width = flow. Build at least two, e.g. raw label -> cleaned outcome and
    category -> cluster. Implement the geometry yourself (arcs + Bezier ribbons) and export it for Tableau.
 I. Ring / donut (two-level sunburst), circular column (radial bar) charts, nested treemap (squarify).
 J. Radar charts: category composition fingerprints (small multiples), well-known items as percentile
    profiles (3x3 small multiples with a median reference outline), and a 3-item overlay.
 K. Waterfall charts: data-cleaning row flow, an additive index built term by term, and a model prediction
    built from SHAP contributions (declare any non-zero axis baseline in the subtitle).
 L. Parallel coordinates of group medians.
Render and LOOK at every figure; fix overlapping labels, clipped text and unreadable colours before moving on.

STEP 3 - MODELS (only where they answer a real question)
Baseline first (e.g. group median), then interpretable regression, then gradient boosting; group-aware
cross-validation if duplicates or near-duplicates exist; report MAE/RMSE/R2 against the baseline and an
irreducible-error ceiling. Classifier with class balancing and macro-F1 if a class target exists.

STEP 4 - EXPORTS
- exports/tableau/: wide table (one row per entity + features + predictions + clusters), long table for
  composition-type charts, summaries, metrics, and exports/tableau/viz/*.csv helper files: radar polygons,
  chord ribbons/arcs, radial-bar polygons and waterfall start/end values as ready x/y coordinates
  (columns: layer, shape_id, point_order, x, y, ...) so Tableau can draw them with Polygon/Line marks.
- exports/knime/: model-ready input with a deterministic, group-safe train/test split column sorted
  train-first, plus a CSV of every number KNIME should reproduce.

STEP 5 - GUIDES (step-by-step, visualization-intensive, written for students who used the tools only in labs)
- docs/TABLEAU_GUIDE.md: which file to connect, data types/roles, every calculated field with exact formula,
  15+ sheets (box plot with five-number reference lines, histogram with bins, quantile bins via LOD
  percentiles, stacked domain bins, chi-square residual highlight table, scatter with trend line + Describe
  Trend Model, coefficient forest plot, PCA scatter, native clustering, elbow line, chord via Polygon marks,
  donut, radial bars, treemap, radar via Line/Polygon marks, waterfall via Gantt bars, KPI tiles), each with
  shelves, marks, colour, filters, tooltips and the insight it shows; 3 interactive dashboards with filter and
  highlight actions; a Story; publishing to Tableau Public.
- docs/KNIME_GUIDE.md: node-by-node workflow (exact settings, ports, what to check) covering readers, row
  filters, rule engine, math formulas, statistics/five-number summary, binning, crosstab chi-square,
  correlation, linear regression, PCA, k-means + silhouette loop, colour manager and native view nodes
  (box plot, histogram, bar, pie/donut, scatter, scatter matrix, heatmap, sunburst, parallel coordinates),
  plus Python View nodes (copy-paste scripts) for radar, chord, waterfall, circular columns, treemap and
  residual heatmap; a composite interactive dashboard (component layout); expected values from Python
  for every check; exporting the .knwf and screenshots.
- Do NOT generate .twb/.twbx/.knwf files; instructions only.

RULES
- Every number in docs, notebooks and charts must come from code output. No fabricated statistics.
- Prefer medians/quantiles for skewed data; state assumptions and test validity (e.g. Cochran's rule).
- Production-quality code: modules + tests + reproducible notebook builds; no logic hidden in notebooks.
- Keep docs/PROJECT_JOURNEY.md updated after every step (decisions, numbers, what is done vs pending).
- At the end: run the tests, rebuild the notebooks, summarise what was built and what is left.
```

---

## How this project used the prompt

For SteelScope (`data/raw/Alloys.csv`, steels & iron alloys), the branch `feature/visual-analytics` implements
Step 2 and the guides:

| Prompt item | Where it lives |
|---|---|
| A–L chart suite | `notebooks/04_visual_analytics.ipynb`, figures `reports/figures/04_*.png` |
| Statistics behind the charts | `src/analysis/visual_stats.py` |
| Figure code (theme, chord, radar, ring, treemap, waterfall…) | `src/analysis/viz_suite.py` |
| Tableau helper CSVs, KNIME expected values | `src/analysis/viz_exports.py` → `exports/tableau/viz/`, `exports/knime/viz_expected_values.csv` |
| Tableau guide | `docs/TABLEAU_GUIDE.md` |
| KNIME guide + Python View scripts | `docs/KNIME_GUIDE.md`, `docs/knime_python_views/*.py` |
