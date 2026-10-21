# Tableau

Everything for the Tableau part of the project.

```
tableau/
├── TABLEAU_GUIDE.md      ← step-by-step guide: 18 sheets, 3 dashboards and a Story
├── workbooks/            ← the team's workbooks
│   ├── DAV_D1.twb
│   ├── DAV_D2.twb
│   └── DAV_D3.twb
└── data/                 ← CSVs written by notebook 03 (never edit by hand)
    ├── steels_wide.csv       one row per grade, every column
    ├── steels_long.csv       one row per (grade, element)
    ├── family_summary.csv    medians and percentiles per family
    └── viz/                  statistics tables and ready-made chart shapes (chord, radar, radial bars, waterfall)
```

## The workbooks

| Workbook | Sheets | Data it reads |
|---|---|---|
| `DAV_D1.twb` | Sheet 1, Sheet 2, Sheet 3, Sheet 4, Sheet 4 (2), Sheet 6 + Dashboard 1 | `data/steels_wide.csv` |
| `DAV_D2.twb` | Attribute vs Cramér's V, PCA analysis, Regression line, Term vs Beta, Treemap + Dashboard 1 | `data/steels_wide.csv`, `data/viz/chi_square_cells.csv`, `chi_square_tests.csv`, `pca_scores.csv`, `regression_coefficients.csv` |
| `DAV_D3.twb` | Box plot MP, Box plot TS, MP vs Al, Sheet 4, Sheet 6, TS in Alloys, TS vs MP + Dashboard 1 | `Synthetic_Alloys_Tableau.csv` (not in this repository) |

## Opening a workbook on another computer

The `.twb` files store the absolute path of the computer they were saved on. When Tableau reports a missing file,
click **Locate** (or *Data → Edit Connection*) and pick the file with the same name in `tableau/data/` or
`tableau/data/viz/`, then save. To share a workbook that opens anywhere, use *File → Export Packaged Workbook*
(`.twbx`), which bundles the data.

`DAV_D3.twb` reads `Synthetic_Alloys_Tableau.csv` from its author's Downloads folder. That file is not in the
repository; add it to `tableau/data/` or export D3 as a `.twbx` before anyone else opens it.

## Regenerating the data

The CSVs in `data/` are written by the appendix of `notebooks/03_visual_analytics.ipynb`. Rerun notebooks 01 → 03
if the cleaned data changes; never edit the CSVs by hand.
