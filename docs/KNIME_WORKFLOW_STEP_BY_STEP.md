# KNIME: build the SteelScope workflow, step by step

This is the **hands-on build sheet**. It tells you *which button to press*, *which node to connect to which*, and
*what to check before moving on*. The settings and the expected numbers for every node live in
[KNIME_GUIDE.md](KNIME_GUIDE.md); the node numbers here are the same, so keep both open side by side.

```
How to use this file
  Part 1  KNIME in 10 minutes      the six moves you repeat for every node
  Part 2  The workflow map         the whole canvas on one screen: what connects to what
  Part 3  Build it, section by section  (A → J), with a checkpoint after each section
  Part 4  Python View nodes        how to paste and run the 6 chart scripts
  Part 5  Dashboard, export, submit
  Part 6  Troubleshooting
```

---

## Part 1. KNIME in 10 minutes

### 1.1 The screen

| Area | 5.x modern UI | 4.7 / classic UI | What it is for |
|---|---|---|---|
| Workflow canvas | centre | centre | where you drop and wire nodes |
| Node repository | left panel, **Nodes** tab (search box at the top) | bottom-left *Node Repository* | the catalogue of nodes |
| Explorer / Space | left panel, **Space** tab | top-left *KNIME Explorer* | your workflows and their files |
| Description | right panel when a node is selected | right *Description* | what the selected node does, its ports and options |
| Output preview | bottom panel when a node is selected | right-click → output table | the table a node produced |

### 1.2 The six moves (you repeat these ~70 times)

| # | Move | How |
|---|---|---|
| 1 | **Add a node** | type its name into the repository search box → drag it onto the canvas (or double-click it to drop it next to the selected node) |
| 2 | **Connect** | drag from the small **output triangle** on the right edge of node A to the **input triangle** on the left edge of node B. Black triangle = data table, blue square = model, red circle = flow variable |
| 3 | **Configure** | double-click the node (or select it and press **F6**). Fill the settings, click **OK** / **Apply and Close** |
| 4 | **Execute** | select the node and press **F7** (or right-click → *Execute*). **Shift + F7** runs every node in the workflow |
| 5 | **Look at the result** | data: right-click → *output table* (5.x: just click the node and look at the bottom panel). Charts: right-click → **Open view** |
| 6 | **Reset** | right-click → *Reset* (**F8**). Needed when you change settings of a node that already ran |

**Traffic light under every node:** 🔴 red = not configured, 🟡 yellow = configured but not run, 🟢 green =
executed. A ⚠ triangle is a warning (hover it to read it); a ❌ is an error (hover, fix, re-execute).

**Shortcut while wiring (5.x):** drag from an output port and release on an *empty* spot of the canvas → a quick
search pops up → type the next node's name → Enter. It adds the node *and* the connection in one move.

### 1.3 Before you build

1. **Python:** *Preferences* (5.x: menu ☰ → *Preferences*; 4.7: *File → Preferences*) → **KNIME → Python** →
   *Bundled environment* → Apply. Install the **KNIME Python Integration** extension first if it is missing
   (*Install KNIME Extensions…*, search "Python").
2. **New workflow:** in the Space/Explorer panel, right-click *LOCAL* → **New workflow** →
   `SteelScope_Visual_Analytics`.
