# KNIME Python View — Radar chart of median composition per family group.
# Input table: the cleaned grades with a "family_group" column (from the Rule Engine node).
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np

SURFACE, INK, INK_2, GRID = "#1a1a19", "#ffffff", "#c3c2b7", "#2c2c2a"
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"]
ORDER = ["Carbon & low-alloy", "Stainless", "Cast iron", "Tool & high-speed", "Weld metal", "Other"]
ELEMENTS = ["C", "Mn", "Si", "Cr", "Ni", "Mo", "V", "W", "Co", "Cu"]

df = knio.input_tables[0].to_pandas()
med = df.groupby("family_group")[ELEMENTS].median().reindex([g for g in ORDER if g in set(df["family_group"])])
lg = np.log1p(med)
scaled = (lg - lg.min()) / (lg.max() - lg.min()).replace(0, 1)      # 0-1 per element across groups

ang = np.linspace(0, 2 * np.pi, len(ELEMENTS), endpoint=False)
ang_closed = np.concatenate([ang, ang[:1]])
fig, axes = plt.subplots(2, 3, figsize=(13, 9), subplot_kw={"polar": True}, facecolor=SURFACE)
for ax, (grp, row), color in zip(axes.ravel(), scaled.iterrows(), SERIES):
    vals = np.concatenate([row.values, row.values[:1]])
    ax.set_facecolor(SURFACE)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.plot(ang_closed, vals, color=color, lw=2)
    ax.fill(ang_closed, vals, color=color, alpha=0.3)
    ax.set_xticks(ang, ELEMENTS, color=INK_2)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0], ["", "", "", ""])
    ax.set_ylim(0, 1)
    ax.grid(color=GRID)
    ax.spines["polar"].set_color(GRID)
    ax.set_title(grp, color=INK, pad=14, fontweight="bold")
fig.suptitle("Radar: median composition fingerprint of each family group (log-scaled, 0-1 across groups)",
             color=INK, x=0.02, ha="left", fontweight="bold")
fig.tight_layout()
knio.output_view = knio.view_matplotlib(fig)
