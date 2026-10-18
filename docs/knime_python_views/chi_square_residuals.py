# KNIME Python View — Chi-square test + standardized-residual heatmap.
# Input table: the cleaned grades. Set ROW and COL to any two categorical columns.
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

ROW, COL = "family_group", "strength_class"
SURFACE, INK, INK_2 = "#0e0b1e", "#ffffff", "#d4ceef"
DIV = LinearSegmentedColormap.from_list("div", ["#0d9de5", "#2b2547", "#ff0d89"])

df = knio.input_tables[0].to_pandas()
obs = pd.crosstab(df[ROW], df[COL])
chi2, p, dof, exp = stats.chi2_contingency(obs.values, correction=False)
res = (obs.values - exp) / np.sqrt(exp)
v = np.sqrt(chi2 / (obs.values.sum() * (min(obs.shape) - 1)))

fig, ax = plt.subplots(figsize=(8, 6), facecolor=SURFACE)
lim = max(4, np.abs(res).max())
ax.imshow(res, cmap=DIV, vmin=-lim, vmax=lim, aspect="auto")
for i in range(obs.shape[0]):
    for j in range(obs.shape[1]):
        ax.text(j, i, f"{obs.iat[i, j]}\n({res[i, j]:+.1f})", ha="center", va="center", color=INK, fontsize=9)
ax.set_xticks(range(obs.shape[1]), [str(c) for c in obs.columns], color=INK_2)
ax.set_yticks(range(obs.shape[0]), [str(r) for r in obs.index], color=INK_2)
ax.set_title(f"{ROW} x {COL}: chi2 = {chi2:,.1f}, df = {dof}, p = {p:.2e}, Cramer's V = {v:.2f}", color=INK, fontsize=10)
fig.tight_layout()
knio.output_view = knio.view_matplotlib(fig)
