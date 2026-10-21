# SteelScope visual-analytics guide (index)

| Guide | What you build | Start here |
|---|---|---|
| [Tableau guide](TABLEAU_GUIDE.md) | 18 sheets (box plots, bins, chi-square heatmap, trend lines, PCA, chord, donut, treemap, radial columns, radar, waterfall), 3 interactive dashboards, a Story, publishing to Tableau Public | §0 Before you start |
| [KNIME guide](KNIME_GUIDE.md) | 41-node workflow: cleaning, five-number summary, binning, crosstab chi-square, correlation, linear regression, PCA, k-means + silhouette loop, decision tree, k-NN and random forest, native views (box, histogram, bar, donut, sunburst, scatter, heatmap, parallel coordinates), Python View radar / chord / waterfall / circular columns / treemap / residual heatmap, composite dashboard, `.knwf` export | §0 Setup |
| [KNIME build sheet](KNIME_WORKFLOW_STEP_BY_STEP.md) | The same workflow as a click-by-click build: KNIME basics, a wiring map of every node, build order with a checkpoint per section, pasting the Python View scripts, dashboard, export, troubleshooting | Part 1 |
| [Python notebook](../notebooks/03_visual_analytics.ipynb) | 27 visuals in matplotlib + seaborn, with the statistics and takeaways (no machine learning: that is done in KNIME) | §1 |
| [Web app](../app/README.md) | Next.js + shadcn/ui application: explorer, grade inspector, substitute finder, target designer | Run it |
| [Claude Code prompt](CLAUDE_CODE_PROMPT.md) | A reusable prompt that plans, then builds, a project like this for any dataset | top |

Files used by the guides: `exports/tableau/*.csv`, `exports/tableau/viz/*.csv` (ready-made shapes for chord,
radar, radial bars and waterfalls), `exports/knime/knime_input.csv` and `exports/knime/viz_expected_values.csv`
(every statistic KNIME should reproduce). To regenerate them, run notebooks 01 → 03 in order
(*Kernel → Restart & Run All*); the exports are written by the appendix of notebook 03.