3. **Put the data inside the workflow** (so the exported `.knwf` works on your faculty's PC too):
   right-click the workflow in the Explorer → *Show in File Explorer* (4.7: *Open file location*). Inside that
   folder create a folder **`data`** and copy into it:
   - `exports/knime/knime_input.csv`
   - `exports/knime/viz_expected_values.csv`
   - `exports/tableau/viz/waterfall_cleaning.csv`
   - `exports/tableau/viz/waterfall_ce_aisi4140.csv`

   In every CSV Reader you then set **Read from: Relative to → Current workflow data area** and type just the
   file name.
4. **Save often:** **Ctrl + S** after every section.

---

## Part 2. The workflow map

Read it left → right. `MAIN` is the output of Node 6 (1382 measured grades, with `family_group`, the four
engineered features and colours attached). Almost every branch starts from `MAIN`, so the canvas looks like a
tree: one trunk (Section A) and many branches.

```
 SECTION A  READ · CLEAN · ENRICH
 [1 CSV Reader]──▶[2 Row Filter]──▶[4 Rule Engine]──▶[5a]──▶[5b]──▶[5c]──▶[5d Math Formula]──▶[6 Color Manager]══▶ MAIN
                        ├──▶[3 Duplicate Row Filter]                                                   (1382 rows)
                        └──▶[3b Duplicate Row Filter]──▶[GroupBy]
 MAIN──▶[5e Math Formula]──▶[Statistics]              (CE cross-check: max difference 0)

 SECTION B  FIVE NUMBERS            SECTION C  BINNING
 MAIN──▶[7 GroupBy]                 MAIN──▶[12 Auto-Binner equal width]──▶[GroupBy]
 MAIN──▶[8 Statistics View]         MAIN──▶[13 Auto-Binner equal freq.]──▶[GroupBy]
 MAIN──▶[9 Box Plot]                MAIN──▶[14 Numeric Binner C]──▶[14b Numeric Binner CE]══▶ BANDED
 MAIN──▶[10 Histogram]              BANDED──▶[15 Bar Chart]
 MAIN──▶[11 Numeric Outliers]

 SECTION D  CHI-SQUARE              SECTION E  CORRELATION · REGRESSION
 BANDED──▶[16 Crosstab]             MAIN──▶[19 Linear Correlation]     MAIN──▶[19b Rank Correlation]
 BANDED──▶[17 Python View χ²]       MAIN──▶[20 Row Filter carbon]──┬──▶[20b LR Learner]─(model)─┐
 BANDED──▶[18 Pivot]──▶[Heatmap]                                  └────────────(data)──────────▶[21a Regression Predictor]
                                                                   [21a]──▶[21b Sorter]──┬──▶[21 Scatter Plot]
                                                                                         └──▶[21c Line Plot]
                                    MAIN──▶[22 Rule-based Row Filter]──▶[22b LR Learner]

 SECTION F + G  PCA · K-MEANS
 MAIN──▶[23 Math Formula (Multi Column)]──▶[24 Normalizer]──┬──▶[25 PCA]══▶ PCA ──┬──▶[26 Scatter Plot]
                                                             │                     ├──▶[26b Scatter Plot Matrix]
                                                             │                     ├──▶[25b Bar Chart (scree)]  (PCA model/eigen port)
                                                             │                     └──▶[27 k-Means]══▶ CLUSTERED
                                                             └──▶[28 Counting Loop Start]──▶[Math Formula (Variable)]──▶[k-Means]
                                                                    ──▶[Silhouette Coefficient]──▶[Loop End]──▶[Line Plot]
 CLUSTERED──▶[29a Color Manager]──▶[29 Scatter Plot]
 CLUSTERED──▶[29b GroupBy]──▶[29c Heatmap]

 SECTION H  CIRCULAR AND COMPOSITION VISUALS
 MAIN──▶[30 Pie Chart (donut)]
 MAIN──▶[31 Sunburst Chart]
 MAIN──▶[32a GroupBy]──▶[32b Column Renamer]──▶[32 Python View: circular columns]
 MAIN──▶[33a GroupBy]──▶[33b Column Renamer]──▶[33 Python View: treemap]
 MAIN──▶[34 Python View: radar]
 CLUSTERED──▶[35a GroupBy]──▶[35b Column Renamer]──▶[35 Python View: chord]
 [36a CSV Reader waterfall_cleaning]──▶[36 Python View: waterfall]
 [36c CSV Reader waterfall_ce_aisi4140]──▶[36d Python View: waterfall]
 MAIN──▶[37a GroupBy]──▶[37b Normalizer]──▶[37 Parallel Coordinates Plot]

 SECTION I  MACHINE LEARNING
 MAIN──▶[38a Number To String]──▶[38 Partitioning]──┬─ port 1 TRAIN (1117)
                                                   └─ port 2 TEST  (265)
   TRAIN──▶[39a Decision Tree Learner]─(model)─▶[39b Decision Tree Predictor]◀── TEST
                                                [39b]──▶[39c Scorer]
   TRAIN──▶[40a Normalizer]─(model)─▶[40b Normalizer (Apply)]◀── TEST
           [40a]──▶[40c K Nearest Neighbor]◀──[40b]        [40c]──▶[40d Scorer]
   TRAIN──▶[41a Random Forest Learner (Regression)]─(model)─▶[41b RF Predictor (Regression)]◀── TEST
                                                            [41b]──▶[41c Numeric Scorer]

 EXTRA  [CSV Reader viz_expected_values]──▶[Table View]     (the answer key, kept on the canvas)
```

**Canvas layout tip.** Lay the sections out in horizontal bands, top to bottom in the order above, and draw one
coloured **workflow annotation** behind each band with its title ("A · Read, clean, enrich", "B · Five-number
summary", …). Graders look at the canvas before anything else.

---

## Part 3. Build it, section by section

Each step says **Add** (node name to search), **Connect** (from where), **Configure** (the essentials; full
settings in KNIME_GUIDE.md under the same node number) and **Run & check**.

### Section A · Read, clean, enrich (Nodes 1–6)

**Step A1 · Node 1 CSV Reader**
- **Add:** `CSV Reader`.
- **Configure:** *Read from* → **Relative to → Current workflow data area** → file `knime_input.csv`.
  Click **Autodetect format**. *Transformation* tab: set `strength_class` to **Number (integer)**,
  `is_imputed_ts` and `liquidus_is_default` to **Boolean** (String is fine too, see A2).
- **Run & check:** output table = **1389 rows**, 49 columns. Scroll right to see the `split` column.

**Step A2 · Node 2 Row Filter**
- **Add:** `Row Filter`. **Connect:** Node 1 → Node 2.
- **Configure:** column `is_imputed_ts`; condition **is false** (Boolean) or *equals* `False` (String);
  *Include* matching rows.
- **Run & check:** **1382 rows**.

**Step A3 · Nodes 3 and 3b Duplicate Row Filter** (sanity checks; nothing connects after Node 3)
- **Connect:** Node 2 → Node 3, and Node 2 → Node 3b.
- **Node 3:** duplicate columns = `canonical_grade` only, *Remove duplicate rows* → still **1382**.
- **Node 3b:** duplicate columns = all element columns (`Al` … `Zr`); *Keep duplicate rows*, *Add column
  showing duplicate status*. Then add a **GroupBy** after it: group by the status column, aggregation *Count*.

**Step A4 · Node 4 Rule Engine**
- **Connect:** Node 2 → Node 4 (*not* from Node 3).
- **Configure:** *Append column* `family_group`; paste the six rules from KNIME_GUIDE.md Node 4.
- **Run & check:** add a temporary **GroupBy** (group `family_group`, *Count*): Carbon & low-alloy **583**,
  Stainless **543**. Delete the temporary node afterwards (or keep it and label it "check").

**Step A5 · Nodes 5a → 5b → 5c → 5d Math Formula** (a chain of four)
- **Connect:** 4 → 5a → 5b → 5c → 5d.
- **Configure each:** *Append column*, type the name, type the expression from the table in KNIME_GUIDE.md.
  Tip: in the expression editor, double-click a column name in the left list to insert it as `$C$` without typos.
- **Run & check:** 5d's output has four new columns at the far right.

**Step A6 · Node 6 Color Manager** (the end of the trunk = `MAIN`)
- **Connect:** 5d → 6.
- **Configure:** column `family_group` → *Nominal* → click each value and set its colour (hex codes in
  KNIME_GUIDE.md Node 6).
- **Run & check:** 1382 rows. Every view you connect to Node 6 now uses these colours.

**Step A7 · Node 5e cross-check**
- **Connect:** 6 → 5e (Math Formula: `abs($carbon_equivalent$ - $carbon_equivalent_python$)`, append `ce_diff`)
  → **Statistics** (4.7) / **Statistics View** (5.x).
- **Run & check:** maximum of `ce_diff` = **0**. This proves your KNIME formula matches the Python pipeline.

✅ **Checkpoint A:** Ctrl + S. Annotate the band "A · Read, clean, enrich".

### Section B · Five-number summary and descriptive views (Nodes 7–11)

All five nodes connect **from Node 6**. Place them in a column to the right of Node 6.

| Step | Node | Configure (essentials) | Run & check |
|---|---|---|---|
| B1 | **7 GroupBy** | *Manual Aggregation*: `tensile_strength_mpa` five times → Minimum, Quantile 0.25, Median, Quantile 0.75, Maximum; plus Count, Mean, Standard deviation | 140 / 510 / 610 / 720 / 2450 |
| B2 | **8 Statistics View** | include numeric columns | mean TS 651.6 > median 610 (right skew) |
| B3 | **9 Box Plot** | category `family_group`, value `tensile_strength_mpa` | *Open view*: six coloured boxes |
| B4 | **10 Histogram** | `tensile_strength_mpa`, 40 bins | long tail above 1000 MPa |
| B5 | **11 Numeric Outliers** | column TS, IQR × 1.5, append flag | **75** flagged rows |

*How to add a quantile in GroupBy:* in *Manual Aggregation*, select the column on the left → **Add** → in the
*Aggregation* drop-down pick **Quantile** → a small *edit* button/parameter field appears → type `0.25`.

✅ **Checkpoint B:** compare Node 7 with the table in KNIME_GUIDE.md §2.

### Section C · Binning (Nodes 12–15)

1. **Node 12 Auto-Binner** (from Node 6): column TS, **5 bins, equal width** → add **GroupBy** on the new bin
   column with *Count* → **671 / 650 / 36 / 18 / 7**.
2. **Node 13 Auto-Binner** (from Node 6): 5 bins, **equal frequency** (or sample quantiles 0, .2, .4, .6, .8, 1)
   → GroupBy Count → **318 / 284 / 240 / 268 / 272**.
3. **Node 14 Numeric Binner** (from Node 6): column `C`, *Append new column* `carbon_band`. Click **Add** four
   times and type each interval and name from KNIME_GUIDE.md Node 14 (watch the bracket direction: *]* includes
   the edge).
4. **Node 14b Numeric Binner** (from Node 14): column `carbon_equivalent` → `ce_band`. The output of 14b is
   `BANDED`.
5. **Node 15 Bar Chart** (from 14b): category `carbon_band`, *Count*, stacked by `family_group`.

✅ **Checkpoint C:** the ">2.1 % C" bar is almost all orange (cast iron).

### Section D · Chi-square (Nodes 16–18), all from `BANDED` (Node 14b)

1. **Node 16 Crosstab:** row `family_group`, column `strength_class`. Execute → right-click → **second output
   table (statistics)** → χ² **548.73**, df **10**. Copy the node (Ctrl+C, Ctrl+V) twice and change the row
   variable to `product_form` (χ² 117.37, df 4) and `carbon_band` (χ² 315.85, df 6).
2. **Node 17 Python View:** paste `chi_square_residuals.py` (see Part 4). Title shows Cramér's V **0.45**.
3. **Node 18 Pivot** (group `family_group`, pivot `strength_class`, aggregation *Count*) → **Heatmap**.

✅ **Checkpoint D:** three Crosstab nodes, one residual heatmap, one native heatmap.

### Section E · Correlation and regression (Nodes 19–22)

1. **Node 19 Linear Correlation** and **19b Rank Correlation** (both from Node 6): include the 14 columns listed
   in KNIME_GUIDE.md; 19b set to **Spearman**. Open the view of each.
2. **Node 20 Row Filter** (from 6): `family` equals `carbon` → **196** rows.
3. **Node 20b Linear Regression Learner** (from 20): target TS, include only `C`. Right-click → view the
   coefficients: intercept **429.19**, slope **428.63**, R² **0.508**.
4. **Node 21a Regression Predictor:** two inputs. Drag the learner's **blue model port** to the predictor's
   model input, and Node 20's data port to the predictor's data input. It appends `Prediction
   (tensile_strength_mpa)`.
5. **Node 21b Sorter** (from 21a): sort by `C` ascending (so the line plot draws left to right).
6. **Node 21 Scatter Plot** (from 21b): x `C`, y TS. **Node 21c Line Plot** (from 21b): x `C`, y the
   prediction column. Both views go side by side in the dashboard.
7. **Node 22 Rule-based Row Filter** (from 6): rule from KNIME_GUIDE.md → **574** rows → **22b Linear
   Regression Learner** with `C, Mn, Si, Cr, Ni, Mo, V` → R² **0.326**.

✅ **Checkpoint E:** the slope of C in 20b and the seven coefficients in 22b match KNIME_GUIDE.md §5.

### Section F · PCA (Nodes 23–26)

1. **Node 23 Math Formula (Multi Column)** (from 6): select the 20 columns listed in KNIME_GUIDE.md, expression
   `ln($$CURRENT_COLUMN$$ + 1)`, **Replace** the selected columns.
2. **Node 24 Normalizer** (from 23): same 20 columns, **Z-score**.
3. **Node 25 PCA** (from 24): the 20 columns; *Dimensions*: 3; **keep the original columns** (untick *Remove
   original data columns*), so the next nodes still see `family_group`, `grade_id` and the 20 normalized columns.
   The output is `PCA`.
4. **Node 25b scree:** the eigenvalues come from the PCA node's spectral-decomposition output (if your PCA node
   has no such port, add a **PCA Compute** node on Node 24 and use its *spectral decomposition* output) →
   **Math Formula** `$eigenvalue$ / COL_SUM($eigenvalue$)` → **Bar Chart**.
   PC1 **15.0 %**, PC2 **11.8 %**.
