# Power BI

Everything for the Power BI part of the project: a six-page interactive report on the cleaned steel data.

```
powerbi/
├── POWERBI_GUIDE.md          ← step-by-step build: load, model, measures, six pages, checklist
├── build_powerbi_data.py     ← writes the star-schema CSVs below from data/processed/steels_clean.csv
├── data/
│   ├── grades.csv            fact table, one row per grade (1,389)
│   ├── composition.csv       one row per (grade, element present) with wt% (13,376)
│   ├── families.csv          family → family group, sort order, colour (17)
│   └── elements.csv          element symbol → name, rare-trace flag (30)
├── queries.pq                ← Power Query (M) for the four tables, driven by a DataFolder parameter
├── measures.dax              ← DAX measures with the value each should show
└── SteelScope.theme.json     ← report theme with the project's family-group colours
```

## Report pages

| Page | Question | Visuals |
|---|---|---|
| Overview | What is in the data and how strong is it? | KPI cards, strength histogram, family treemap, median-with-quartiles chart |
| Families and strength classes | Does family decide strength? | 100 % stacked bars, class matrix heatmap, decomposition tree |
| Carbon is the dial | What makes a plain steel stronger? | scatter with trend line, weldability bands |
| Chemistry map | Which steels are chemically alike? | PCA scatter, element heatmap matrix |
| Grade inspector | What is this one grade? | drillthrough page with cards and composition bars |
| Target finder | Which grades meet my requirement? | range slicers, matches per family, candidate table |

## Build it

Follow [POWERBI_GUIDE.md](POWERBI_GUIDE.md) and save the report as `powerbi/SteelScope.pbix`. The `.pbix` is
created in Power BI Desktop (it is a binary file and cannot be generated from code), so this folder ships
everything that goes into it: data, model, measures, theme and the page-by-page layout.

Regenerate the data after the cleaned dataset changes:

```bash
python powerbi/build_powerbi_data.py
```
