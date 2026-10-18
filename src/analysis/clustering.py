"""Unsupervised structure of composition space, compared with the named families."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

from .constants import RANDOM_STATE
from .features import family_group
from .substitutes import SubstituteIndex, substitute_features

TRANSFORM = "log1p + z-score"   # same space as the substitute engine (chosen in substitutes.evaluate_transforms)


@dataclass
class ClusteringResult:
    matrix: np.ndarray
    silhouette_by_k: pd.Series
    k: int
    kmeans_labels: np.ndarray
    hdbscan_labels: np.ndarray
    agreement: pd.DataFrame
    contingency: pd.DataFrame
    profiles: pd.DataFrame
    pca_xy: np.ndarray
    pca_explained: np.ndarray
    umap_xy: np.ndarray | None


def composition_matrix(grades: pd.DataFrame, rare: list[str]) -> np.ndarray:
    return SubstituteIndex.fit(grades, substitute_features(rare), TRANSFORM).matrix


def silhouette_scan(X: np.ndarray, ks=range(4, 15)) -> pd.Series:
    return pd.Series({k: silhouette_score(X, KMeans(k, n_init=20, random_state=RANDOM_STATE).fit_predict(X),
                                          random_state=RANDOM_STATE) for k in ks}, name="silhouette")


def label_clusters(grades: pd.DataFrame, labels: np.ndarray, X: np.ndarray, feats: list[str]) -> pd.DataFrame:
    """Profile each cluster: size, dominant family, median TS, and the elements that most distinguish it
    (largest mean standardized value)."""
    rows = []
    for c in sorted(set(labels)):
        idx = labels == c
        sub = grades[idx]
        fam = sub["family_label"].value_counts()
        z = pd.Series(X[idx].mean(axis=0), index=feats).sort_values(ascending=False)
        top = [f"{e}↑" for e in z.index[:3] if z[e] > 0.5]
        rows.append({"cluster": int(c), "n": int(idx.sum()), "dominant_family": fam.index[0],
                     "dominant_share": float(fam.iloc[0] / idx.sum()), "n_families": int(sub["family"].nunique()),
                     "median_ts": float(sub["tensile_strength_mpa"].median()),
                     "median_alloying": float(sub["alloying_total"].median()),
                     "signature": " ".join(top) if top else "lean / near-average"})
    p = pd.DataFrame(rows).set_index("cluster")
    p["label"] = [f"C{c}: {r.dominant_family} ({r.signature})" for c, r in p.iterrows()]
    return p


def run_clustering(grades: pd.DataFrame, rare: list[str], k: int | None = None, with_umap: bool = True) -> ClusteringResult:
    g = grades.reset_index(drop=True)
    X = composition_matrix(g, rare)
    sil = silhouette_scan(X)
    k = int(sil.idxmax()) if k is None else k
    km = KMeans(k, n_init=50, random_state=RANDOM_STATE).fit_predict(X)
    hd = HDBSCAN(min_cluster_size=15, min_samples=5).fit_predict(X)
    rows = []
    for name, lab, mask in [("KMeans", km, np.ones(len(g), bool)), ("HDBSCAN (non-noise)", hd, hd >= 0)]:
        for ref in ["family", "family_group"]:
            truth = g[ref] if ref == "family" else family_group(g["family"])
            rows.append({"method": name, "vs": ref, "n_clusters": len(set(lab[mask])),
                         "noise_share": float(1 - mask.mean()),
                         "ARI": adjusted_rand_score(truth[mask], lab[mask]),
                         "NMI": normalized_mutual_info_score(truth[mask], lab[mask])})
    agreement = pd.DataFrame(rows)
    feats = substitute_features(rare)
    profiles = label_clusters(g, km, X, feats)
    contingency = pd.crosstab(pd.Series(km, name="cluster").map(profiles["label"]), g["family_label"])
    pca = PCA(n_components=2, random_state=RANDOM_STATE).fit(X)
    umap_xy = None
    if with_umap:
        import umap
        umap_xy = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=RANDOM_STATE).fit_transform(X)
    return ClusteringResult(X, sil, k, km, hd, agreement, contingency, profiles, pca.transform(X),
                            pca.explained_variance_ratio_, umap_xy)