5. **Node 26 Scatter Plot** (from 25): x `PCA dimension 0`, y `PCA dimension 1`, colour from Node 6.
   **26b Scatter Plot Matrix** (from 25): PC 0/1/2 + TS.

✅ **Checkpoint F:** pink stainless points stretch away along one axis, violet tool steels along the other.

### Section G · K-means and choosing k (Nodes 27–29)

1. **Node 27 k-Means** (from Node 25): include **only the 20 normalized element columns** (exclude the PCA
   dimensions and TS), 8 clusters, static seed ✓. It appends `Cluster`. The output is `CLUSTERED`: it holds the
   PCA dimensions *and* the cluster, so no Joiner is needed.
2. **Node 28 silhouette loop** (from Node 24), five nodes in a row:
   1. **Counting Loop Start:** *Number of loops* **11**.
   2. **Math Formula (Variable):** expression `$${Icurrentiteration}$$ + 2`, new variable `k`, *Convert to
      Int* ✓.
   3. **k-Means:** same columns and seed as Node 27. Open its **Flow Variables** tab → set *Number of clusters*
      (`nrClusters`) to the variable **k**. The red variable connection comes in from the Math Formula
      (Variable) node: connect the variable ports (red circles; right-click a node → *Show flow variable
      ports* if you cannot see them).
   4. **Silhouette Coefficient:** cluster column `Cluster`, the same 20 columns. Use its summary output (one
      row per cluster plus the overall value). If your version only gives per-row values, add **GroupBy** →
      *Mean* of the silhouette column.
   5. **Loop End:** *Add iteration column* ✓. After it, a **Math Formula** `$Iteration$ + 2` → column `k`,
      then a **Line Plot** (x `k`, y mean silhouette).
   - **Run:** execute the **Loop End** node; KNIME runs the whole loop 11 times (k = 2 … 12).
