# KNIME guide: SteelScope visual analytics workflow

A node-by-node build guide for someone who has used KNIME only in lab sessions. The workflow is
**visualization-first**: every analytical step ends in a view (native KNIME view nodes where they exist,
Python View nodes for radar, chord, waterfall, circular-column, treemap and residual-heatmap charts), and
everything is assembled into an interactive dashboard (a component with a composite view). Every statistic you
should see is listed next to the node, taken from the Python notebooks (`exports/knime/viz_expected_values.csv`).

**Division of work.** Python (notebooks 01, 02, 03) cleans the data and produces the statistical visuals.
**All machine learning (k-means clustering, decision tree, k-NN, random forest) is built here in KNIME**;
there are no Python models to compare against, so for those nodes you report KNIME's own scores.

> Written for **KNIME Analytics Platform 5.2 or newer** (classic or modern UI). Node names are from the Node
> Repository; type them into the repository search box. Where KNIME 4.7 uses a different name, it is given in
> brackets.

---

## 0. Setup (once)

1. **Install extensions:** *File → Install KNIME Extensions…* and tick
   - **KNIME Python Integration** (for the Python View nodes),
   - **KNIME Statistics Nodes** (usually pre-installed; needed for Crosstab chi-square and Rank Correlation),
   - **KNIME Plotly / JavaScript Views** are optional: the 5.x built-in views are enough.
2. **Python environment:** *Preferences → KNIME → Python* → choose **Bundled environment**. It includes
   pandas, numpy, scipy and matplotlib, which is all the scripts in `docs/knime_python_views/` need (they
   deliberately avoid seaborn/squarify).
3. **Workflow:** *File → New → New KNIME Workflow* → name `SteelScope_Visual_Analytics`.
4. Use **annotations** (right-click canvas → *New Workflow Annotation*) to label the sections below; graders
   read the workflow canvas first.

### Data files
| File | Rows | Use |
|---|---|---|
| `exports/knime/knime_input.csv` | 1389 | Main input: cleaned grades, 30 elements, family, product form, TS, class, liquidus, group-safe train/test `split` column, Python's engineered features for cross-checks |
| `exports/tableau/viz/waterfall_cleaning.csv`, `waterfall_ce_aisi4140.csv` | 6 / 8 | Waterfall inputs |
| `exports/knime/viz_expected_values.csv` | 85 | The numbers to reproduce (open it in a CSV Reader + Table View to keep it visible in the workflow) |

---

## 1. Section A: Read, filter, enrich

### Node 1. CSV Reader
- **Settings:** file = `knime_input.csv`; *Has column header* ✓; delimiter `,`; *Transformation* tab: check
  the types: `strength_class` → **Number (integer)**, `is_imputed_ts` and `liquidus_is_default` → **Boolean**
  (if KNIME reads them as String "True"/"False", keep String and adapt node 2).
- **Output port:** table with **1389 rows × 49 columns**.
- **Check:** right-click → *Output table*; column `split` has values train / test / excluded_no_measured_ts.

### Node 2. Row Filter: keep measured strength
- **Settings (5.x Row Filter):** filter criterion column `is_imputed_ts`, operator **is false** (Boolean) or
  *is equal to* `False` (String) → *Include matching rows*.
- **Output:** **1382 rows** (7 removed). These 7 grades have no measured tensile strength.

### Node 3. Duplicate Row Filter: sanity check
- **Settings:** *Choose columns for duplicates detection* = `canonical_grade` only; *Remove duplicate rows*.
- **Output:** still **1382** rows: the Python pipeline already merged the twin listings.
- **Second instance (Node 3b):** same node on all element columns (`Al` … `Zr`), option **Keep duplicate rows**
  → *Add column showing duplicate status*. Then **GroupBy** on that status column with *Count* → shows how many
  grades share an identical composition with another grade (processing variants: same chemistry, different
  heat treatment).

