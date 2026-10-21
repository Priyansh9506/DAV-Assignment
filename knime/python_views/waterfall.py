# KNIME Python View — Waterfall chart.
# Input table: columns "step" (string), "value" (number), "kind" ("total" or "delta"), in display order.
# Example: Table Creator with the cleaning steps, or tableau/data/viz/waterfall_ce_aisi4140.csv via CSV Reader.
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np

SURFACE, INK, INK_2, GRID = "#0e0b1e", "#ffffff", "#d4ceef", "#251f45"
TOTAL, UP, DOWN = "#0d9de5", "#5bab0f", "#ff0d89"

wf = knio.input_tables[0].to_pandas().reset_index(drop=True)
run, starts, ends = 0.0, [], []
for _, r in wf.iterrows():
    if r["kind"] == "total":
        run = float(r["value"])
        starts.append(0.0)
    else:
        starts.append(run)
        run += float(r["value"])
    ends.append(run)

fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
for i, r in wf.iterrows():
    lo, hi = sorted([starts[i], ends[i]])
    c = TOTAL if r["kind"] == "total" else (UP if r["value"] >= 0 else DOWN)
    ax.bar(i, hi - lo, bottom=lo, width=0.62, color=c, edgecolor=SURFACE)
    ax.text(i, hi, f"{r['value']:+,.3g}" if r["kind"] != "total" else f"{r['value']:,.4g}", ha="center", va="bottom",
            color=INK, fontsize=9)
    if i < len(wf) - 1:
        ax.plot([i + 0.31, i + 0.69], [ends[i]] * 2, color=INK_2, lw=1)
ax.set_xticks(np.arange(len(wf)), wf["step"], rotation=20, ha="right", color=INK_2)
ax.grid(axis="y", color=GRID)
ax.set_title("Waterfall: running total built step by step (sky = total, lime = increase, pink = decrease)", color=INK)
fig.tight_layout()
knio.output_view = knio.view_matplotlib(fig)
