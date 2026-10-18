import numpy as np
import pandas as pd
import pytest

from src.analysis import visual_stats as V
from src.analysis import viz_suite as VS


def test_five_number_summary_matches_numpy():
    df = pd.DataFrame({"tensile_strength_mpa": [1, 2, 3, 4, 100.0]})
    r = V.five_number_summary(df, cols=["tensile_strength_mpa"]).loc["tensile_strength_mpa"]
    assert (r["min"], r["Q1"], r["median"], r["Q3"], r["max"]) == (1, 2, 3, 4, 100)
    assert r["IQR"] == 2 and r["upper_fence"] == 7 and r["n_outliers"] == 1


def test_chi_square_independent_vs_dependent():
    rng = np.random.default_rng(0)
    a = rng.choice(["x", "y"], 400)
    indep = V.chi_square(pd.DataFrame({"a": a, "b": rng.choice(["p", "q"], 400)}), "a", "b", "indep", n_perm=200)
    dep = V.chi_square(pd.DataFrame({"a": a, "b": np.where(a == "x", "p", "q")}), "a", "b", "dep", n_perm=200)
    assert indep.p_value > 0.01 and indep.cramers_v < 0.2
    assert dep.p_value < 1e-10 and dep.cramers_v == pytest.approx(1.0, abs=1e-9)
    assert dep.p_permutation <= 1 / 201 + 1e-12          # never exceeded by a permutation
    assert dep.asymptotic_valid


def test_ols_matches_polyfit_and_bands_order():
    rng = np.random.default_rng(1)
    x = rng.uniform(0, 1, 200)
    y = 400 + 450 * x + rng.normal(0, 30, 200)
    res = V.ols(pd.DataFrame({"C": x}), pd.Series(y))
    slope, intercept = np.polyfit(x, y, 1)
    assert res.coef[1] == pytest.approx(slope) and res.coef[0] == pytest.approx(intercept)
    assert 0.9 < res.r2 < 1 and res.p[1] < 1e-50
    band = V.simple_regression_bands(res, np.linspace(0, 1, 5))
    assert (band["pi_low"] < band["ci_low"]).all() and (band["ci_high"] < band["pi_high"]).all()


def test_waterfall_layout_running_total():
    wf = pd.DataFrame([{"step": "start", "value": 100, "kind": "total"}, {"step": "a", "value": -30, "kind": "delta"},
                       {"step": "b", "value": 10, "kind": "delta"}, {"step": "end", "value": 80, "kind": "total"}])
    lay = V.waterfall_layout(wf)
    assert lay["start"].tolist() == [0, 100, 70, 0] and lay["end"].tolist() == [100, 70, 80, 80]


def test_chord_geometry_conserves_flows():
    flows = pd.DataFrame({"source": ["A", "A", "B"], "target": ["X", "Y", "X"], "value": [10, 30, 20]})
    arcs, rib = VS.chord_geometry(flows, ["A", "B"], ["X", "Y"])
    assert rib["ribbon_id"].nunique() == 3
    span = (arcs["a1"] - arcs["a0"]).to_numpy()
    assert span[0] / span[1] == pytest.approx(40 / 20)                 # arc length ∝ total flow
    r = np.hypot(rib["x"], rib["y"])
    assert r.max() <= 1.0 + 1e-9                                       # ribbons stay inside the ring


def test_radar_geometry_closed_polygons():
    table = pd.DataFrame({"a": [1.0, 0.5], "b": [0.2, 1.0], "c": [0.0, 0.5]}, index=["e1", "e2"])
    geo = VS.radar_geometry(table, scale_max=1.0)
    for _, g in geo.groupby("entity"):
        assert len(g) == 4
        assert g["x"].iloc[0] == pytest.approx(g["x"].iloc[-1]) and g["y"].iloc[0] == pytest.approx(g["y"].iloc[-1])
    top = geo[(geo["entity"] == "e1") & (geo["axis"] == "a")].iloc[0]
    assert top["x"] == pytest.approx(0, abs=1e-12) and top["y"] == pytest.approx(1.0)   # first axis points up


def test_radial_bar_geometry_lengths():
    geo = VS.radial_bar_geometry(pd.Series({"big": 100.0, "small": 50.0}), inner=0.35, max_len=0.6)
    r = geo.assign(r=np.hypot(geo["x"], geo["y"])).groupby("bar")["r"].max()
    assert r["big"] == pytest.approx(0.95) and r["small"] == pytest.approx(0.65)
