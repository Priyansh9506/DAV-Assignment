# KNIME Python View — Circular migration (chord) plot.
# Input table: one row per flow with columns "source", "target", "count"
# (e.g. GroupBy on family_group + Cluster with Count; then Column Rename to source/target/count).
import knime.scripting.io as knio
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import PathPatch, Wedge
from matplotlib.path import Path

SURFACE, INK, INK_2 = "#1a1a19", "#ffffff", "#c3c2b7"
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]

flows = knio.input_tables[0].to_pandas()
flows["count"] = flows["count"].astype(float)
sources = list(flows.groupby("source")["count"].sum().sort_values(ascending=False).index)
targets = list(flows.groupby("target")["count"].sum().sort_values(ascending=False).index)
color = {s: SERIES[i % len(SERIES)] for i, s in enumerate(sources)}


def arc(a0, a1, r=1.0, n=24):
    t = np.radians(np.linspace(a0, a1, n))
    return np.column_stack([r * np.cos(t), r * np.sin(t)])


def bezier(p0, p1, p2, p3, n=30):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


gap, split = 2.0, 14.0
total = flows["count"].sum()
deg = (180 - split - gap * (max(len(sources), len(targets)) - 1)) / total
s_tot, t_tot = flows.groupby("source")["count"].sum(), flows.groupby("target")["count"].sum()
s_arc, t_arc, a = {}, {}, 90 + split / 2
for s in sources:                                   # sources on the left half
    s_arc[s] = [a, a + s_tot[s] * deg]
    a += s_tot[s] * deg + gap
a = 90 - split / 2
for t in targets:                                   # targets on the right half
    t_arc[t] = [a - t_tot[t] * deg, a]
    a -= t_tot[t] * deg + gap
s_cur = {s: v[0] for s, v in s_arc.items()}
t_cur = {t: v[1] for t, v in t_arc.items()}

fig, ax = plt.subplots(figsize=(11, 10), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
for _, f in flows.assign(_s=flows["source"].map(sources.index), _t=flows["target"].map(targets.index)).sort_values(["_s", "_t"]).iterrows():
    span = f["count"] * deg
    src = arc(s_cur[f["source"]], s_cur[f["source"]] + span)
    s_cur[f["source"]] += span
    tgt = arc(t_cur[f["target"]], t_cur[f["target"]] - span)
    t_cur[f["target"]] -= span
    poly = np.vstack([src, bezier(src[-1], src[-1] * 0.25, tgt[0] * 0.25, tgt[0]), tgt,
                      bezier(tgt[-1], tgt[-1] * 0.25, src[0] * 0.25, src[0])])
    ax.add_patch(PathPatch(Path(poly), facecolor=color[f["source"]], alpha=0.55, edgecolor=color[f["source"]], lw=0.4))
for node, (a0, a1) in list(s_arc.items()) + list(t_arc.items()):
    ax.add_patch(Wedge((0, 0), 1.09, a0, a1, width=0.07, color=color.get(node, INK_2)))
    mid = np.radians((a0 + a1) / 2)
    d = np.degrees(mid) % 360
    left = 90 < d < 270
    ax.text(1.14 * np.cos(mid), 1.14 * np.sin(mid), node, rotation=d + 180 if left else d, rotation_mode="anchor",
            ha="right" if left else "left", va="center", fontsize=8.5, color=INK)
ax.set_xlim(-1.8, 1.8)
ax.set_ylim(-1.6, 1.5)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Circular migration plot (left = from, right = to; ribbon width = number of grades)", color=INK)
knio.output_view = knio.view_matplotlib(fig)