3. **Node 29a Color Manager** (from 27) on `Cluster` → **29 Scatter Plot** PC0 × PC1.
4. **Node 29b GroupBy** (from 27): group `Cluster`, *Median* of `C, Cr, Ni, Mo, V, W, Co, tensile_strength_mpa`,
   *Mode* of `family_label` → **29c Heatmap**. The element columns are normalized at this point, so read the
   heatmap as "above / below the average steel", not as wt%.

✅ **Checkpoint G:** write down the cluster sizes (Node 27 → GroupBy `Cluster` Count) and the k you chose from
the silhouette line, with one sentence of justification for the report.

### Section H · Circular and composition visuals (Nodes 30–37)

| Step | Build | Input |
|---|---|---|
| H1 | **30 Pie Chart**: category `family_group`, Count, *Donut* ✓ | Node 6 |
| H2 | **31 Sunburst Chart**: levels `family_group` → `family_label` | Node 6 |
| H3 | **32a GroupBy** (`family_label`, Median TS) → **32b Column Renamer** (`family_label`→`label`, median column→`value`) → **32 Python View** `circular_columns.py` | Node 6 |
| H4 | **33a GroupBy** (`family_label`; Count `grade_id`, Median TS) → **33b Column Renamer** (→ `label`, `size`, `color_value`) → **33 Python View** `treemap.py` | Node 6 |
| H5 | **34 Python View** `radar_family_groups.py` | Node 6 |
| H6 | **35a GroupBy** (groups `family_group`, `Cluster`; Count) → **35b Column Renamer** (→ `source`, `target`, `count`) → **35 Python View** `chord_migration.py` | Node 27 |
| H7 | **36a CSV Reader** `waterfall_cleaning.csv` (data area) → **36 Python View** `waterfall.py`; copy both nodes, point the reader to `waterfall_ce_aisi4140.csv` → second waterfall | none |
| H8 | **37a GroupBy** (`family_group`; Median of 8 columns) → **37b Normalizer** (min-max) → **37 Parallel Coordinates Plot** | Node 6 |

