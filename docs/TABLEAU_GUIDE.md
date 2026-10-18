# Tableau guide: SteelScope visual analytics

A step-by-step build guide for someone who has used Tableau only in lab sessions. You will build **20 sheets,
3 interactive dashboards and a Story**, then publish to Tableau Public. Each sheet lists *exactly* what goes on
which shelf, which mark type to pick, how to colour/filter/tooltip it, and the **insight it shows**. Where a
number is quoted, it was printed by the Python code (`notebooks/04_visual_analytics.ipynb` and the CSVs in
`exports/`), so you can check your sheet against it.

> Works in **Tableau Public (free) or Tableau Desktop 2023.x / 2024.x**. Menu names below are from those versions.

---

## 0. Before you start

### 0.1 Files you will use

| File (in `exports/tableau/`) | Rows | What it is | Used by sheets |
|---|---|---|---|
| `steels_wide.csv` | 1389 | One row per steel grade: names, family, strength, liquidus, 30 elements, CE, predictions, clusters | 1–8, 12, 15, 19 |
| `steels_long.csv` | 41 670 | One row per (grade, element): wt% | 16 |
| `viz/chi_square_cells.csv` | 60 | Observed / expected / standardized residual per cell of 5 chi-square tests | 9 |
| `viz/chi_square_tests.csv` | 5 | χ², df, p, Cramér's V per test | 9 (tooltip), 10 |
| `viz/regression_coefficients.csv` | 8 | Multiple-regression coefficients with 95 % CI | 11 |
| `viz/pca_kmeans_scores.csv` | 1389 | PC1–PC3, k-means cluster (k = 8) and silhouette per grade | 12, 13 |
| `viz/kmeans_scan.csv` | 11 | Inertia and silhouette for k = 2…12 | 13 |
| `viz/chord_family_to_cluster.csv`, `viz/chord_raw_class_migration.csv` | 3648 / 1512 | Ready-made polygons for the circular migration (chord) plots | 14 |
| `viz/radial_bars_family_ts.csv` | 408 | Polygons for the circular column chart | 17 |
| `viz/radar_showcase_grades.csv`, `viz/radar_family_composition.csv` | 621 / 510 | Radar polygons + grid lines | 18 |
| `viz/waterfall_cleaning.csv`, `viz/waterfall_ce_aisi4140.csv`, `viz/waterfall_prediction_aisi4140.csv` | 6 / 8 / 10 | Waterfall steps with start/end | 20 |

> **Why helper files?** Tableau has no built-in chord, radar, radial-bar or waterfall chart. The helper
> files already contain the x/y coordinates of every shape, so you only drag fields. The geometry is
> produced by the same Python code that draws the notebook figures.

### 0.2 One data source per file

1. Open Tableau → **Connect → To a File → Text file** → choose `exports/tableau/steels_wide.csv`.
2. For each additional file: **Data → New Data Source → Text file**. Do **not** join or relate these
   files; each sheet uses one data source.
3. Rename each data source (right-click its name at the top of the Data pane → *Rename*), e.g. `Wide`,
   `Long`, `Chi cells`, `Chord family`, `Radar showcase`…

### 0.3 Field types and roles (do this on `Wide` before building)

Tableau usually tidies field names (`tensile_strength_mpa` → *Tensile Strength Mpa*). The formulas below
use the tidied names. If your field still shows the raw name, put that inside the brackets instead.

| Field | Set data type | Set role | How |
|---|---|---|---|
| Grade Id, Display Name, Family, Family Label, Family Group, Product Form, Naming Source, Strength Class Label, Cluster Label | String | Dimension | default |
| Strength Class, Cluster Id, Hdbscan Cluster | Number (whole) | **Dimension** | right-click → *Convert to Dimension* |
| Is Imputed Ts, Liquidus Is Default, Is Stainless Comp | Boolean | Dimension | data-source page: click the type icon → *Boolean* |
| Tensile Strength Mpa, Liquidus C, all element columns, Carbon Equivalent, Alloying Total, Ts Pred Mpa, Residual Mpa, Pca 1/2, Umap 1/2 | Number (decimal) | Measure | default |

In every helper file: **Point Order** → Number (whole), keep as *Measure*. **X**, **Y** → Number (decimal),
Measure.

