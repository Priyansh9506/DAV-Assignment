"""Nearest-neighbour substitute engine on transformed, standardized composition.

The same `SubstituteIndex` is used by notebook 03 (evaluation) and by the app (src/services), so the
neighbours a user sees are exactly the ones that were evaluated.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances

from .constants import ELEMENTS

TS = "tensile_strength_mpa"
TRANSFORMS = {
    "raw wt% (unscaled)": (lambda x: x, False),
    "z-score": (lambda x: x, True),
    "sqrt + z-score": (np.sqrt, True),
    "log1p + z-score": (np.log1p, True),
}


def substitute_features(rare: list[str]) -> list[str]:
    """Every non-rare element except Fe (redundant with the others) plus summed trace elements."""
    return [el for el in ELEMENTS if el not in rare and el != "Fe"] + ["trace_total"]


@dataclass
class SubstituteIndex:
    features: list[str]
    transform: str
    center: np.ndarray
    scale: np.ndarray
    matrix: np.ndarray            # transformed + standardized rows, aligned to `ids`
    ids: np.ndarray

    @classmethod
    def fit(cls, grades: pd.DataFrame, features: list[str], transform: str, id_col: str = "grade_id") -> "SubstituteIndex":
        fn, standardize = TRANSFORMS[transform]
        T = fn(grades[features].to_numpy(dtype=float))
        center = T.mean(axis=0) if standardize else np.zeros(T.shape[1])
        scale = T.std(axis=0) if standardize else np.ones(T.shape[1])
        scale = np.where(scale > 0, scale, 1.0)
        return cls(features, transform, center, scale, (T - center) / scale, grades[id_col].to_numpy())

    def vectorize(self, comp: pd.DataFrame) -> np.ndarray:
        fn, _ = TRANSFORMS[self.transform]
        return (fn(comp[self.features].to_numpy(dtype=float)) - self.center) / self.scale

    def distances_from(self, vec: np.ndarray) -> np.ndarray:
        return np.sqrt(((self.matrix - vec) ** 2).sum(axis=1))

    def to_config(self) -> dict:
        return {"features": self.features, "transform": self.transform,
                "center": self.center.tolist(), "scale": self.scale.tolist()}


def nearest_non_identical(index: SubstituteIndex, grades: pd.DataFrame, k: int = 1) -> pd.DataFrame:
    """For every grade, its k nearest neighbours that do NOT share its exact composition (identical
    chemistry would make the evaluation trivial)."""
    D = pairwise_distances(index.matrix)
    grp = grades["composition_group_id"].to_numpy()
    D[grp[:, None] == grp[None, :]] = np.inf
    order = np.argsort(D, axis=1)[:, :k]
    rows = []
    for i in range(len(grades)):
        for rank, j in enumerate(order[i], 1):
            rows.append({"i": i, "j": j, "rank": rank, "distance": D[i, j]})
    return pd.DataFrame(rows)


def evaluate_transforms(grades: pd.DataFrame, rare: list[str], k: int = 5, seed: int = 0) -> pd.DataFrame:
    """Does the nearest neighbour behave like a substitute? Family agreement and |ΔTS| of the nearest
    non-identical neighbour, compared to a random-pair baseline."""
    g = grades.reset_index(drop=True)
    feats = substitute_features(rare)
    ts, fam, liq = g[TS].to_numpy(), g["family"].to_numpy(), g["liquidus_c"].to_numpy()
    rng = np.random.default_rng(seed)
    rand_j = rng.integers(0, len(g), size=len(g))
    rows = [{"transform": "random pair (baseline)", "family_agree@1": float(np.mean(fam == fam[rand_j])),
             "family_agree@5": np.nan,
             "median_abs_dTS@1": float(np.nanmedian(np.abs(ts - ts[rand_j]))),
             "median_abs_dLiq@1": float(np.median(np.abs(liq - liq[rand_j])))}]
    for name in TRANSFORMS:
        idx = SubstituteIndex.fit(g, feats, name)
        nn = nearest_non_identical(idx, g, k=k)
        first = nn[nn["rank"] == 1]
        i, j = first["i"].to_numpy(), first["j"].to_numpy()
        rows.append({"transform": name, "family_agree@1": float(np.mean(fam[i] == fam[j])),
                     "family_agree@5": float(np.mean(fam[nn["i"]] == fam[nn["j"]])),
                     "median_abs_dTS@1": float(np.nanmedian(np.abs(ts[i] - ts[j]))),
                     "median_abs_dLiq@1": float(np.median(np.abs(liq[i] - liq[j])))})
    return pd.DataFrame(rows).set_index("transform")


def top_differences(diff: pd.Series, n: int = 3) -> str:
    """'Ni -4.50, Mo +2.10, Cr -1.00': the n element differences (candidate - reference, wt%) largest in size."""
    nz = diff[diff.abs() > 1e-9]
    top = nz.reindex(nz.abs().sort_values(ascending=False).index).head(n)
    return ", ".join(f"{el} {v:+.2f}" for el, v in top.items())


def find_substitutes(index: SubstituteIndex, grades: pd.DataFrame, grade_id: str, k: int = 5,
                     leaner_only: bool = False, same_family: bool = False, include_identical: bool = True) -> pd.DataFrame:
    """Top-k substitutes for one grade with strength / liquidus / alloy-content deltas and the elements
    that differ most."""
    g = grades.set_index("grade_id")
    if grade_id not in g.index:
        raise KeyError(grade_id)
    ref = g.loc[grade_id]
    pos = {gid: i for i, gid in enumerate(index.ids)}
    d = pd.Series(index.distances_from(index.matrix[pos[grade_id]]), index=index.ids, name="distance")
    cand = g.join(d).drop(index=grade_id)
    if not include_identical:
        cand = cand[cand["composition_group_id"] != ref["composition_group_id"]]
    if leaner_only:
        cand = cand[cand["alloying_total"] < ref["alloying_total"]]
    if same_family:
        cand = cand[cand["family"] == ref["family"]]
    top = cand.nsmallest(k, "distance").copy()
    top["delta_ts_mpa"] = top[TS] - ref[TS]
    top["delta_liquidus_c"] = top["liquidus_c"] - ref["liquidus_c"]
    top["delta_alloying_total"] = top["alloying_total"] - ref["alloying_total"]
    els = [e for e in ELEMENTS if e != "Fe"]
    diffs = top[els].sub(ref[els], axis=1)
    top["largest_differences"] = [top_differences(row) for _, row in diffs.iterrows()]
    cols = ["display_name", "family_label", "distance", TS, "delta_ts_mpa", "liquidus_c", "delta_liquidus_c",
            "alloying_total", "delta_alloying_total", "largest_differences"]
    return top[cols].reset_index()