**GroupBy column names.** KNIME names aggregated columns like `Median(tensile_strength_mpa)` and
`Count*(grade_id)`. Look at the GroupBy output table to see the exact name, then rename it in the Column Renamer.
The Python scripts only look for `label`, `value`, `size`, `color_value`, `source`, `target`, `count`.

✅ **Checkpoint H:** circular columns peak at Spring steel **1790**; the cleaning waterfall ends at **1382**;
the CE waterfall ends at **0.781**.

### Section I · Machine learning (Nodes 38–41)

**Step I1 · split**
- **38a Number To String** (from 6): convert `strength_class`, so the classifiers treat it as a class label.
- **38 Partitioning** (from 38a): **Absolute**, **1117**, **Take from top**. Port 1 = TRAIN **1117**, port 2 =
  TEST **265**. (The file is sorted train-first: after Node 2, the first 1117 rows are exactly `split = train`.)
  A sturdier alternative is a **Rule-based Row Splitter** with `$split$ = "train" => TRUE`: same result, and it
  keeps working even if someone re-sorts the table.
- **Baseline:** GroupBy `strength_class` Count on the TEST port → 133 of 265 are class 2, so always guessing
  class 2 scores **0.502** accuracy. Every model must beat this.

**Step I2 · decision tree (39)**
- **39a Decision Tree Learner** ← TRAIN. Class `strength_class`; Gini; MDL pruning; min records 5. Exclude
  `tensile_strength_mpa`, `strength_class` (it is the target), `is_imputed_ts`, all IDs and names, `split`,
  `composition_group_id` and the `*_python` columns.
