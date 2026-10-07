"""Cleaning pipeline on a small synthetic raw file with every data issue planted."""
import numpy as np
import pandas as pd
import pytest

from src.analysis import cleaning as C
from src.analysis.constants import ELEMENTS, IMPUTED_TS_VALUE


def _row(name, ts, liq, cls, **comp):
    r = {"Alloy": name, "Tensile Strength": ts, "Melting Completion (Liquidus)": liq, "Class": cls}
    r.update({el: 0.0 for el in ELEMENTS})
    r.update(comp)
    return r


@pytest.fixture
def raw_csv(tmp_path):
    rows = [
        # twin pair, both measured
        _row("EN 1.0420 (GE200) Cast Non-Alloy Steel", 480, 1460, 1, Fe=98.9, C=0.3, Mn=0.8),
        _row("EN-1.0420-GE200-Cast-Non-Alloy-Steel", 480, 1460, 1, Fe=98.9, C=0.3, Mn=0.8),
        # exact duplicate of the line above
        _row("EN-1.0420-GE200-Cast-Non-Alloy-Steel", 480, 1460, 1, Fe=98.9, C=0.3, Mn=0.8),
        # twin pair, hyphenated listing imputed
        _row("AISI 201 (S20100) Stainless Steel", 650, 1410, 2, Fe=72.0, C=0.1, Cr=17.0, Ni=4.5, Mn=6.4),
        _row("AISI-201-S20100-Stainless-Steel", IMPUTED_TS_VALUE, 1410, 2, Fe=72.0, C=0.1, Cr=17.0, Ni=4.5, Mn=6.4),
        # single listing, imputed only
        _row("Grey-Cast-Iron", IMPUTED_TS_VALUE, 1250, 2, Fe=94.0, C=3.4, Si=2.2, Mn=0.4),
        # same composition as the grey iron, different measured strength (processing variant)
        _row("ASTM Grade 20 or 150 (ISO 150, EN-JL 1020, F11401) Grey Cast Iron", 160, 1250, 0, Fe=94.0, C=3.4, Si=2.2, Mn=0.4),
        _row("ASTM Grade 40 or 275 (F12801) Grey Cast Iron", 290, 1250, 0, Fe=94.0, C=3.4, Si=2.2, Mn=0.4),
        # generic name -> composition rule
        _row("EN 1.8901 (S460N) Steel", 600, 1460, 1, Fe=97.6, C=0.2, Mn=1.7, Nb=0.05, V=0.2),
    ]
    path = tmp_path / "raw.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_pipeline_row_counts(raw_csv):
    res = C.run_cleaning(raw_csv)
    log = res.log
    assert log.get("load_raw").rows_after == 9
    assert log.get("drop_exact_duplicates").rows_after == 8
    assert log.get("flag_imputed_ts").metrics["n_imputed"] == 2
    assert log.get("collapse_to_grades").rows_after == 6
    assert len(res.grades) == 6 and len(res.listings) == 8


def test_twin_recovers_measured_ts_and_unmeasured_grade_is_nan(raw_csv):
    g = C.run_cleaning(raw_csv).grades.set_index("canonical_grade")
    aisi = g.loc[C.canonical_key("AISI 201 (S20100) Stainless Steel")]
    assert aisi["tensile_strength_mpa"] == 650
    assert not aisi["is_imputed_ts"] and aisi["had_imputed_listing"]
    assert aisi["display_name"] == "AISI 201 (S20100) Stainless Steel"   # spaced name preferred
    grey = g.loc[C.canonical_key("Grey-Cast-Iron")]
    assert np.isnan(grey["tensile_strength_mpa"]) and grey["is_imputed_ts"]
    assert pd.isna(grey["strength_class"])


def test_features_and_flags(raw_csv):
    g = C.run_cleaning(raw_csv).grades.set_index("display_name")
    assert g.loc["EN 1.8901 (S460N) Steel", "family"] == "alloy"
    assert g.loc["EN 1.8901 (S460N) Steel", "family_source"] == "composition_rule"
    assert g.loc["EN 1.0420 (GE200) Cast Non-Alloy Steel", "family"] == "carbon"
    assert g.loc["EN 1.0420 (GE200) Cast Non-Alloy Steel", "liquidus_is_default"]
    assert g.loc["EN 1.0420 (GE200) Cast Non-Alloy Steel", "product_form"] == "cast"
    # three grey-iron grades share one composition group
    grey = g[g["family"] == "cast_iron_grey"]
    assert grey["composition_group_id"].nunique() == 1
    assert (grey["composition_group_size"] == 3).all()
    assert (grey["composition_group_n_measured"] == 2).all()


def test_strength_class_bins():
    ts = pd.Series([140, 290, 300, 600, 610, 2450, np.nan])
    assert C.strength_class(ts).tolist()[:6] == [0, 0, 1, 1, 2, 2]
    assert pd.isna(C.strength_class(ts).iloc[6])


def test_canonical_key_merges_formats():
    assert C.canonical_key("ACI-ASTM CF8 (SCS13, SCS13A,J92600) Cast Stainless Steel") == \
        C.canonical_key("ACI-ASTM-CF8-SCS13-SCS13A-J92600-Cast-Stainless-Steel")


def test_conflicting_twin_compositions_raise(tmp_path):
    rows = [_row("EN 1.0420 (GE200) Steel", 480, 1460, 1, Fe=98.9, C=0.3),
            _row("EN-1.0420-GE200-Steel", 480, 1460, 1, Fe=98.8, C=0.4)]
    path = tmp_path / "bad.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    with pytest.raises(ValueError, match="composition"):
        C.run_cleaning(path)


def test_missing_column_raises(tmp_path):
    df = pd.DataFrame([_row("X", 500, 1460, 1, Fe=100.0)]).drop(columns=["Zr"])
    path = tmp_path / "missing.csv"
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        C.run_cleaning(path)
