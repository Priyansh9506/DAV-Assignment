import pandas as pd
import pytest

from src.analysis import features as F
from src.analysis.constants import ELEMENTS


@pytest.mark.parametrize("name, family", [
    ("EN 1.0420 (GE200) Cast Non-Alloy Steel", "carbon"),
    ("EN-1.0420-GE200-Cast-Non-Alloy-Steel", "carbon"),
    ("SAE-AISI 1043 (G10430) Carbon Steel", "carbon"),
    ("SAE-AISI 4137 (G41370) Cr-Mo Steel", "alloy"),
    ("ASTM A387 Grade 22 (K21590) 2.25Cr-1Mo Steel", "alloy"),
    ("AWS E308L (W30813) Weld Metal", "weld_metal"),
    ("ACI-ASTM CA15 (SCS1,J91150) Cast Stainless Steel", "stainless"),
    ("SAE-AISI M2 (T11302) Molybdenum High-Speed Steel", "high_speed"),
    ("SAE-AISI O2 (T31502) Oil-Hardening Steel", "tool"),
    ("Aged Grade 300 Maraging Steel", "maraging"),
    ("ASTM Grade 30 or 200 (ISO 200, EN-JL 1030, F12101) Grey Cast Iron", "cast_iron_grey"),
    ("ASTM Grade 65-45-12 (SAE D4512, ISO 450-10) Ductile Cast Iron", "cast_iron_ductile"),
    ("ASTM A439 Type D-2 (S-NiCr 20 2, F43000) Cast Iron", "cast_iron_austenitic"),
    ("ASTM A602 Grade M3210 (F20000) Cast Iron", "cast_iron_malleable"),
    ("Type 1 (K94490) Iron-Nickel Soft Magnetic Alloy", "fe_ni_special"),
    ("EN 1.3961 (GX3Ni36) Casting Alloy", "fe_ni_special"),
    ("EN 1.5522 (22MnB4) Boron Steel", "boron"),
])
def test_family_from_name(name, family):
    assert F.family_from_name(name) == family


def test_generic_name_falls_back_to_composition():
    assert F.family_from_name("EN 1.8901 (S460N) Steel") is None


def _comp(**kw):
    row = {el: 0.0 for el in ELEMENTS}
    row.update(kw)
    return pd.Series(row)


def test_family_from_composition_rules():
    assert F.family_from_composition(_comp(Fe=98.5, C=0.2, Mn=1.2, Si=0.3)) == "carbon"
    assert F.family_from_composition(_comp(Fe=97.0, C=0.4, Mn=0.8, Cr=1.0, Mo=0.2)) == "alloy"
    assert F.family_from_composition(_comp(Fe=70.0, C=0.05, Cr=18.0, Ni=10.0)) == "stainless"
    # high-carbon high-Cr (e.g. cast iron chemistry) is not stainless by the EN definition
    assert F.family_from_composition(_comp(Fe=80.0, C=2.5, Cr=15.0)) == "alloy"


@pytest.mark.parametrize("name, source", [
    ("EN 1.4301 (X5CrNi18-10) Stainless Steel", "EN"),
    ("EN-1.4301-X5CrNi18-10-Stainless-Steel", "EN"),
    ("SAE-AISI 4140 (G41400) Cr-Mo Steel", "SAE-AISI"),
    ("AISI 201 (S20100) Stainless Steel", "SAE-AISI"),
    ("ASTM A182 Grade F5 (K41545) Steel", "ASTM"),
    ("UNS S30601 (Alloy 611) Stainless Steel", "UNS"),
    ("AWS E308L (W30813) Weld Metal", "AWS"),
    ("ACI-ASTM CF8 (SCS13, SCS13A,J92600) Cast Stainless Steel", "ACI"),
    ("Grade 300 Maraging Steel", "Other"),
])
def test_naming_source(name, source):
    assert F.naming_source(name) == source


@pytest.mark.parametrize("name, family, form", [
    ("AWS E308L (W30813) Weld Metal", "weld_metal", "weld"),
    ("EN 1.4408 (GX5CrNiMo19-11-2) Cast Stainless Steel", "stainless", "cast"),
    ("EN-1.4518-GX2CrNiMo19-11-3-Cast-Stainless-Steel", "stainless", "cast"),
    ("EN 1.7357 (G17CrMo5-5) Cast Steel", "alloy", "cast"),
    ("ACI-ASTM CA15M (J91151) Cast Stainless Steel", "stainless", "cast"),
    ("Grey-Cast-Iron", "cast_iron_grey", "cast"),
    ("EN 1.4301 (X5CrNi18-10) Stainless Steel", "stainless", "wrought"),
])
def test_product_form(name, family, form):
    assert F.product_form(name, family) == form


def test_condition_in_name():
    assert F.condition_in_name("Aged Grade 300 Maraging Steel") == "aged"
    assert F.condition_in_name("H900 Hardened CB7Cu-1 Cast Stainless Steel") == "precipitation_hardened"
    assert F.condition_in_name("Full-Hard Type 1 Iron-Nickel Soft Magnetic Alloy") == "full_hard"
    assert F.condition_in_name("EN 1.4301 (X5CrNi18-10) Stainless Steel") == "none"


def test_composition_features_iiw_carbon_equivalent():
    row = _comp(Fe=96.0, C=0.4, Mn=0.9, Cr=1.0, Mo=0.2, V=0.1, Ni=1.5, Cu=0.15)
    out = F.composition_features(pd.DataFrame([row]))
    expected_ce = 0.4 + 0.9 / 6 + (1.0 + 0.2 + 0.1) / 5 + (1.5 + 0.15) / 15
    assert out.loc[0, "carbon_equivalent"] == pytest.approx(expected_ce)
    assert out.loc[0, "alloying_total"] == pytest.approx(4.0)
    assert out.loc[0, "cr_plus_ni"] == pytest.approx(2.5)
    assert not out.loc[0, "is_stainless_comp"]


def test_composition_group_ids_are_order_independent():
    a, b = _comp(Fe=99.0, C=1.0), _comp(Fe=98.0, C=2.0)
    ids1 = F.composition_group_ids(pd.DataFrame([a, b, a]))
    ids2 = F.composition_group_ids(pd.DataFrame([b, a, a]))
    assert ids1.iloc[0] == ids1.iloc[2] != ids1.iloc[1]
    assert set(ids1) == set(ids2)
    assert ids1.iloc[0] == ids2.iloc[1]


def test_rare_elements_threshold():
    df = pd.DataFrame([_comp(Fe=99.0, C=1.0, Pb=0.1)] + [_comp(Fe=99.0, C=1.0)] * 5)
    rare = F.rare_elements(df, min_rows=2)
    assert "Pb" in rare and "C" not in rare and "Fe" not in rare
