"""Helper CSVs that let Tableau draw the notebook-04 visuals, plus the expected values quoted in the KNIME guide.

    python -m src.analysis.viz_exports

exports/tableau/viz/   one CSV per chart; circular charts come as ready x/y polygons (layer, shape_id, point_order)
exports/knime/viz_expected_values.csv   numbers to check KNIME's outputs against
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import visual_stats as V
from . import viz_suite as VS
from .cleaning import load_clean_grades, load_pipeline_meta
from .constants import CLEAN_LISTINGS_CSV, DATA_RAW, EXPORTS_KNIME, EXPORTS_TABLEAU

logger = logging.getLogger("steelscope.viz_exports")
VIZ_DIR = EXPORTS_TABLEAU / "viz"
TS = V.TS


def chord_layers(flows: pd.DataFrame, sources: list[str], targets: list[str]) -> pd.DataFrame:
    """Ribbons + outer-ring arcs as polygons in one table (Tableau: Polygon mark, Path = point_order)."""
    arcs, rib = VS.chord_geometry(flows, sources, targets)
    rib = rib.assign(layer="ribbon", shape_id="R" + rib["ribbon_id"].astype(str), color_key=rib["source"],
                     label="")
    arc_rows = []
    for a in arcs.itertuples():
        outer = VS._arc(a.a0, a.a1, 1.09, 30)
        inner = VS._arc(a.a1, a.a0, 1.02, 30)
        mid = np.radians((a.a0 + a.a1) / 2)
        for k, (x, y) in enumerate(np.vstack([outer, inner])):
            arc_rows.append({"layer": "arc", "shape_id": f"A_{a.side}_{a.node}", "source": a.node if a.side == "source" else "",
                             "target": a.node if a.side == "target" else "", "value": a.value, "point_order": k, "x": x,
                             "y": y, "color_key": a.node if a.side == "source" else "destination",
                             "label": f"{a.node} ({int(a.value)})" if k == 0 else "",
                             "label_x": 1.2 * np.cos(mid), "label_y": 1.2 * np.sin(mid)})
    cols = ["layer", "shape_id", "source", "target", "value", "color_key", "point_order", "x", "y", "label"]
    out = pd.concat([rib[cols], pd.DataFrame(arc_rows)], ignore_index=True)
    return out


def radar_layers(table: pd.DataFrame, scale_max: float, rings=(0.25, 0.5, 0.75, 1.0)) -> pd.DataFrame:
    """Data polygons + background rings, spokes and axis-label anchors, with the grid repeated for every entity so
    a Tableau trellis (Entity on Columns) or an Entity filter keeps its own grid.
    Tableau: Line mark, Path = point_order, Detail = shape_id, Color = layer."""
    geo = VS.radar_geometry(table, scale_max).assign(layer="data")
    geo["shape_id"] = geo["entity"] + " | data"
    n = len(table.columns)
    ang = np.radians(90 - np.arange(n) * 360 / n)
    grid = []
    for ent in table.index:
        for r in rings:
            for i in range(n + 1):
                j = i % n
                grid.append({"layer": "grid", "shape_id": f"{ent} | ring {int(r * 100)}%", "entity": ent,
                             "axis": table.columns[j], "point_order": i, "x": r * np.cos(ang[j]), "y": r * np.sin(ang[j])})
        for j, a in enumerate(ang):
            for i, rr in enumerate([0, 1.0]):
                grid.append({"layer": "grid", "shape_id": f"{ent} | spoke {table.columns[j]}", "entity": ent,
                             "axis": table.columns[j], "point_order": i, "x": rr * np.cos(a), "y": rr * np.sin(a)})
            grid.append({"layer": "axis_label", "shape_id": f"{ent} | label {table.columns[j]}", "entity": ent,
                         "axis": table.columns[j], "point_order": 0, "x": 1.18 * np.cos(a), "y": 1.18 * np.sin(a)})
    return pd.concat([geo, pd.DataFrame(grid)], ignore_index=True)


def build_viz_exports(grades: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    grades = load_clean_grades() if grades is None else grades
    rare = load_pipeline_meta()["rare_elements"]
    g = V.with_groups(grades)
    m = g.dropna(subset=[TS])
    out: dict[str, pd.DataFrame] = {}

    fns = V.five_number_summary(g)
    out["five_number_summary.csv"] = fns.reset_index()
    out["descriptive_stats.csv"] = V.descriptive_stats(g).reset_index()
    out["binning_comparison.csv"] = V.binning_comparison(g)
    b = V.add_bins(g)
    out["binned_grades.csv"] = b[["grade_id", "display_name", "family_group", "family_label", TS, "C", "carbon_equivalent",
                                  "alloying_total", "carbon_band", "ce_band", "alloy_band", "strength_class_label"]].astype(
        {"carbon_band": str, "ce_band": str, "alloy_band": str})

    chi = V.chi_square_suite(grades)
    out["chi_square_tests.csv"] = pd.DataFrame([r.as_row() for r in chi])
    cells = []
    for r in chi:
        for i in r.observed.index:
            for j in r.observed.columns:
                cells.append({"test": r.name, "row_value": str(i), "col_value": str(j), "observed": int(r.observed.loc[i, j]),
                              "expected": float(r.expected.loc[i, j]), "std_residual": float(r.std_residuals.loc[i, j])})
    out["chi_square_cells.csv"] = pd.DataFrame(cells)

    reg = V.regression_suite(grades)
    out["regression_simple_band.csv"] = V.simple_regression_bands(reg["simple"], np.linspace(0, reg["carbon"]["C"].max(), 60))
    coef = reg["multi"].table().join(reg["std_multi"].table()[["coef"]].rename(columns={"coef": "standardized_beta"}))
    out["regression_coefficients.csv"] = coef.reset_index(names="term")

    X, feats = V.composition_space(grades, rare)
    pca = V.pca_analysis(X, feats)
    scores = pd.DataFrame(pca["scores"][:, :3], columns=["PC1", "PC2", "PC3"])
    out["pca_explained.csv"] = pca["explained"]
    out["pca_loadings.csv"] = pca["loadings"].iloc[:, :5].reset_index(names="element")
    scan = V.kmeans_scan(X)
    k, labels = V.kmeans_visual(X, scan)
    names = V.cluster_names(grades, labels)
    from sklearn.metrics import silhouette_samples
    out["kmeans_scan.csv"] = scan.reset_index()
    out["pca_kmeans_scores.csv"] = pd.concat([g[["grade_id", "display_name", "family_group", "family_label", TS]].reset_index(drop=True),
                                              scores], axis=1).assign(cluster=labels + 1, cluster_name=pd.Series(labels).map(names),
                                                                      silhouette=silhouette_samples(X, labels))

    raw, listings = pd.read_csv(DATA_RAW), pd.read_csv(CLEAN_LISTINGS_CSV)
    f1 = V.flow_raw_class_to_outcome(raw, listings, grades)
    src1 = sorted(f1["source"].unique())
    tgt1 = ["Grade class 0", "Grade class 1", "Grade class 2", "Unmeasured TS (excluded)", "Merged into twin listing",
            "Dropped: exact duplicate"]
    out["chord_raw_class_migration.csv"] = chord_layers(f1, src1, tgt1)
    f2 = V.flow_family_to_cluster(grades, labels, names)
    src2 = [s for s in VS.FAMILY_GROUP_ORDER if s in set(f2["source"])]
    tgt2 = [names[i] for i in sorted(names)]
    out["chord_family_to_cluster.csv"] = chord_layers(f2, src2, tgt2)
    out["flows_raw_class_migration.csv"] = f1
    out["flows_family_to_cluster.csv"] = f2

    fam_med = m.groupby("family_label")[TS].median().sort_values(ascending=False)
    rb = VS.radial_bar_geometry(fam_med)
    out["radial_bars_family_ts.csv"] = rb.merge(g[["family_label", "family_group"]].drop_duplicates(), left_on="bar",
                                                right_on="family_label", how="left")

    comp_scaled, comp_raw = V.radar_family_composition(grades)
    out["radar_family_composition.csv"] = radar_layers(comp_scaled, 1.0).merge(
        comp_raw.reset_index().melt(id_vars="family_group", var_name="axis", value_name="median_wt_pct"),
        left_on=["entity", "axis"], right_on=["family_group", "axis"], how="left").drop(columns="family_group")
    picks = V.showcase_grades(grades)
    out["radar_showcase_grades.csv"] = radar_layers(V.radar_grade_percentiles(grades, picks), 100.0)

    counts = {"raw": len(raw), "duplicates": int(raw.duplicated().sum()), "twins": int(len(listings) - len(grades)),
              "grades": len(grades), "unmeasured": int(grades[TS].isna().sum()), "measured": int(grades[TS].notna().sum())}
    out["waterfall_cleaning.csv"] = V.waterfall_layout(V.waterfall_cleaning(counts))
    r4140 = grades[grades["display_name"].str.startswith(V.SHOWCASE_GRADES["AISI 4140"])].iloc[0]
    out["waterfall_ce_aisi4140.csv"] = V.waterfall_layout(V.waterfall_ce(r4140))
    wf_pred, info = V.prediction_waterfall(grades, V.SHOWCASE_GRADES["AISI 4140"])
    out["waterfall_prediction_aisi4140.csv"] = V.waterfall_layout(wf_pred).assign(grade=info["grade"],
                                                                                  measured_ts=info["measured"])
    for df in out.values():
        if "row_id" not in df.columns:
            df.insert(0, "row_id", range(1, len(df) + 1))

    sizes = " ".join(map(str, pd.Series(labels).value_counts().sort_values(ascending=False).values))
    expected = knime_expected(fns, chi, reg, pca, scan, k, counts, sizes)
    return {"tableau": out, "knime": expected, "k": k, "names": names}


def knime_expected(fns, chi, reg, pca, scan, k, counts, k_sizes: str) -> pd.DataFrame:
    rows = []
    for var in [TS, "liquidus_c", "carbon_equivalent", "alloying_total"]:
        r = fns.loc[var]
        for stat in ["n", "min", "Q1", "median", "Q3", "max", "IQR", "n_outliers"]:
            rows.append({"section": "Five-number summary", "item": f"{var} | {stat}", "value": r[stat]})
    for r in chi:
        rows += [{"section": "Chi-square", "item": f"{r.name} | {s}", "value": v} for s, v in
                 [("chi2", r.chi2), ("df", r.dof), ("p_value", r.p_value), ("cramers_v", r.cramers_v), ("n", r.n)]]
    s = reg["simple"]
    rows += [{"section": "Simple regression (carbon steels, TS ~ C)", "item": i, "value": v} for i, v in
             [("n", s.n), ("intercept", s.coef[0]), ("slope C", s.coef[1]), ("R^2", s.r2), ("p slope", s.p[1])]]
    mr = reg["multi"]
    rows += [{"section": "Multiple regression (carbon & low-alloy)", "item": f"coef {t}", "value": c}
             for t, c in zip(mr.terms, mr.coef)]
    rows += [{"section": "Multiple regression (carbon & low-alloy)", "item": i, "value": v} for i, v in
             [("n", mr.n), ("R^2", mr.r2), ("adj R^2", mr.adj_r2)]]
    ev = pca["explained"]
    rows += [{"section": "PCA (log1p + z-score composition)", "item": f"{c} explained variance", "value": v}
             for c, v in zip(ev["component"].head(5), ev["explained_variance_ratio"].head(5))]
    rows.append({"section": "PCA (log1p + z-score composition)", "item": "components for 80 %", "value": pca["n_for_80pct"]})
    rows += [{"section": "k-Means scan", "item": f"k={kk} silhouette", "value": v} for kk, v in scan["silhouette"].items()]
    rows.append({"section": "k-Means scan", "item": "k used for visuals", "value": k})
    rows.append({"section": "k-Means scan", "item": f"cluster sizes at k={k}, largest first", "value": k_sizes})
    rows += [{"section": "Row counts (waterfall)", "item": i, "value": v} for i, v in counts.items()]
    return pd.DataFrame(rows)


def save(result: dict) -> None:
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in result["tableau"].items():
        df.to_csv(VIZ_DIR / name, index=False)
        logger.info("tableau/viz/%-36s %6d rows", name, len(df))
    result["knime"].to_csv(EXPORTS_KNIME / "viz_expected_values.csv", index=False)
    logger.info("knime/viz_expected_values.csv %d rows", len(result["knime"]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    save(build_viz_exports())


if __name__ == "__main__":
    main()