- **39b Decision Tree Predictor**: model ← 39a (blue port), data ← TEST.
- **39c Scorer**: first column `strength_class`, second `Prediction (strength_class)` → accuracy, Cohen's κ,
  confusion matrix. Right-click 39a → *View: Decision Tree View* to see the splits.

**Step I3 · k-NN (40)**
- **40a Normalizer** ← TRAIN (min-max, numeric features only) → **40b Normalizer (Apply)**: model ← 40a's
  blue port, data ← TEST.
- **40c K Nearest Neighbor**: top input ← 40a's data port (normalized TRAIN), bottom input ← 40b (normalized
  TEST). k = 5, *weight by distance* ✓. Try k = 3, 7, 9 by changing the setting and re-running.
- **40d Scorer** as in 39c.

**Step I4 · random forest regression (41)**
- **41a Random Forest Learner (Regression)** ← TRAIN, target `tensile_strength_mpa`, same exclusions as 39a
  (keep `strength_class` out of the features too, it is computed from TS), 100 models.
- **41b Random Forest Predictor (Regression)**: model ← 41a, data ← TEST → **41c Numeric Scorer**: R², MAE,
  RMSE.

✅ **Checkpoint I:** fill in this table for your report with the values *your* KNIME run shows:

| Model | Metric | Your value |
|---|---|---|
| Majority-class baseline | accuracy | 0.502 |
| Decision tree | accuracy / κ | |
| k-NN (best k = …) | accuracy / κ | |
| Random forest (regression) | R² / MAE (MPa) / RMSE (MPa) | |

---

## Part 4. Python View nodes (Nodes 17, 32, 33, 34, 35, 36)

The six scripts are in `docs/knime_python_views/`. They use only pandas, numpy, scipy and matplotlib, which
the bundled environment has.

1. **Add** `Python View` and place it after the node named in its step.
2. **Input port:** if the node shows no input triangle, click the **+ / ⋯** handle on its left edge (5.x) or
   right-click → *Add Input Port → Input Table* (4.7). Connect the input.
3. **Open the script:** open the `.py` file in Notepad or VS Code → **Ctrl + A**, **Ctrl + C**.
4. **Configure** the Python View (double-click): the script editor opens with a template. Click inside the
   editor → **Ctrl + A** → **Delete** → **Ctrl + V**.
5. **Test inside the editor:** click **Run all** (4.7: *Execute script*). The chart preview appears in the
   editor's output area. Errors appear in the console underneath.
