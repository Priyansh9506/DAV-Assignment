# Power BI

Everything for the Power BI part of the project: a six-page interactive report on the cleaned steel data.

```
powerbi/
├── SteelScope.pbip           ← open this in Power BI Desktop (Power BI Project)
├── SteelScope.SemanticModel/ ← model in TMDL: 4 tables, 3 relationships, measures, DataFolder parameter
├── SteelScope.Report/        ← report in PBIR: six pages, every visual placed and formatted
├── build_pbip.py             ← writes the two folders above from the files below
├── build_powerbi_data.py     ← writes the star-schema CSVs below from data/processed/steels_clean.csv
├── data/
│   ├── grades.csv            fact table, one row per grade (1,389)
│   ├── composition.csv       one row per (grade, element present) with wt% (13,376)
│   ├── families.csv          family → family group, sort order, colour (17)
│   └── elements.csv          element symbol → name, rare-trace flag (30)
├── queries.pq                ← Power Query (M) for the four tables, driven by a DataFolder parameter
├── measures.dax              ← DAX measures with the value each should show
├── SteelScope.theme.json     ← report theme with the project's family-group colours
└── POWERBI_GUIDE.md          ← how the report is built, page by page, with a checklist of expected values
```

## Open the report

1. Open `powerbi/SteelScope.pbip` in Power BI Desktop (tested with 2.159, October 2026; the report uses the
   March 2026 PBIR schemas, so older Desktop builds may refuse it).
2. Press **Refresh now** in the yellow bar (or *Home → Refresh*). A project stores no data, so this loads the CSVs.
3. To share a single file: *File → Save as* → `SteelScope.pbix`.

The `DataFolder` parameter holds the absolute path of `powerbi/data/` on the machine that ran `build_pbip.py`.
After cloning or moving the project, run it again (or change the parameter in *Transform data → Manage parameters*):

```bash
python powerbi/build_pbip.py
```

`build_pbip.py` reads `queries.pq`, `measures.dax` and the theme, so edit those and re-run it rather than editing
the generated folders. Changes made and saved in Desktop are written back to the same folders.

## Report pages

| Page | Question | Visuals |
|---|---|---|
| Overview | What is in the data and how strong is it? | slicers, KPI cards, strength histogram, family treemap, quartiles by group |
| Families & classes | Does family decide strength? | 100 % stacked bars, class matrix heatmap, decomposition tree |
| Carbon is the dial | What makes a plain steel stronger? | carbon scatter with trend line, pooled scatter, weldability bands |
| Chemistry map | Which steels are chemically alike? | PCA scatter, element heatmap matrix |
| Grade inspector | What is this one grade? | drillthrough page: cards, composition bars and table |
| Target finder | Which grades meet my requirement? | range slicers, matches per family, candidate table |

Regenerate the data after the cleaned dataset changes, then rebuild the report:

```bash
python powerbi/build_powerbi_data.py
python powerbi/build_pbip.py
```
