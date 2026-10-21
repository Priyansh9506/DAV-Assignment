# KNIME Python View — Chi-square test + standardized-residual heatmap.
# Input table: the cleaned grades. Set ROW and COL to any two categorical columns
# (e.g. "family_group", "carbon_band", "product_form" x "strength_class").
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

ROW, COL = "family_group", "strength_class"
CLASS_NAMES = {0: "0 · Low (<300 MPa)", 1: "1 · Medium (300-600)", 2: "2 · High (>600)"}
SURFACE, INK, INK_2 = "#0e0b1e", "#ffffff", "#d4ceef"
DIV = LinearSegmentedColormap.from_list("div", ["#0d9de5", "#2b2547", "#ff0d89"])

df = knio.input_tables[0].to_pandas()
obs = pd.crosstab(df[ROW], df[COL])
chi2, p, dof, exp = stats.chi2_contingency(obs.values, correction=False)
res = (obs.values - exp) / np.sqrt(exp)
v = np.sqrt(chi2 / (obs.values.sum() * (min(obs.shape) - 1)))


def label(c):
    try:
        return CLASS_NAMES.get(int(float(c)), str(c)) if COL == "strength_class" else str(c)
    except ValueError:
        return str(c)


fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
lim = max(4, np.abs(res).max())
im = ax.imshow(res, cmap=DIV, vmin=-lim, vmax=lim, aspect="auto")
for i in range(obs.shape[0]):
    for j in range(obs.shape[1]):
        ax.text(j, i, f"{obs.iat[i, j]}\n({res[i, j]:+.1f})", ha="center", va="center", color=INK, fontsize=9)
ax.set_xticks(range(obs.shape[1]), [label(c) for c in obs.columns], color=INK_2)
ax.set_yticks(range(obs.shape[0]), [str(r) for r in obs.index], color=INK_2)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
cb.set_label("standardized residual (pink = more grades than independence predicts)", color=INK_2, fontsize=8)
cb.ax.tick_params(colors=INK_2)
ax.set_title(f"{ROW} x {COL}: chi2 = {chi2:,.1f}, df = {dof}, p = {p:.1e}, Cramer's V = {v:.2f}\n"
             "cell = count (standardized residual)", color=INK, fontsize=10)
fig.tight_layout()
knio.output_view = knio.view_matplotlib(fig)