6. **OK / Apply and Close** → select the node → **F7** → right-click → **Open view**.
7. **Save as image:** in the node settings tick the image output (if offered) → connect **Image Writer (Port)**
   → `reports/knime_screenshots/<name>.png`.

| Script | Input it expects | Comes from |
|---|---|---|
| `chi_square_residuals.py` | `family_group`, `strength_class` (edit `ROW`, `COL` at the top for other pairs) | Node 14b |
| `circular_columns.py` | `label`, `value` | Node 32b |
| `treemap.py` | `label`, `size`, `color_value` | Node 33b |
| `radar_family_groups.py` | `family_group` + element columns `C … Cu` | Node 6 |
| `chord_migration.py` | `source`, `target`, `count` | Node 35b |
| `waterfall.py` | `step`, `value`, `kind` | Node 36a / 36c |

---

## Part 5. Dashboard, export, submit

### 5.1 Build the dashboard component (Section J)

1. Hold **Ctrl** and click the view nodes listed in KNIME_GUIDE.md §10 (box plot, histogram, bar chart, residual
   heatmap, regression scatter, PCA scatter, cluster scatter, donut, sunburst, circular columns, radar, chord,
   waterfall).
2. Right-click one of them → **Create component…** → name `SteelScope Dashboard`. KNIME moves the nodes inside
   and creates one input port per incoming connection automatically.
3. **Ctrl + double-click** the component to open it → toolbar **Layout Editor** (5.x: *Component → Layout*).
   Drag each view tile into the rows given in KNIME_GUIDE.md §10.
4. **Linking:** in each native view's settings tick *Publish selection* and *Subscribe to selection*. Add a
   **Single Selection Widget** (or **Value Filter Widget**) on `family_group` inside the component and connect a
   **Row Filter**/**Interactive Range Slider Filter** if you want one control to filter every view.
5. Go back to the main workflow (tab at the top), execute the component (**F7**), right-click → **Open view**.
   That is your dashboard; maximise the window and screenshot it (**Win + Shift + S**).

### 5.2 Export

1. **Canvas picture:** zoom to fit (*Ctrl + Shift + F* in 4.7, *Fit to screen* button in 5.x) → screenshot,
   or 4.7: *File → Export → Export Workflow as SVG*.
2. **Workflow file:** Explorer/Space → right-click the workflow → **Export…** → tick *Reset workflow before
   export* → `SteelScope_Visual_Analytics.knwf`. The `data` folder from Part 1.3 travels inside it.
3. **Re-import test:** *File → Import KNIME Workflow…* the `.knwf` into a new folder → **Shift + F7** → every node
   must turn green with no path errors. Do this before you submit.

### 5.3 What to submit / show in the viva

- the `.knwf` file;
- screenshots: the full canvas, the dashboard, each Python View chart, the Scorer confusion matrices;
- the filled Checkpoint I table and the final checklist from KNIME_GUIDE.md §12.

---

## Part 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| CSV Reader: *file does not exist* | path still points at the old location | *Relative to → Current workflow data area* and only the file name; the file must be in the workflow's `data` folder |
| Row Filter keeps 0 or 1389 rows | `is_imputed_ts` was read as String | filter on the text `False`, or set the column type to Boolean in the CSV Reader *Transformation* tab |
| Rule Engine: everything becomes "Other" | quotes or case differ | values are lower-case (`"carbon"`, `"stainless"`); copy the rules from the guide exactly |
| GroupBy has no *Quantile* option | very old KNIME version | update KNIME, or read the quartiles from the **Statistics View** (Node 8) |
| Python View: `ModuleNotFoundError` | wrong Python environment | Preferences → KNIME → Python → *Bundled environment* |
| Python View: `KeyError: 'label'` | GroupBy column not renamed | add/fix the Column Renamer before the Python View |
| Python View: `KeyError: 'family_group'` | input not from Node 6 / 14b | reconnect from the node in the Part 4 table |
| Decision tree / Scorer greyed out | `strength_class` is still a number | add **Number To String** (38a) before Partitioning |
| Loop runs once only | Loop End not executed, or k not wired | execute **Loop End**, not the k-Means; check the k-Means *Flow Variables* tab |
| Views show no colours | view connected upstream of Node 6 | connect views after the Color Manager |
| Exported workflow fails on another PC | absolute file paths | use the workflow data area (Part 1.3) |
