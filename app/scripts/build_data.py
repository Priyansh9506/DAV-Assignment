"""Build the SteelScope app's data files from the cleaned dataset.

Reads  ../data/processed/steels_clean.csv  (written by notebooks/01_cleaning.ipynb)
Writes src/data/grades.json     one record per canonical grade (1,389), read on the server only
       src/data/meta.json       element list, family groups, PCA summary, data provenance
       public/data/search.json  [id, name, group] per grade, fetched once by the browser for grade search
       public/data/points.json  [id, PC1, PC2] per grade, fetched once by the browser for the chemistry map

Everything the app shows is computed here or in the browser from these two files; nothing is typed in by hand.
Run from the app folder:  python scripts/build_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
SRC = ROOT / "data" / "processed" / "steels_clean.csv"
META_IN = ROOT / "data" / "processed" / "pipeline_meta.json"
CLEANING_LOG = ROOT / "reports" / "cleaning_log.json"
OUT = APP / "src" / "data"
PUBLIC = APP / "public" / "data"

ELEMENTS = ["Al", "As", "B", "C", "Ca", "Ce", "Co", "Cr", "Cu", "Fe", "La", "Mg", "Mn", "Mo", "N", "Nb", "Ni",
            "O", "P", "Pb", "S", "Se", "Si", "Sn", "Ta", "Ti", "V", "W", "Zn", "Zr"]
N_NEIGHBOURS = 10
RANDOM_STATE = 42

# Same six groups as the KNIME Rule Engine and notebook 03, in the Neon Forge colour order.
GROUP_ORDER = ["Carbon & low-alloy", "Stainless", "Cast iron", "Tool & high-speed", "Weld metal", "Other"]
GROUP_OF_FAMILY = {
    **{f: "Carbon & low-alloy" for f in ["carbon", "alloy", "boron", "spring", "bearing", "nitriding", "weathering"]},
    "stainless": "Stainless",
    "tool": "Tool & high-speed", "high_speed": "Tool & high-speed",
    "weld_metal": "Weld metal",
}


def family_group(family: str) -> str:
    if family in GROUP_OF_FAMILY:
        return GROUP_OF_FAMILY[family]
    return "Cast iron" if family.startswith("cast_iron") else "Other"


def composition_space(grades: pd.DataFrame, rare: list[str]) -> tuple[np.ndarray, list[str]]:
    """log1p + z-score of every non-rare element except Fe plus summed trace elements (as in notebook 03)."""
    feats = [el for el in ELEMENTS if el not in rare and el != "Fe"] + ["trace_total"]
    T = np.log1p(grades[feats].to_numpy(dtype=float))
    sd = T.std(axis=0)
    return (T - T.mean(axis=0)) / np.where(sd > 0, sd, 1.0), feats


def nearest_neighbours(X: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """k nearest grades by Euclidean distance, plus the share of all grade pairs that are farther apart."""
    sq = (X ** 2).sum(axis=1)
    D = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0.0))
    D[np.abs(D) < 1e-9] = 0.0
    pair_d = np.sort(D[np.triu_indices_from(D, k=1)])
    np.fill_diagonal(D, np.inf)
    idx = np.argsort(D, axis=1, kind="stable")[:, :k]
    dist = np.take_along_axis(D, idx, axis=1)
    farther = 1.0 - np.searchsorted(pair_d, dist, side="right") / len(pair_d)
    return idx, dist, farther


def r(x: float, nd: int) -> float | None:
    return None if pd.isna(x) else round(float(x), nd)


def main() -> None:
    g = pd.read_csv(SRC)
    meta_in = json.loads(META_IN.read_text())
    rare = meta_in["rare_elements"]
    g["family_group"] = g["family"].map(family_group)

    X, feats = composition_space(g, rare)
    pca = PCA(random_state=RANDOM_STATE).fit(X)
    scores = pca.transform(X)[:, :2]
    nb_idx, nb_dist, nb_farther = nearest_neighbours(X, N_NEIGHBOURS)

    records = []
    for i, row in g.reset_index(drop=True).iterrows():
        comp = {el: r(row[el], 4) for el in ELEMENTS if row[el] > 0}
        records.append({
            "id": row["grade_id"],
            "name": row["display_name"],
            "alt": None if pd.isna(row["alt_name"]) else row["alt_name"],
            "family": row["family"],
            "familyLabel": row["family_label"],
            "group": row["family_group"],
            "form": row["product_form"],
            "standard": row["naming_source"],
            "listings": int(row["n_listings"]),
            "ts": r(row["tensile_strength_mpa"], 1),
            "strengthClass": None if pd.isna(row["strength_class"]) else int(row["strength_class"]),
            "liquidus": r(row["liquidus_c"], 1),
            "liquidusDefault": bool(row["liquidus_is_default"]),
            "comp": comp,
            "traceTotal": r(row["trace_total"], 4),
            "alloyTotal": r(row["alloying_total"], 4),
            "ce": r(row["carbon_equivalent"], 4),
            "crEq": r(row["cr_eq"], 4),
            "niEq": r(row["ni_eq"], 4),
            "chemTwins": int(row["composition_group_size"]) - 1,
            "pc": [r(scores[i, 0], 3), r(scores[i, 1], 3)],
            "neighbours": [
                {"id": g.at[int(j), "grade_id"], "distance": r(d, 3), "fartherShare": r(f, 4)}
                for j, d, f in zip(nb_idx[i], nb_dist[i], nb_farther[i])
            ],
        })

    loadings = pd.DataFrame(pca.components_[:2].T * np.sqrt(pca.explained_variance_[:2]), index=feats,
                            columns=["PC1", "PC2"])
    top = {pc: loadings[pc].abs().sort_values(ascending=False).index[:4].tolist() for pc in ["PC1", "PC2"]}
    meta = {
        "source": "data/processed/steels_clean.csv (notebooks/01_cleaning.ipynb)",
        "nGrades": int(len(g)),
        "nMeasured": int(g["tensile_strength_mpa"].notna().sum()),
        "elements": ELEMENTS,
        "rareElements": rare,
        "pcaFeatures": feats,
        "groupOrder": GROUP_ORDER,
        "pca": {
            "explained": [round(float(v), 4) for v in pca.explained_variance_ratio_[:5]],
            "componentsFor80": int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), 0.80) + 1),
            "topLoadings": {pc: [{"element": el, "loading": round(float(loadings.at[el, pc]), 3)} for el in els]
                            for pc, els in top.items()},
        },
        "defaultLiquidus": meta_in["default_liquidus_c"],
        "nDefaultLiquidus": int(g["liquidus_is_default"].sum()),
        "cleaning": [{"step": s["step"], "detail": s["detail"], "rowsAfter": s["rows_after"]}
                     for s in json.loads(CLEANING_LOG.read_text())],
        "strengthClasses": [{"value": int(c), "label": lab, "min": float(s.min()), "max": float(s.max())}
                            for (c, lab), s in g.groupby(["strength_class", "strength_class_label"])
                            ["tensile_strength_mpa"]],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "grades.json").write_text(json.dumps(records, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    compact = {"separators": (",", ":"), "ensure_ascii": False}
    (PUBLIC / "search.json").write_text(json.dumps([[r["id"], r["name"], r["group"]] for r in records], **compact),
                                        encoding="utf-8")
    (PUBLIC / "points.json").write_text(json.dumps([[r["id"], *r["pc"]] for r in records], **compact),
                                        encoding="utf-8")
    print(f"wrote {len(records)} grades, PC1+PC2 = {sum(meta['pca']['explained'][:2]):.3f}, "
          f"{(OUT / 'grades.json').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
