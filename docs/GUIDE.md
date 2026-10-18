# SteelScope visual-analytics guide (index)

| Guide | What you build | Start here |
|---|---|---|
| [Tableau guide](TABLEAU_GUIDE.md) | 20 sheets (box plots, bins, chi-square heatmap, trend lines, PCA, clustering, chord, donut, treemap, radial columns, radar, waterfall), 3 interactive dashboards, a Story, publishing to Tableau Public | §0 Before you start |
| [KNIME guide](KNIME_GUIDE.md) | 40-node workflow: cleaning, five-number summary, binning, crosstab chi-square, correlation, linear regression, PCA, k-means + silhouette loop, native views (box, histogram, bar, donut, sunburst, scatter, heatmap, parallel coordinates), Python View radar / chord / waterfall / circular columns / treemap / residual heatmap, composite dashboard, `.knwf` export | §0 Setup |
| [Python notebook](../notebooks/04_visual_analytics.ipynb) | The same 34 visuals in matplotlib + seaborn, with the statistics and takeaways | §1 |
| [Claude Code prompt](CLAUDE_CODE_PROMPT.md) | A reusable prompt that plans, then builds, a project like this for any dataset | top |

Files used by the guides: `exports/tableau/*.csv`, `exports/tableau/viz/*.csv` (ready-made shapes for chord,
radar, radial bars and waterfalls), `exports/knime/knime_input.csv` and `exports/knime/viz_expected_values.csv`
(every number KNIME should reproduce). Regenerate them with `python -m src.analysis.exports` and
`python -m src.analysis.viz_exports`.