### Node 4. Rule Engine: family group
- **Settings:** *Append column* `family_group`; rules (paste exactly):
```
$family$ IN ("carbon", "alloy", "boron", "spring", "bearing", "nitriding", "weathering") => "Carbon & low-alloy"
$family$ = "stainless" => "Stainless"
$family$ LIKE "cast_iron*" => "Cast iron"
$family$ IN ("tool", "high_speed") => "Tool & high-speed"
$family$ = "weld_metal" => "Weld metal"
TRUE => "Other"
```
- **Check:** GroupBy on `family_group` (Count) → Carbon & low-alloy **583**, Stainless **543**, Weld metal **83**,
  Tool & high-speed **82**, Cast iron **63**, Other **28** (measured grades only).

### Nodes 5a–5d. Math Formula: engineered features
One Math Formula node per feature (*Append column*):

| Node | New column | Expression |
|---|---|---|
| 5a | `alloying_total` | `100 - $Fe$` |
| 5b | `carbon_equivalent` | `$C$ + $Mn$/6 + ($Cr$ + $Mo$ + $V$)/5 + ($Ni$ + $Cu$)/15` |
| 5c | `cr_eq` | `$Cr$ + $Mo$ + 1.5*$Si$ + 0.5*$Nb$` |
| 5d | `ni_eq` | `$Ni$ + 30*$C$ + 0.5*$Mn$` |

- **Cross-check (Node 5e, Math Formula):** `abs($carbon_equivalent$ - $carbon_equivalent_python$)` → then a
  **Statistics** node: the maximum must be **0** (up to rounding 1e-12).
- **Expected (after Row Filter, 1382 rows):** mean `alloying_total` **18.00**, mean `carbon_equivalent`
  **2.823**, max `carbon_equivalent` **9.563**, max `ni_eq` **109.9**.

### Node 6. Color Manager
- **Settings:** column `family_group`; set the "Neon Forge" colours (colour-blind validated): Carbon & low-alloy
  `#0d9de5` (sky), Stainless `#ff0d89` (hot pink), Cast iron `#ed6300` (electric orange), Tool & high-speed `#a053fd`
  (violet), Weld metal `#5bab0f` (lime), Other `#ef0be8` (magenta).
- **Dark canvas for native views:** in each view node's settings set the background to `#0e0b1e` where the
  option exists (Plot appearance / Background colour); the Python View scripts already use it.
- Every view downstream inherits these colours, so the whole workflow looks consistent.

---

## 2. Section B: Five-number summary and descriptive statistics

### Node 7. GroupBy: five-number summary
- **Settings:** *Groups* tab: no group column (or `family_group` for per-group summaries). *Manual
  Aggregation*: add `tensile_strength_mpa` five times with methods **Minimum**, **Quantile** (parameter
  0.25), **Median**, **Quantile** (0.75), **Maximum**; add **Count** and **Mean**, **Standard deviation**.
  Repeat for `liquidus_c`, `carbon_equivalent`, `alloying_total`.
- **Expected (after the Row Filter, 1382 rows):**

| Variable | n | min | Q1 | median | Q3 | max |
|---|---|---|---|---|---|---|
| tensile_strength_mpa | 1382 | 140 | 510 | 610 | 720 | 2450 |
| liquidus_c | 1382 | 1160 | 1430 | 1450 | 1460 | 1830 |
| carbon_equivalent | 1382 | 0 | 0.577 | 2.487 | 4.787 | 9.563 |
| alloying_total | 1382 | 0.0325 | 2.55 | 11.875 | 31.975 | 70.7 |

  The notebook's five-number table for liquidus, CE and alloy total uses all 1389 grades (e.g. CE median 2.527),
  so those three rows differ slightly from KNIME's 1382-row values; tensile strength is identical (it only exists
  for the 1382). KNIME's quantile interpolation can also differ from pandas by a hair on tied values.

### Node 8. Statistics View [4.7: Statistics]
- **Settings:** include the numeric columns of interest. Open the view: it shows min, max, mean, std,
  skewness, kurtosis, number of missing values and a mini histogram per column.
