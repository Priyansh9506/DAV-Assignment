# KNIME Python View — Circular column (radial bar) chart.
# Input table: columns "label" (string) and "value" (number), e.g. GroupBy family_label -> Median(tensile_strength_mpa)
# followed by Column Rename to label / value.
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np

SURFACE, INK, INK_2, GRID = "#0e0b1e", "#ffffff", "#d4ceef", "#251f45"

d = knio.input_tables[0].to_pandas().dropna(subset=["value"]).sort_values("value", ascending=False)
n = len(d)
theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
width = 2 * np.pi / n * 0.85
inner = d["value"].max() * 0.45                       # hollow centre so short bars stay visible

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"polar": True}, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
colors = plt.get_cmap("plasma")(0.14 + 0.86 * d["value"].to_numpy() / d["value"].max())   # longer = hotter
ax.bar(theta, d["value"], width=width, bottom=inner, color=colors, edgecolor=SURFACE, alpha=0.95)
for t, (lab, v) in zip(theta, zip(d["label"], d["value"])):
    rot = (90 - np.degrees(t)) % 360                 # on-screen angle of this bar (clockwise from the top)
    flip = 90 < rot < 270                            # left half: turn the text so it is not upside down
    ax.text(t, inner + v + d["value"].max() * 0.04, f"{lab}  {v:,.0f}", rotation=rot + 180 if flip else rot,
            rotation_mode="anchor", ha="right" if flip else "left", va="center", fontsize=8, color=INK_2)
ax.set_ylim(0, inner + d["value"].max() * 1.6)
ax.set_xticks([])
ax.set_yticks([])
ax.spines["polar"].set_visible(False)
ax.grid(color=GRID)
ax.set_title("Circular column chart (bar length = value)", color=INK)
knio.output_view = knio.view_matplotlib(fig)
