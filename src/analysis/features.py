"""Feature engineering for steel grades.

Every function takes a DataFrame with the 30 element columns (wt%) and/or a `display_name`
column and returns a Series/DataFrame aligned to the input index. No function mutates its input.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .constants import EN10020_ALLOY_LIMITS, ELEMENTS, STAINLESS_MIN_CR

# --------------------------------------------------------------------------------------------
# Family taxonomy
# --------------------------------------------------------------------------------------------
# Ordered rules: the first pattern that matches the grade name wins. Process-defined families
# (weld metal) and metallurgically distinct ones (maraging, cast irons) come before keyword
# families so that e.g. "AWS E308L Weld Metal" is weld metal, not stainless.
FAMILY_RULES: list[tuple[str, str]] = [
    ("maraging", r"maraging"),
    ("cast_iron_austenitic", r"\bA436\b|\bA439\b|\bA571\b"),           # Ni-Resist irons
    ("cast_iron_grey", r"gr[ae]y[\s-]+cast[\s-]+iron"),
    ("cast_iron_malleable", r"malleable|\bA602\b"),
    ("cast_iron_ductile", r"ductile|nodular|spheroidal|austempered|\bA897\b|EN-JS|\b\d{2,3}-\d{2,3}-\d{1,2}\b.*cast iron"),
    ("cast_iron_other", r"cast[\s-]+iron"),
    ("fe_ni_special", r"soft[\s-]+magnetic|expansion|sealing|casting[\s-]+alloy|iron-nickel-chromium|iron-cobalt|fe-cr-ni-co|fe-ni-co"),
    ("weld_metal", r"weld"),
    ("high_speed", r"high[\s-]+speed"),
    ("tool", r"tool|hot[\s-]+work|cold[\s-]+work|air[\s-]+hardening|oil[\s-]+hardening|water[\s-]+hardening|shock[\s-]+resisting|mou?ld"),
    ("stainless", r"stainless"),
    ("bearing", r"bearing"),
    ("spring", r"spring|music[\s-]+wire"),
    ("boron", r"boron"),
    ("nitriding", r"nitriding"),
    ("weathering", r"weathering"),
    # carbon must precede alloy: "Non-Alloy Steel" contains "Alloy Steel"
    ("carbon", r"non[\s-]+alloy|carbon[\s-]+steel|structural[\s-]+carbon"),
    ("alloy", r"carbon[\s-]+molybdenum|chromium|molybdenum|nickel|vanadium|tungsten|silicon|"
              r"ni-cr-mo|cr-mo|(?<!non-)(?<!non )alloy[\s-]+steel|\d+(\.\d+)?cr-\d"),
]
_COMPILED_FAMILY_RULES = [(fam, re.compile(p, re.IGNORECASE)) for fam, p in FAMILY_RULES]

FAMILY_LABELS = {
    "carbon": "Carbon / non-alloy steel",
    "alloy": "Alloy steel",
    "stainless": "Stainless steel",
    "tool": "Tool steel",
    "high_speed": "High-speed steel",
    "maraging": "Maraging steel",
    "bearing": "Bearing steel",
    "spring": "Spring steel",
    "boron": "Boron steel",
    "nitriding": "Nitriding steel",
    "weathering": "Weathering steel",
    "weld_metal": "Weld metal",
    "cast_iron_grey": "Grey cast iron",
    "cast_iron_ductile": "Ductile cast iron",
    "cast_iron_malleable": "Malleable cast iron",
    "cast_iron_austenitic": "Austenitic (Ni-Resist) cast iron",
    "cast_iron_other": "Other cast iron",
    "fe_ni_special": "Fe-Ni/Co special alloy",
}


def family_from_name(name: str) -> str | None:
    """Return the first family whose rule matches `name`, or None if no rule matches."""
    for fam, pattern in _COMPILED_FAMILY_RULES:
        if pattern.search(name):
            return fam
    return None


def family_from_composition(row: pd.Series) -> str:
    """EN 10020-style fallback: stainless if Cr >= 10.5 and C <= 1.2, alloy if any element
    exceeds its non-alloy limit, otherwise carbon."""
    if row["Cr"] >= STAINLESS_MIN_CR and row["C"] <= 1.2:
        return "stainless"
    if any(row[el] >= lim for el, lim in EN10020_ALLOY_LIMITS.items()):
        return "alloy"
    return "carbon"


def assign_family(df: pd.DataFrame, name_col: str = "display_name") -> pd.DataFrame:
    """Return `family` and `family_source` ('name' or 'composition_rule')."""
    by_name = df[name_col].map(family_from_name)
    by_comp = df.apply(family_from_composition, axis=1)
    family = by_name.fillna(by_comp)
    source = np.where(by_name.notna(), "name", "composition_rule")
    return pd.DataFrame({"family": family, "family_source": source}, index=df.index)


# --------------------------------------------------------------------------------------------
# Naming source, product form, processing condition
# --------------------------------------------------------------------------------------------
_NAMING_SOURCE_RULES = [
    ("ACI", r"^ACI\b"),
    ("SAE-AISI", r"^(SAE|AISI)\b"),
    ("ASTM", r"^ASTM\b"),
    ("EN", r"^EN\b"),
    ("UNS", r"^UNS\b"),
    ("AWS", r"^AWS\b"),
]


def naming_source(name: str) -> str:
    """Standard body that issued the designation; trade/generic names map to 'Other'."""
    for src, pattern in _NAMING_SOURCE_RULES:
        if re.search(pattern, name):
            return src
    return "Other"


_EN_CAST_DESIGNATION = re.compile(r"^EN[\s-]1\.\d{4}[\s-]\(?G[A-Z0-9]", re.IGNORECASE)


def product_form(name: str, family: str) -> str:
    """'weld' for weld metals, 'cast' for cast irons / cast steels, otherwise 'wrought'."""
    if family == "weld_metal":
        return "weld"
    if family.startswith("cast_iron") or re.search(r"\bcast(ing)?\b", name, re.IGNORECASE):
        return "cast"
    if name.upper().startswith("ACI") or _EN_CAST_DESIGNATION.search(name):
        return "cast"
    return "wrought"


_CONDITION_RULES = [
    ("aged", r"^aged\b"),
    ("annealed", r"^annealed\b"),
    ("full_hard", r"^full[\s-]hard\b"),
    ("precipitation_hardened", r"^H\d{3,4}\s+hardened"),
    ("austempered", r"austempered"),
    ("oil_tempered", r"oil[\s-]tempered"),
]


def condition_in_name(name: str) -> str:
    """Heat-treatment state stated in the grade name ('none' for almost every grade)."""
    for cond, pattern in _CONDITION_RULES:
        if re.search(pattern, name, re.IGNORECASE):
            return cond
    return "none"


# --------------------------------------------------------------------------------------------
# Composition-derived metallurgical indices
# --------------------------------------------------------------------------------------------
def composition_features(df: pd.DataFrame) -> pd.DataFrame:
    """Alloying total, IIW carbon equivalent, Cr+Ni and Schaeffler equivalents."""
    out = pd.DataFrame(index=df.index)
    out["comp_sum"] = df[ELEMENTS].sum(axis=1)
    out["alloying_total"] = 100.0 - df["Fe"]
    # IIW carbon equivalent (weldability / hardenability index)
    out["carbon_equivalent"] = (
        df["C"] + df["Mn"] / 6 + (df["Cr"] + df["Mo"] + df["V"]) / 5 + (df["Ni"] + df["Cu"]) / 15
    )
    out["cr_plus_ni"] = df["Cr"] + df["Ni"]
    # Schaeffler diagram equivalents (stainless microstructure map)
    out["cr_eq"] = df["Cr"] + df["Mo"] + 1.5 * df["Si"] + 0.5 * df["Nb"]
    out["ni_eq"] = df["Ni"] + 30 * df["C"] + 0.5 * df["Mn"]
    out["is_stainless_comp"] = df["Cr"] >= STAINLESS_MIN_CR
    return out


def rare_elements(df: pd.DataFrame, min_rows: int) -> list[str]:
    """Elements that are non-zero in fewer than `min_rows` rows."""
    nonzero = (df[ELEMENTS] > 0).sum()
    return sorted(nonzero[nonzero < min_rows].index.tolist())


def composition_group_ids(df: pd.DataFrame) -> pd.Series:
    """Stable id per distinct composition (rounded to 1e-6 wt%), numbered by first appearance
    after sorting on the element vector so the ids do not depend on input row order."""
    comp = df[ELEMENTS].round(6)
    key = comp.apply(lambda r: tuple(r.values), axis=1)
    ordered = sorted(set(key))
    lookup = {k: f"CG{i + 1:04d}" for i, k in enumerate(ordered)}
    return key.map(lookup)