- **Check:** `tensile_strength_mpa` skewness clearly positive (right tail), mean **651.6** > median 610.

### Node 9. Box Plot (view)
- **Settings:** category column = `family_group`; numeric column = `tensile_strength_mpa`.
- **What to look at:** hover each box: the tooltip shows the five numbers per group. Cast iron lowest, Tool &
  high-speed highest median; many outliers above the Carbon & low-alloy box (spring and maraging grades).
- **Insight:** family sets the strength range; within a family the spread is still a few hundred MPa.

### Node 10. Histogram (view)
- **Settings:** column `tensile_strength_mpa`; number of bins **40**; *Show mean/median* if available.
- **Insight:** right-skewed distribution with a long tail above 1000 MPa.

### Node 11. Numeric Outliers
- **Settings:** column `tensile_strength_mpa`; interquartile range multiplier **1.5**; *Remove outliers* off,
  *append outlier flag* on.
- **Expected:** **75** grades flagged.

---

## 3. Section C: Binning

### Node 12. Auto-Binner: equal width
- **Settings:** column `tensile_strength_mpa`; **Fixed number of bins = 5**; method **Equal width**; append column.
- Then **GroupBy** on the bin column → Count.
- **Expected:** **671 / 650 / 36 / 18 / 7** (KNIME may label the bin edges slightly differently).

### Node 13. Auto-Binner: equal frequency
- **Settings:** same column; **Sample quantiles** 0.0, 0.2, 0.4, 0.6, 0.8, 1.0 (or *Equal frequency*, 5 bins).
- **Expected counts:** **318 / 284 / 240 / 268 / 272** (edges 500, 580, 650, 750 MPa; ties make them unequal).

### Node 14. Numeric Binner: metallurgical carbon bands
- **Settings:** column `C`, append `carbon_band`; intervals:
  - `Low carbon (<=0.25)`: (−∞, 0.25]
  - `Medium carbon (0.25-0.60)`: (0.25, 0.60]
  - `High carbon / tool (0.60-2.1)`: (0.60, 2.1]
  - `Cast-iron range (>2.1)`: (2.1, ∞)
- Add a second Numeric Binner for `carbon_equivalent` → `ce_band`: ≤0.40 *Readily weldable*, ≤0.60 *Preheat
  advised*, >0.60 *Difficult* (use it later only on Carbon & low-alloy rows).

### Node 15. Bar Chart (view): stacked composition of bins
- **Input:** Node 14. **Settings:** category = `carbon_band`; aggregation = *Count*; **split by / stack by**
  `family_group`; normalised (100 %) mode if offered.
- **Insight:** the ">2.1 % C" band is almost entirely cast iron.

---

## 4. Section D: Chi-square tests

### Node 16. Crosstab
- **Settings:** row variable `family_group`, column variable `strength_class`, weight none.
- **Ports:** port 1 = cross-tabulation (counts, expected, deviation, cell chi-square); **port 2 = statistics**.
- **Expected (port 2):** Chi-Square **548.73**, degrees of freedom **10**, p-value ≈ **1.7 × 10⁻¹¹¹**.
- Repeat with (`product_form`, `strength_class`) → χ² **117.37**, df **4**; and (`carbon_band`,
  `strength_class`) → χ² **315.85**, df **6**.
- **Validity note:** more than 20 % of cells have expected counts < 5 in these tables (the low class has only 23
  grades). The Python notebook confirms each result with a Monte-Carlo permutation p-value (all < 0.001).

### Node 17. Python View: residual heatmap + Cramér's V
- **Input:** Node 14 output (needs `family_group`, `strength_class`). Paste
  `docs/knime_python_views/chi_square_residuals.py` into the script editor; change `ROW`/`COL` at the top for
  other pairs.
- **What you see:** each cell shows the count and its standardized residual; red = more grades than independence
  predicts. Cast iron × class 0 shows **22** grades with residual **+20.5**; Cramér's V in the title **0.45**.