### 0.4 Global setting for the shape sheets

For sheets 14, 17 and 18 you need one mark per CSV row: **Analysis menu → untick *Aggregate Measures***
(on that sheet only).

---

## 1. Calculated fields (data source `Wide`)

Create each with **Analysis → Create Calculated Field…**. Type the name and paste the formula exactly.

| # | Name | Formula | Why |
|---|---|---|---|
| C1 | `Measured TS` | `IF NOT [Is Imputed Ts] THEN [Tensile Strength Mpa] END` | Strength without the 7 unmeasured grades (they are NULL anyway; this makes the intent explicit) |
| C2 | `Liquidus Type` | `IF [Liquidus Is Default] THEN "Default 1460 °C" ELSE "Grade-specific" END` | Hollow vs filled marks in the design-space chart |
| C3 | `Carbon Band` | `IF [C] <= 0.25 THEN "1 Low carbon (≤0.25)" ELSEIF [C] <= 0.60 THEN "2 Medium carbon (0.25–0.60)" ELSEIF [C] <= 2.1 THEN "3 High carbon / tool (0.60–2.1)" ELSE "4 Cast-iron range (>2.1)" END` | Domain binning (the numeric prefix keeps the sort order) |
| C4 | `Alloy Band` | `IF [Alloying Total] < 5 THEN "1 Lean (<5 %)" ELSEIF [Alloying Total] < 10 THEN "2 Medium (5–10 %)" ELSEIF [Alloying Total] < 30 THEN "3 High (10–30 %)" ELSE "4 Very high (>30 %)" END` | Domain binning |
| C5 | `CE Weldability` | `IF [Family Group] = "Carbon & low-alloy" THEN (IF [Carbon Equivalent] <= 0.40 THEN "Readily weldable" ELSEIF [Carbon Equivalent] <= 0.60 THEN "Preheat advised" ELSE "Difficult" END) END` | IIW CE bands, plain steels only |
| C6 | `TS Quintile` | `IF [Measured TS] <= {FIXED : PERCENTILE([Measured TS], 0.2)} THEN "Q1" ELSEIF [Measured TS] <= {FIXED : PERCENTILE([Measured TS], 0.4)} THEN "Q2" ELSEIF [Measured TS] <= {FIXED : PERCENTILE([Measured TS], 0.6)} THEN "Q3" ELSEIF [Measured TS] <= {FIXED : PERCENTILE([Measured TS], 0.8)} THEN "Q4" ELSEIF NOT ISNULL([Measured TS]) THEN "Q5" END` | Equal-frequency (quantile) bins |
| C7 | `TS z within family` | `([Measured TS] - {FIXED [Family] : AVG([Measured TS])}) / {FIXED [Family] : STDEV([Measured TS])}` | How unusual a grade is inside its own family |
| C8 | `Interval Width` | `[Ts Pred Hi Mpa] - [Ts Pred Lo Mpa]` | Width of the model's 80 % prediction range |
| C9 | `Abs Residual` | `ABS([Residual Mpa])` | Model error per grade |
| C10 | `Grades` | `COUNTD([Grade Id])` | Clean count measure |
| C11 | `Share of Grades` | `[Grades] / TOTAL([Grades])` | Percent-of-total for stacked bars and donuts (table calculation) |
| C13 | `Equal Width Bin` | `MIN(INT(([Measured TS] - 140) / 462), 4) + 1` | 5 equal-width bins of 462 MPa starting at the minimum (Tableau's own bins start at 0, so they cannot reproduce this) |
| C12 | `Five-number label` | `"min " + STR(ROUND(MIN([Measured TS]),0)) + " · Q1 " + STR(ROUND(PERCENTILE([Measured TS],0.25),0)) + " · median " + STR(ROUND(MEDIAN([Measured TS]),0)) + " · Q3 " + STR(ROUND(PERCENTILE([Measured TS],0.75),0)) + " · max " + STR(ROUND(MAX([Measured TS]),0))` | Text tile with the five-number summary |

Waterfall data sources (`waterfall_*.csv`): create `Bar Size` = `[Start] - [End]` and
`Direction` = `IF [Kind] = "total" THEN "Total" ELSEIF [Value] >= 0 THEN "Increase" ELSE "Decrease" END`.

Chi-square cells source: create `Residual Label` = `STR([Observed]) + CHAR(10) + "(" + STR(ROUND([Std Residual],1)) + ")"`.

**Check:** drag `Measured TS` to Text → it shows the SUM; change the aggregation to **Count** → **1382**. `Grades` → **1389**.

---

## 2. Colour plan: the "Neon Forge" look (use it everywhere)

The Python figures use a midnight canvas with neon, colour-blind-validated hues. Recreate it in Tableau so
the dashboards and the notebook look like one product.

### 2.1 Install the palettes once (Preferences.tps)
1. Close Tableau. Open `Documents/My Tableau Repository/Preferences.tps` in Notepad (create it if missing).
2. Replace its content with:
```xml
<?xml version='1.0'?>
<workbook>
  <preferences>
    <color-palette name="Neon Forge" type="regular">
      <color>#0d9de5</color> <color>#ff0d89</color> <color>#ed6300</color> <color>#a053fd</color>
      <color>#5bab0f</color> <color>#ef0be8</color> <color>#07a4a4</color> <color>#c58501</color>
    </color-palette>
    <color-palette name="Neon Plasma" type="ordered-sequential">
      <color>#5102a3</color> <color>#8a09a5</color> <color>#b83289</color> <color>#da5b69</color>
      <color>#f48849</color> <color>#febd2a</color> <color>#f0f921</color>
    </color-palette>
    <color-palette name="Neon Sky-Pink" type="ordered-diverging">
      <color>#0d9de5</color> <color>#2b2547</color> <color>#ff0d89</color>
    </color-palette>
  </preferences>
</workbook>
```
3. Reopen Tableau. The three palettes now appear in every **Edit Colors** dialog.

### 2.2 Family-group colours (assign once, Tableau reuses them on every sheet)

| Family Group | Colour | Hex |
|---|---|---|
| Carbon & low-alloy | sky | `#0d9de5` |
| Stainless | hot pink | `#ff0d89` |
| Cast iron | electric orange | `#ed6300` |
| Tool & high-speed | violet | `#a053fd` |
| Weld metal | lime | `#5bab0f` |
| Other | magenta | `#ef0be8` |

Drag `Family Group` to Color → **Edit Colors…** → palette *Neon Forge* → **Assign Palette** (the order above
matches the palette order).

### 2.3 Rules that keep it beautiful *and* readable
- **Scatter plots:** at most three neon hues (sky, pink, orange) and the rest in a dim violet-grey `#4b4470`.
  These three were validated as distinguishable for colour-blind viewers in every pairing.
- **Magnitudes** (heatmap cells, treemap colour, histogram bins): *Neon Plasma*, which runs indigo → magenta →
  orange → gold. **Plus/minus** values (chi-square residuals, loadings): *Neon Sky-Pink*, centred at 0.
- **Story accent:** use gold `#ffd166` only for annotation lines, callout borders and the one mark the sheet's
  story is about. Never use it as a data colour.
- **Canvas:** Format → Workbook → set *Worksheets* and *Dashboards* shading to `#0e0b1e`, fonts to white
  (titles) and lavender `#d4ceef` (labels); gridlines `#251f45`. Add Annotations (right-click a mark →
  **Annotate → Mark…**) with a gold border for the story beats listed under each sheet.

## 3. Sheets

> For every sheet: give it a title that states the insight (double-click the title), and make sure the
> tooltip (Marks → Tooltip) shows the grade or category name plus the measured values.

### Sheet 1: KPI tiles ("BANs")
- **Data:** Wide. **Mark:** Text.
- Build four small sheets (or one with Measure Names): `Grades` (1389), `CNT(Measured TS)` (1382),
  `MEDIAN(Measured TS)` (610), `MEDIAN(Liquidus C)` (1450).
- Text: font 28 pt bold, label underneath in 10 pt.
- **Insight:** dataset size after cleaning and the typical grade (610 MPa, 1450 °C).

### Sheet 2: Five-number summary box plot by family group
- **Data:** Wide. **Columns:** `Measured TS`. **Rows:** `Family Group`. **Detail:** `Grade Id`.
- Analysis → untick nothing (keep aggregation); the Grade Id on Detail gives one dot per grade.
- **Mark:** Circle, size small, opacity 50 %. **Color:** `Family Group`.
- **Analytics pane → Box Plot** → drop on *Cell*. Edit the box plot (right-click axis → Edit Box Plot):
  whiskers = *Data within 1.5 times the IQR*, fill = light grey.
- **Reference line:** Analytics → *Reference Line* → Per Cell → Value = Median → Label = Value.
- **Sort:** Family Group by `MEDIAN(Measured TS)` ascending.
- **Tooltip:** `<Display Name>`, TS, liquidus.
- **Check (whole dataset, remove Family Group from Rows temporarily):** hover the box → lower hinge **510**,
  median **610**, upper hinge **720**, minimum **140**, maximum **2450**.
- **Insight:** families shift the whole distribution; cast iron sits lowest, tool & high-speed highest;
  many high-strength outliers sit above the whiskers (75 Tukey outliers overall).

### Sheet 3: Five-number summary tile
- **Data:** Wide. **Mark:** Text. **Text:** `Five-number label`. **Rows:** `Family Group` (optional).
- **Insight:** the numbers behind sheet 2, readable without hovering.

### Sheet 4: Histogram with bins
- Right-click `Measured TS` → **Create → Bins…** → size **50** → creates `Measured TS (bin)`.
- **Columns:** `Measured TS (bin)` (continuous: right-click → *Continuous*). **Rows:** `CNT(Grade Id)`.
- **Mark:** Bar. **Color:** `Family Group` (stacked). **Filter:** `Is Imputed Ts` = False.
- **Reference line:** Average and Median of `Measured TS` (Analytics → Reference Line → Table).
- **Insight:** right-skewed distribution: mean 651.6 > median 610 MPa.

### Sheet 5: Equal-width vs equal-frequency bins
- **Left view:** Columns `Equal Width Bin` (C13, convert to Dimension); Rows `CNT(Grade Id)`.
  **Check:** **671 / 650 / 36 / 18 / 7** grades (bins of 462 MPa from 140 to 2450).
- **Right view:** Columns `TS Quintile`; Rows `CNT(Grade Id)`. **Check:** **318 / 284 / 240 / 268 / 272**.
  (Python's quantile edges are 500 / 580 / 650 / 750 MPa; ties at those values make the counts unequal.)
- Put both on the dashboard side by side.
- **Insight:** equal-width bins hide the detail in the dense 400–800 MPa range; quantile bins balance the
  counts but stretch the top bin from 750 to 2450 MPa.

### Sheet 6: Domain bins, 100 % stacked bars
- **Rows:** `Carbon Band`. **Columns:** `Grades` → right-click → *Quick Table Calculation → Percent of Total*
  → *Compute Using → Table (across)*. **Color:** `Family Group`. **Label:** the percentage.
- Duplicate the sheet and swap `Carbon Band` for `Alloy Band`, Color = `Strength Class Label`.
- **Insight:** the ">2.1 % C" band is almost entirely cast iron; the share of high-strength grades rises
  with alloy content.

### Sheet 7: Strength vs liquidus design space (scatter)
- **Columns:** `Liquidus C`. **Rows:** `Measured TS`. **Detail:** `Grade Id`.
- **Mark:** Shape. **Shape:** `Liquidus Type` (filled circle = grade-specific, open circle = default).
  **Color:** `Family Group`.
- **Filters (show them):** `Family Group`, `Product Form`, `Naming Source`, `Liquidus Type`.
- **Insight:** strength and liquidus are near-independent axes (Python Spearman ρ = 0.00 over all grades);
  the vertical stripe at 1460 °C is the default value, not physics.

### Sheet 8: Correlation heatmap (from the long table)
- Easiest route: create the Spearman matrix in Python (already in the notebook) and show it here as a
  highlight table, or build a Pearson heatmap in Tableau:
  - **Data:** Wide. Create one calculated field per pair, e.g. `corr C-TS` = `CORR([C], [Measured TS])`.
  - For a full matrix use the notebook figure `04_10_correlation_clustermap.png` (Dashboard → Image object).
- **Insight:** elements that travel together (Cr-Ni-N, W-V-Mo-Co) and the weak overall link of C to strength.

### Sheet 9: Chi-square residual highlight table
- **Data:** Chi cells. **Filter:** `Test` (single value, show filter).
- **Columns:** `Col Value`. **Rows:** `Row Value`. **Mark:** Square.
- **Color:** `AVG(Std Residual)` → Edit Colors → *Neon Sky-Pink*, **Center = 0**, tick *Use full colour range*.
- **Story beat:** annotate Cast iron × Low (<300) with a gold border: "22 grades where chance expects ~1".
- **Label:** `Residual Label`.
- **Tooltip:** observed, expected, residual.
- **Check (Family group × strength class):** Cast iron × Low (<300) = **22** grades, residual **+20.5**.
- **Insight:** red cells hold more grades than independence predicts. Cast irons are the low-strength
  class; tool & high-speed steels over-index in the high class.

### Sheet 10: Cramér's V lollipop
- **Data:** chi_square_tests.csv. **Rows:** `Test`. **Columns:** `Cramers V` twice → dual axis →
  synchronise. First mark = Bar (size thin), second = Circle (large).
- **Label:** `Cramers V` (2 decimals) and `P Permutation`.
- **Check:** Family group × default liquidus **0.67**, Family group × strength class **0.45**, CE band ×
  class **0.41**, Carbon band × class **0.34**, Product form × class **0.21**.
- **Insight:** all associations are significant; Cramér's V ranks how strong they are.

### Sheet 11: Regression: trend line and coefficient forest plot
**11a. Simple regression with trend line**
- **Data:** Wide. **Filter:** `Family` = carbon.
- **Columns:** `C`. **Rows:** `Measured TS`. **Detail:** `Grade Id`. **Mark:** Circle.
- **Analytics → Trend Line → Linear** (drop on the model). Right-click the line → **Edit Trend Lines** →
  tick *Show Confidence Bands*.
- Right-click the line → **Describe Trend Model…**
- **Check:** n = **196**, slope **428.6**, intercept **429.2**, R² **0.508**, p < 0.0001.
- **Insight:** in carbon steels about half the variation in strength is explained by carbon alone:
  +43 MPa per 0.1 % C.

**11b. Forest plot of the multiple regression**
- **Data:** regression_coefficients.csv. **Filter:** `Term` ≠ Intercept.
- **Rows:** `Term`. **Columns:** `Standardized Beta`. **Mark:** Circle.
- For the confidence interval use the raw-unit columns: **Columns** `Ci95 Low` → Mark **Gantt Bar**,
  **Size** = calc `[Ci95 High] - [Ci95 Low]`. Put both on a dual axis if you want both scales.
- **Check:** coef C **648.5** MPa/wt%, Si **193.3**, V **362.2**, Mn **−19.6** (not significant), R² **0.326**.
- **Insight:** C, Si, V, Ni and Cr raise strength in plain steels, but a linear model explains only about a
  third of the variance.

### Sheet 12: PCA scatter (biplot without arrows)
- **Data:** pca_kmeans_scores.csv. **Columns:** `PC1`. **Rows:** `PC2`. **Detail:** `Grade Id`.
- **Color:** `Family Group` (only the 3 big groups coloured; set the other three to grey in Edit Colors).
- **Tooltip:** Display Name, family, TS.
- **Axis titles:** "PC1 (15.0 % of variance)", "PC2 (11.8 % of variance)".
- **Insight:** stainless grades spread along PC1 (Cr, Ni, N), high-speed/tool steels along PC2 (V, W, Co),
  and plain steels cluster tightly near the origin.

### Sheet 13: K-means: native clustering and the elbow
**13a. Tableau's own clustering**
- **Data:** Wide. **Columns:** `Cr`, **Rows:** `Ni`, **Detail:** `Grade Id`.
- **Analytics → Cluster** → drop on the view. In the dialog add variables `C, Mn, Si, Cr, Ni, Mo, V, W, Co,
  Cu, N` and set **Number of clusters = 8**.
- Right-click the Clusters pill on Color → **Describe Clusters** → note the F-statistics (most separating
  elements) and the cluster sizes.
- Tableau standardises with min-max scaling and its own initialisation, so expect a different split from
  Python. Python's k = 8 cluster sizes (log1p + z-score composition) are **704 / 377 / 84 / 73 / 65 / 43 / 25 / 18**.

**13b. Python clusters on the PCA plane**
- **Data:** pca_kmeans_scores.csv. Columns `PC1`, Rows `PC2`, **Color:** `Cluster Name`, Detail `Grade Id`.
- **13c. Elbow:** data kmeans_scan.csv, Columns `K` (dimension), Rows `Silhouette` (line + circle). Dual axis
  with `Inertia` is **not** recommended (two scales mislead); make a second small sheet for inertia instead.
- **Insight:** clusters recover chemistry-defined families (austenitic, N/Mn-rich, high-speed, cast iron), while
  carbon, alloy, boron and spring steels mostly share one lean cluster.

### Sheet 14: Circular migration plot (chord diagram)
- **Data:** Chord family (`chord_family_to_cluster.csv`). **Analysis → Aggregate Measures: OFF.**
- **Columns:** `X`. **Rows:** `Y`. **Mark:** **Polygon**.
- **Path:** `Point Order`. **Detail:** `Shape Id`. **Color:** `Color Key` (family-group colours from §2.2;
  set "destination" to pale lavender `#e9e4ff`). **Opacity:** 75 %.
- Right-click each axis → **Edit Axis** → fixed range **−1.8 to 1.8** for both, then hide the axes
  (right-click → uncheck *Show Header*) and remove gridlines (Format → Lines → None).
- **Labels:** drag `Label X` to Columns and `Label Y` to Rows next to the existing pills → right-click each
  new pill → **Dual Axis** → **Synchronize Axis**. On the new marks card choose **Text**, put `Label` on Text,
  `Shape Id` on Detail.
- **Tooltip:** `Source`, `Target`, `Value` ("<Value> grades migrate from <Source> to <Target>").
- Repeat with `chord_raw_class_migration.csv` for the second plot (raw Class → cleaned outcome).
- **Check:** the ribbon from *Carbon & low-alloy* to the largest cluster carries the most grades; raw class 2 sends
  **871** rows to "Merged into twin listing" and **7** to "Unmeasured TS (excluded)".
- **Insight:** stainless grades fan out over several chemistry clusters, while plain-steel family names
  collapse into one lean cluster. In the raw-class chord, the imputed rows almost all disappear into the twin merge.

### Sheet 15: Ring (donut) diagram
- **Data:** Wide. **Rows:** type `MIN(0)` twice (double-click Rows, type `MIN(0)`, Enter; repeat).
- First marks card: **Pie**, Angle = `Grades`, Color = `Family Group`, Label = `Family Group` + `Grades`.
- Second marks card: **Circle**, remove all fields, colour = the worksheet background, size smaller than the pie.
- Right-click the second `MIN(0)` → **Dual Axis**; Synchronize; hide headers.
- Centre text: on the second card put `Grades` on Label (shows **1389**).
- For the outer ring (families), duplicate the sheet with Color = `Family Label`.
- **Insight:** stainless (546) and carbon & low-alloy (583) are 81 % of all grades.

### Sheet 16: Treemap
- **Data:** Wide. Drag `Family Group` to Detail, `Family Label` to Detail, `Grades` to Size,
  `MEDIAN(Measured TS)` to Color (*Neon Plasma*; Edit Colors → *End* at 1100 so one extreme family does not
  flatten the scale). Mark becomes **Square** automatically (or use Show Me → Treemap).
- **Label:** Family Label, Grades, Median TS.
- Composition variant: data Long, Detail = `Element`, Size = `SUM(Wt Pct)`, filter `Element` ≠ Fe,
  Color = `Element Role`.
- **Insight:** area shows how many grades exist and colour shows how strong they are: spring and maraging
  tiles are small but the brightest.

### Sheet 17: Circular column chart (radial bars)
- **Data:** radial_bars_family_ts.csv. **Aggregate Measures: OFF.**
- **Columns:** `X`, **Rows:** `Y`, **Mark:** Polygon, **Path:** `Point Order`, **Detail:** `Bar`,
  **Color:** `Family Group`. Fix both axes to −1.3…1.3 and hide them.
- Labels: dual axis with `AVG(X)`/`AVG(Y)` on a Text mark showing `Bar` and `Value`, filtered to
  `Point Order` = 18 (the middle of each bar's outer edge).
- **Insight:** ranks families by median strength at a glance: spring 1790, maraging 1085, nitriding 1025 MPa
  at the top; grey cast iron 260 MPa at the bottom.

### Sheet 18: Radar charts
- **Data:** Radar showcase (`radar_showcase_grades.csv`). **Aggregate Measures: OFF.**
- Create two calculated fields in this data source:
  - `Data Only Y` = `IF [Layer] = "data" THEN [Y] END` (the polygon layer)
  - `Axis Label Text` = `IF [Layer] = "axis_label" THEN [Axis] END`
- **Columns:** `Entity` (discrete, one radar per alloy) then `X`. **Rows:** `Y`.
- **Marks card 1 (Y): Line.** Path = `Point Order`, Detail = `Shape Id`, Color = `Layer`
  (data = the alloy's family-group colour, grid = `#251f45`, axis_label = fully transparent), Label = `Axis Label Text`
  (Label → *Allow labels to overlap other marks*).
- **Fill (optional):** drag `Data Only Y` to Rows next to `Y` → right-click → **Dual Axis** → **Synchronize
  Axis**. On marks card 2 choose **Polygon**, Path = `Point Order`, Detail = `Shape Id`, Color = orange at 35 %
  opacity. Grid rows have NULL in `Data Only Y`, so only the alloy shape is filled.
- Fix both axes to −1.3…1.3 and hide headers, so every panel is a perfect circle-sized square.
- **Filter:** `Entity` (multi-select, show filter) so viewers can pick alloys; `Layer` must stay unfiltered.
- Repeat with `radar_family_composition.csv` (one radar per family group; tooltip shows `Median Wt Pct`).
- **Check:** AISI 316's Mo spoke is near the outer ring; 17-4 PH reaches about the 90th percentile in tensile
  strength with a mid-range Ni spoke.
- **Insight:** each alloy becomes a recognisable shape: high-speed steels max out W/V/Co/Mo; stainless Cr/Ni;
  cast iron C/Si.

### Sheet 19: Model error and uncertainty
- **Data:** Wide. **Columns:** `Measured TS`. **Rows:** `Ts Pred Mpa`. **Detail:** `Grade Id`.
  **Color:** `Abs Residual` (*Neon Plasma*). Add a reference line y = x: Analytics → Trend Line is not it; instead
  create a calculated field `Identity` = `[Measured TS]` and put it on a dual axis as a Line.
- Second view: **Rows** `Family Label`, **Columns** `AVG(Abs Residual)`, Bar, sorted.
- **Insight:** errors are small where chemistry decides strength and large in heat-treatment-defined families
  (maraging, ductile and malleable irons).

### Sheet 20: Waterfall charts
- **Data:** waterfall_cleaning.csv.
- **Columns:** `Step` (sort: Manual, or by `Row Id` ascending). **Rows:** `SUM(End)`.
- **Mark:** **Gantt Bar**. **Size:** `SUM(Bar Size)`. **Color:** `Direction` (Total = sky `#0d9de5`,
  Increase = lime `#5bab0f`, Decrease = hot pink `#ff0d89`).
- **Story beat:** annotate the twin-listing bar: "The big secret: 1,221 rows were the same steel written twice". **Label:** `SUM(Value)`.
- **Check:** 2672 → −62 → −1221 → **1389** → −7 → **1382**.
- Repeat with `waterfall_ce_aisi4140.csv` (C 0.405 + Mn/6 0.146 + Cr/5 0.190 + Mo/5 0.040 = **CE 0.781**) and
  `waterfall_prediction_aisi4140.csv` (average prediction → SHAP pushes → predicted TS). For the prediction
  waterfall right-click the axis → Edit Axis → untick *Include zero* and state the starting value in the title.
- **Insight:** twin listings, not duplicates or missing values, are the dominant data issue; for AISI 4140
  carbon and chromium make up most of the carbon equivalent.

---

## 4. Dashboards (Dashboard → New Dashboard; Size: *Automatic* or 1366 × 768)

### Dashboard A: Strength Explorer
- **Layout:** top row = Sheet 1 tiles; middle = Sheet 7 (scatter, large, left) + Sheet 16 (treemap, right);
  bottom = Sheet 2 (box plot).
- **Filters:** show `Family Group`, `Product Form`, `Liquidus Type` from Sheet 7 → right-click each filter →
  *Apply to Worksheets → All Using This Data Source*.
- **Actions:** Dashboard → Actions → Add Action:
  1. **Filter action** "Treemap filters scatter": Source = Sheet 16, Run on = *Select*, Target = Sheet 7 and
     Sheet 2, Clearing = *Show all values*.
  2. **Highlight action** "Hover family": Source = Sheet 2, Run on = *Hover*, Target = Sheet 7, Fields =
     `Family Group`.
- **Story it tells:** pick a family in the treemap → the scatter shows where its grades sit in strength and
  melting range, and the box plot shows the spread.

### Dashboard B: Statistics Lab
- **Layout:** Sheet 3 (five-number tile) + Sheet 4 (histogram) on top; Sheet 5 (both binning views) middle;
  Sheet 9 (chi-square heatmap) + Sheet 10 (Cramér's V) bottom; Sheet 11a on the right.
- **Parameter:** create `Bin Size` (integer, 25–200, step 25). Edit the `Measured TS (bin)` field to use it,
  right-click the parameter → *Show Parameter*. Students can change the histogram resolution live.
- **Action:** Filter action from Sheet 10 (Source, *Select*) to Sheet 9 on field `Test`, so clicking a lollipop
  switches the heatmap to that test.

### Dashboard C: Circular & Composition Gallery
- **Layout:** Sheet 14 (chord) large on the left; Sheet 18 (radar trellis) on the right; Sheet 17 (radial
  columns) and Sheet 15 (donut) at the bottom; Sheet 20 (waterfall) as a floating panel or second tab.
- **Action:** Highlight action from Sheet 15 (donut, *Select*) to Sheets 16/17 on `Family Group`.
- Add a **Text object** explaining how to read a chord diagram: "ribbon width = number of grades; left =
  from, right = to".

---

## 5. Story (Story → New Story)
Create 6 story points, each with a one-line caption:
1. "2672 listings are really 1389 grades": Sheet 20 (cleaning waterfall).
2. "Family sets the strength range": Dashboard A with Spring selected in the treemap.
3. "Skewed data: medians, not means": Sheet 4 + Sheet 5.
4. "Associations are real and measurable": Dashboard B with the chi-square heatmap.
5. "Chemistry clusters vs family names": Sheet 14.
6. "Each alloy has a fingerprint": Sheet 18 with 304 / 316 / 17-4 PH selected.

---

## 6. Publish to Tableau Public
1. **Data → (each data source) → Extract Data…** → *Extract*. Tableau Public requires extracts; it does this
   automatically on save, but extracting first avoids surprises.
2. **File → Save to Tableau Public As…** → sign in → name the workbook *SteelScope Visual Analytics*.
3. In the browser that opens: **Edit Details** → add a description and set the Story as the default view
   (*Toggle tabs* on so all dashboards are reachable).
4. Copy the share link into `docs/PROJECT_JOURNEY.md` and your report.
5. Take screenshots: **Dashboard → Export Image…** for each dashboard (PNG) and save them in
   `reports/tableau_screenshots/`.

---

## 7. Final checklist

| Check | Expected |
|---|---|
| Count of `Measured TS` | 1382 |
| Count of grades | 1389 |
| Box plot (all grades): Q1 / median / Q3 | 510 / 610 / 720 MPa |
| Equal-width 5-bin counts | 671 / 650 / 36 / 18 / 7 |
| Quintile counts | 318 / 284 / 240 / 268 / 272 |
| Chi-square family group × class | χ² = 548.7, df = 10, V = 0.45 |
| Trend line (carbon steels) | slope 428.6, R² 0.508 |
| PCA variance (PC1 / PC2) | 15.0 % / 11.8 % |
| Cleaning waterfall | 2672 → 2610 → 1389 → 1382 |
| AISI 4140 carbon equivalent | 0.781 |
