# SteelScope app

A small web application on the cleaned steel dataset (the brief's *Application Development* part). It answers the
three questions the project asks, interactively:

| Page | Question it answers | What you see |
|---|---|---|
| **Explorer** (`/`) | What is in the data, and how strong is it? | Filters (family group, product form, strength range, name search), stat cards, stacked strength histogram, family donut, box plots per group, sortable grade table |
| **Grade inspector** (`/grades/[id]`) | What is this grade, and where does it stand? | Key numbers, percentile bars within its family and among all grades, composition radar against its group median, composition bars, carbon-equivalent waterfall with weldability band, five closest grades |
| **Substitute finder** (`/substitutes/[id]`) | Which grades have the most similar chemistry? | Ten nearest grades by distance in log + z-score composition space, how close they are compared with all grade pairs, strength difference, and the PCA chemistry map with the selection ringed |
| **Target designer** (`/designer`) | For a required strength and melting range, which families deliver it? | Strength and liquidus windows, product form, a switch to ignore the 1460 °C placeholder liquidus, strength × liquidus scatter with the target box, matches per family, candidate table |
| **About the data** (`/about`) | Where do the numbers come from? | Cleaning log, family groups, methods (CE, PCA loadings, distance, percentiles), known limits |

There is no prediction in the app: the project keeps all machine learning in KNIME. Every number shown is
computed from the data files below, in the data script or in the page.

## Run it

```bash
cd app
npm install
npm run dev
```

Open http://localhost:3000. Press **Ctrl K** anywhere to jump to a grade.

```bash
npm run build && npm start   # production build: 2,787 prerendered pages
npx vitest run               # unit tests for the statistics helpers
```

## Data

The app reads files written by `scripts/build_data.py` from `../data/processed/steels_clean.csv` (the output of
`notebooks/01_cleaning.ipynb`). Rerun it whenever the cleaned data changes:

```bash
python scripts/build_data.py
```

| File | Contents | Used by |
|---|---|---|
| `src/data/grades.json` | One record per grade: names, family, group, form, strength, class, liquidus, composition, CE, PCA coordinates, ten nearest neighbours | Server only (pages send the browser just the fields they need) |
| `src/data/meta.json` | Element lists, PCA summary and loadings, strength classes, cleaning log | Server only |
| `public/data/search.json` | `[id, name, group]` per grade | Grade search, fetched once |
| `public/data/points.json` | `[id, PC1, PC2]` per grade | Chemistry map, fetched once |

The PCA and the neighbour search use the same composition space as notebook 03 (20 features, `log1p`, z-score);
the script reproduces the notebook's explained variance (PC1 15.0 %, PC2 11.8 %).

## Stack and structure

Next.js 16 (App Router, Cache Components), React 19, TypeScript, Tailwind CSS 4, shadcn/ui (Base UI primitives),
Recharts, Lucide icons, Vitest.

```
app/
├── scripts/build_data.py        ← data preparation (Python, pandas, scikit-learn)
├── public/data/                 ← search index and map points for the browser
└── src/
    ├── app/                     ← pages: explorer, grades/[id], substitutes/[id], designer, about
    ├── components/              ← page sections and charts (components/ui = shadcn)
    ├── hooks/use-theme.ts       ← light / dark toggle
    ├── data/                    ← grades.json, meta.json (server only)
    └── lib/                     ← data access (server), statistics helpers, steel domain rules, types
```

Family-group colours come from a palette checked for colour-blind separation in light and dark mode; scatter plots
also use a shape per group, and every chart has a legend, labels or a table beside it.
