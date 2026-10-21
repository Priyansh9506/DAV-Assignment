# KNIME Python View — Treemap (squarified layout, no extra packages needed).
# Input table: columns "label" (string), "size" (number, e.g. count of grades) and "color_value"
# (number, e.g. median tensile strength). GroupBy on family_label: Count(grade_id), Median(tensile_strength_mpa).
import knime.scripting.io as knio
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

SURFACE, INK = "#0e0b1e", "#ffffff"
SEQ = LinearSegmentedColormap.from_list("seq", ["#5102a3", "#8a09a5", "#b83289", "#da5b69", "#f48849", "#febd2a", "#f0f921"])


def squarify(sizes, x, y, w, h):
    """Bruls et al. squarified treemap: returns a list of (x, y, w, h) for sizes sorted descending."""
    rects, sizes = [], [s * w * h / sum(sizes) for s in sizes]

    def worst(row, side):
        s = sum(row)
        return max(max(side ** 2 * r / s ** 2, s ** 2 / (side ** 2 * r)) for r in row)

    while sizes:
        side = min(w, h)
        row = [sizes.pop(0)]
        while sizes and worst(row + [sizes[0]], side) <= worst(row, side):
            row.append(sizes.pop(0))
        s = sum(row)
        if w >= h:                                  # lay the row along the left edge
            cw, cy = s / h, y
            for r in row:
                rects.append((x, cy, cw, r / cw))
                cy += r / cw
            x, w = x + cw, w - cw
        else:                                       # lay the row along the bottom edge
            ch, cx = s / w, x
            for r in row:
                rects.append((cx, y, r / ch, ch))
                cx += r / ch
            y, h = y + ch, h - ch
    return rects


d = knio.input_tables[0].to_pandas().sort_values("size", ascending=False).reset_index(drop=True)
norm = Normalize(d["color_value"].min(), min(d["color_value"].max(), 1100))
fig, ax = plt.subplots(figsize=(13, 8), facecolor=SURFACE)
for (rx, ry, rw, rh), (_, r) in zip(squarify(d["size"].tolist(), 0, 0, 100, 60), d.iterrows()):
    c = SEQ(norm(r["color_value"]))
    ax.add_patch(plt.Rectangle((rx, ry), rw, rh, facecolor=c, edgecolor=SURFACE, lw=2))
    if rw > 6 and rh > 4:
        ax.text(rx + 0.5, ry + rh - 0.5, f"{r['label']}\n{int(r['size'])} · {r['color_value']:.0f}", va="top",
                fontsize=8, color=SURFACE if norm(r["color_value"]) > 0.6 else INK)
ax.set_xlim(0, 100)
ax.set_ylim(0, 60)
ax.axis("off")
ax.set_title("Treemap: area = size, colour = colour value", color=INK, loc="left", fontweight="bold")
knio.output_view = knio.view_matplotlib(fig)