### Node 18. Heatmap (view): crosstab counts
- Pivot node (rows `family_group`, columns `strength_class`, Count) → **Heatmap** node on the count columns.
- **Insight:** native alternative to Node 17 for a quick look.

---

## 5. Section E: Correlation and regression

### Node 19. Linear Correlation
- **Settings:** include `C, Mn, Si, Cr, Ni, Mo, V, W, Co, Cu, N, carbon_equivalent, alloying_total,
  tensile_strength_mpa`.
- **View:** colour-coded correlation matrix (Pearson).
- **Node 19b. Rank Correlation:** same columns, **Spearman** → closer to the notebook's clustermap.
- **Insight:** strong Cr–Ni–N and W–V–Mo–Co blocks; carbon is almost uncorrelated with strength across all
  families (Simpson's paradox, explained in notebook 02).

### Node 20. Row Filter → Linear Regression Learner (simple)
- **Row Filter:** `family` = `carbon` → **196** rows.
- **Linear Regression Learner:** target `tensile_strength_mpa`; include only `C`.
- **View / statistics port:** coefficient table and R².
- **Expected:** intercept **429.19**, slope C **428.63** (≈ +43 MPa per 0.1 % C), R² **0.508**, p (C) ≈ 10⁻³¹.

### Node 21. Scatter Plot (view)
- **Input:** Node 20 rows; x = `C`, y = `tensile_strength_mpa`; colour from Color Manager.
- Add the regression line with a **Regression Predictor** → append `Prediction`, and plot it with **Line Plot**
  (x = C, y = Prediction) on the same component layout.
- **Insight:** clear upward trend in carbon steels; the scatter around the line shows grade-to-grade variation.

### Node 22. Rule-based Row Filter → Linear Regression Learner (multiple)
- **Rule-based Row Filter:** `$family_group$ = "Carbon & low-alloy" AND $C$ <= 1 => TRUE` → **574** rows.
- **Learner:** target TS; features `C, Mn, Si, Cr, Ni, Mo, V`.
- **Expected coefficients (MPa per wt%):** Intercept **404.0**, C **648.5**, Mn **−19.6**, Si **193.3**,
  Cr **19.7**, Ni **23.8**, Mo **−74.2**, V **362.2**; R² **0.326**, adjusted R² **0.317**.
- **Insight:** C, Si, V, Ni and Cr raise strength; Mn is not significant. A linear model explains only about a
  third of the variance, which is why the non-linear models in Section I (decision tree, k-NN, random forest)
  are worth building.

---

## 6. Section F: PCA

### Node 23. Math Formula (Multi Column) [4.7: Math Formula (Multi Column) from KNIME Labs]
- **Columns:** `Al, B, C, Co, Cr, Cu, Mn, Mo, N, Nb, Ni, O, P, S, Si, Ti, V, W, Zr, trace_total`
  (the 19 non-rare elements except Fe, plus `trace_total`).
- **Expression:** `ln($$CURRENT_COLUMN$$ + 1)`; *Replace* the columns.
- Why: compositions are heavily skewed; log1p stops a few large values dominating.

### Node 24. Normalizer
- **Settings:** same 20 columns; **Z-score normalization (Gaussian)**.
- KNIME uses the sample standard deviation and Python the population one. That scales every column by the
  same factor, so PCA proportions and k-means groupings are unaffected.

### Node 25. PCA
- **Settings:** the 20 normalized columns; **Dimensions to reduce to: 3** (or *minimum information 80 %* to
  see how many are needed); keep original columns.
- **Expected explained variance:** PC1 **15.0 %**, PC2 **11.8 %**, PC3 **9.5 %**, PC4 **7.6 %**, PC5 **5.9 %**;
  **12** components are needed for 80 %.
- **Node 25b. Bar Chart / Line Plot (scree):** use the PCA node's spectral-decomposition output (eigenvalues)
  → **Math Formula** `$eigenvalue$ / COL_SUM($eigenvalue$)` → Bar Chart.

### Node 26. Scatter Plot: PCA map
- x = `PCA dimension 0`, y = `PCA dimension 1`; colour = `family_group` (Color Manager).
- **Insight:** stainless spreads along PC1 (Cr, Ni, N), high-speed/tool steels along PC2 (V, W, Co); plain
  steels cluster near the origin.
- **Node 26b. Scatter Plot Matrix:** `PCA dimension 0/1/2` + `tensile_strength_mpa`, colour = family group.

---

## 7. Section G: K-means clustering

### Node 27. k-Means
- **Input:** Node 24 (normalized log composition). **Settings:** number of clusters **8**; max iterations 99;
  *Use static random seed* ✓ (any value); include the 20 columns.
- **Output:** appended `Cluster` column; cluster centres on port 2.
- **What to expect:** one very large cluster (the lean plain steels) and several small, chemically sharp ones
  (austenitic stainless, N/Mn-rich stainless, high-speed steel, cast iron). Note the sizes for your report.

### Node 28. Silhouette loop (choosing k)
1. **Counting Loop Start:** from 2 to 12 (KNIME counts iterations from 0, so set iterations = 11 and
   create k with a **Math Formula (Variable)** `$${Icurrentiteration}$$ + 2`).
2. **k-Means** with *Number of clusters* controlled by the flow variable `k` (Flow Variables tab).
3. **Silhouette Coefficient** node (KNIME Labs / Statistics) on the cluster column → overall mean silhouette.
4. **Loop End:** collect rows; add the iteration/k column.
5. **Line Plot:** x = k, y = mean silhouette.
- **What to expect:** the silhouette rises slowly with k and has no sharp elbow (steel chemistry is a
  continuum with dense islands). Pick the best k in a readable range (4–8) and justify it from this plot.

### Node 29. Scatter Plot: clusters on the PCA map
- Join `Cluster` to the PCA output (Joiner on `grade_id`), **Color Manager** on `Cluster`, Scatter Plot of
  PC1 vs PC2.
- **Node 29b. GroupBy** `Cluster` → Median of `C, Cr, Ni, Mo, V, W, Co, tensile_strength_mpa` and *Mode* of
  `family_label` → **Heatmap** of the medians = cluster fingerprints.
- **Insight:** clusters match chemistry (austenitic Cr-Ni, N/Mn-rich, high-speed W/V/Co, cast iron C/Si), while
  carbon, alloy, boron and spring steels share one lean cluster.

---

## 8. Section H: Circular and composition visuals

### Node 30. Pie Chart (donut)
- **Input:** Node 6 output. **Settings:** category `family_group`, aggregation *Count*, **Donut** ✓ (inner
  radius ~60 %), show labels and percentages.
- **Expected:** Carbon & low-alloy 583, Stainless 543, Weld metal 83, Tool & high-speed 82, Cast iron 63,
  Other 28.

### Node 31. Sunburst Chart (ring / two-level donut)
- **Settings:** hierarchy columns `family_group` → `family_label`; frequency = count.
- **Insight:** inner ring = groups, outer ring = families; click a slice to zoom.

### Node 32. GroupBy → Python View: circular column chart
- **GroupBy:** group `family_label`, aggregation **Median** of `tensile_strength_mpa`; **Column Rename**:
  `family_label` → `label`, `Median(tensile_strength_mpa)` → `value`.
- **Python View:** paste `docs/knime_python_views/circular_columns.py`.
- **Expected:** Spring steel **1790**, Maraging **1085**, Nitriding **1025** at the top; Grey cast iron **260** lowest.

### Node 33. GroupBy → Python View: treemap
- **GroupBy:** group `family_label`; aggregations *Count* (`grade_id`) and *Median* (`tensile_strength_mpa`);
  rename to `label`, `size`, `color_value`.
- **Python View:** `docs/knime_python_views/treemap.py`.
- **Insight:** stainless is the biggest tile (543 measured grades, median 630 MPa); spring/maraging tiles are
  small but brightest.

### Node 34. Python View: radar of family groups
- **Input:** Node 6 output (has `family_group` and the element columns).
- **Python View:** `docs/knime_python_views/radar_family_groups.py`.
- **Insight:** each group's composition becomes a shape: Tool & high-speed peaks at W and V, stainless at
  Cr and Ni, cast iron at C and Si.

### Node 35. GroupBy → Python View: circular migration (chord) plot
- **GroupBy:** groups `family_group`, `Cluster` (from Node 27); aggregation *Count*; rename columns to
  `source`, `target`, `count`.
- **Python View:** `docs/knime_python_views/chord_migration.py`.
- **Insight:** left = named family groups, right = chemistry clusters; ribbon width = grades moving from a name
  to a chemistry cluster. Stainless fans out over several clusters; plain steels collapse into one.

### Node 36. CSV Reader → Python View: waterfall
- **CSV Reader:** `exports/tableau/viz/waterfall_cleaning.csv` (keep columns `step`, `value`, `kind`).
- **Python View:** `docs/knime_python_views/waterfall.py`.
- **Expected:** 2672 → −62 → −1221 → **1389** → −7 → **1382**.
- Second instance with `waterfall_ce_aisi4140.csv`: C 0.405 + Mn/6 0.146 + Cr/5 0.190 + Mo/5 0.040 = **0.781**.

### Node 37. Parallel Coordinates Plot
- **Input:** GroupBy `family_group` → Median of `tensile_strength_mpa, liquidus_c, carbon_equivalent,
  alloying_total, C, Cr, Ni, Mo` → **Normalizer (min-max)** → Parallel Coordinates Plot, colour = family group.
- **Insight:** one line per group across eight properties; stainless is high on Cr/Ni/alloy but mid on
  strength.

---

## 9. Section I: Machine learning in KNIME

All models predict from **composition + family + product form only**. Never use `tensile_strength_mpa`,
`strength_class_label` or `is_imputed_ts` as a feature: the strength class is computed from tensile strength,
so including it leaks the answer. Exclude identifiers too (`grade_id`, names, `composition_group_id`, `split`).

### Node 38. Partitioning
- **Input:** Node 6 output (1382 rows, file already sorted train-first).
- **Settings:** **Absolute**, **1117** rows, **Take from top**. Port 1 = train (**1117**), port 2 = test (**265**).
  This reproduces the group-safe `split` column: grades with identical chemistry never sit on both sides.
- **Class target:** for the classifiers, convert `strength_class` to String first (**Number to String**) so
  KNIME treats it as a class, not a number.
- **Baseline to beat:** predicting the majority class gives the accuracy of class 2's share of the test set.
  Compute it with a GroupBy on `strength_class` over port 2.

### Node 39. Decision Tree Learner → Decision Tree Predictor → Scorer
- **Learner:** class column `strength_class`; quality measure **Gini index**; pruning **MDL**; min number
  of records per node **5**; features = 19 elements + `trace_total` + the 4 engineered features + `family`
  + `product_form`.
- **Predictor:** model from the learner, data from Partitioning port 2. **Scorer:** actual `strength_class` vs
  `Prediction (strength_class)` → accuracy, Cohen's κ and the confusion matrix.
- **Decision Tree View:** open the learner's view. The first splits show which families and elements separate
  the classes (expect a family / cast-iron split near the root).

### Node 40. Normalizer → Normalizer (Apply) → K Nearest Neighbor → Scorer
- k-NN works on distances, so scale first: **Normalizer** (min-max 0–1) on the training port's numeric feature
  columns, then **Normalizer (Apply)** with its model on the test port (never fit the scaling on test rows).
- **K Nearest Neighbor:** class column `strength_class`; **k = 5** (try 3, 5, 7, 9 and keep the best);
  *Weight neighbours by distance* ✓. Numeric features only (drop or one-hot the string columns with
  **One to Many** first).
- **Scorer:** as in Node 39. Compare accuracy and κ with the decision tree.

### Node 41. Random Forest Learner (Regression) → Random Forest Predictor (Regression) → Numeric Scorer
- **Learner:** target `tensile_strength_mpa`; same features as Node 39; 100 models; attribute sampling
  *square root*.
- **Numeric Scorer:** R², MAE and RMSE on the test port. Judge MAE against the irreducible-error floor from
  notebook 01 (identical compositions differ by about 111 MPa on average because of heat treatment).
- **Scorer views:** in the classifiers' confusion matrices, errors cluster between classes 1 and 2 near 600 MPa.

---

## 10. Section J: The interactive dashboard (component composite view)

1. Select nodes **9, 10, 15, 17, 21, 26, 29, 30, 31, 32, 34, 35, 36, 39** (Ctrl+click) → right-click →
   **Create Component…** → name `SteelScope Dashboard`.
2. Open the component (Ctrl+double-click) → **Layout Editor** (toolbar button): drag views into a grid:
   - Row 1: Donut (30) · Sunburst (31) · Circular columns (32)
   - Row 2: Box plot (9) · Histogram (10) · Stacked carbon bands (15)
   - Row 3: PCA scatter (26) · Cluster scatter (29) · Chord (35)
   - Row 4: Chi-square heatmap (17) · Regression scatter (21) · Radar (34) · Waterfall (36)
   - Row 5: Decision tree view and confusion matrix (39)
3. **Interactivity:** in each native view's settings tick **Publish selection** and **Subscribe to selection**
   (and *Subscribe to filter*). Selecting a family in the bar/box/scatter views then highlights the same grades
   everywhere. Add a **Value Filter Widget** / **Single Selection Widget** on `family_group` inside the
   component to filter all views at once.
4. Right-click the component → **Execute and Open Views** (5.x: *Open view*). That is the dashboard to screenshot.

---

## 11. Export and screenshots
1. **Images of single views:** most 5.x view nodes have an *image output port*. Enable it in the node settings
   (*Generate image*) → connect **Image Writer (Port)** → `reports/knime_screenshots/<name>.png`. Python
   View nodes also offer an image output in their settings.
2. **Dashboard screenshot:** open the component view → maximise → OS screenshot (Win + Shift + S).
3. **Workflow canvas screenshot:** *File → Export → Export Workflow as SVG* (or a screenshot with all
   annotations visible).
4. **Export the workflow:** right-click the workflow in KNIME Explorer → **Export KNIME Workflow…** →
   tick *Reset workflow before export* (smaller file) → save `SteelScope_Visual_Analytics.knwf`.

---

## 12. Final checklist

| Node | Check | Expected |
|---|---|---|
| 2 Row Filter | rows | 1382 |
| 4 Rule Engine | Carbon & low-alloy / Stainless | 583 / 543 |
| 5e Math Formula check | max abs CE difference | 0 |
| 7 GroupBy | TS min / Q1 / median / Q3 / max | 140 / 510 / 610 / 720 / 2450 |
| 11 Numeric Outliers | TS outliers | 75 |
| 12 / 13 Auto-Binner | equal width / equal frequency | 671·650·36·18·7 / 318·284·240·268·272 |
| 16 Crosstab | family group × class χ², df | 548.73, 10 |
| 20 Linear Regression | slope C, R² | 428.63, 0.508 |
| 22 Linear Regression | R² | 0.326 |
| 25 PCA | PC1 / PC2 variance | 15.0 % / 11.8 % |
| 28 Silhouette | chosen k | your choice, justified by the plot |
| 36 Waterfall | final total | 1382 |
| 38 Partitioning | train / test | 1117 / 265 |
| 39 / 40 Scorer | decision tree / k-NN accuracy, κ | report KNIME's values; both must beat the majority-class baseline |
| 41 Numeric Scorer | random forest R², MAE | report KNIME's values |
