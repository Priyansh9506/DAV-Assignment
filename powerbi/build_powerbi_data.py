"""Build the Power BI star schema from the cleaned dataset.

Reads  data/processed/steels_clean.csv   (written by notebooks/01_cleaning.ipynb)
Writes powerbi/data/grades.csv           fact table: one row per canonical grade (1,389)
       powerbi/data/composition.csv      one row per (grade, element present) with wt%
       powerbi/data/families.csv         dimension: 17 families -> 6 family groups, sort order, colour
       powerbi/data/elements.csv         dimension: 30 elements with full names and a rare-element flag

Run from the project root:  python powerbi/build_powerbi_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "steels_clean.csv"
META = ROOT / "data" / "processed" / "pipeline_meta.json"
OUT = ROOT / "powerbi" / "data"

ELEMENTS = {
    "Al": "Aluminium", "As": "Arsenic", "B": "Boron", "C": "Carbon", "Ca": "Calcium", "Ce": "Cerium", "Co": "Cobalt",
    "Cr": "Chromium", "Cu": "Copper", "Fe": "Iron", "La": "Lanthanum", "Mg": "Magnesium", "Mn": "Manganese",
    "Mo": "Molybdenum", "N": "Nitrogen", "Nb": "Niobium", "Ni": "Nickel", "O": "Oxygen", "P": "Phosphorus",
    "Pb": "Lead", "S": "Sulphur", "Se": "Selenium", "Si": "Silicon", "Sn": "Tin", "Ta": "Tantalum", "Ti": "Titanium",
    "V": "Vanadium", "W": "Tungsten", "Zn": "Zinc", "Zr": "Zirconium",
}
# Same six groups and colours as the web app (light theme) and the KNIME Rule Engine.
GROUPS = [
    ("Carbon & low-alloy", "#2a78d6"), ("Stainless", "#eb6834"), ("Cast iron", "#1baf7a"),
    ("Tool & high-speed", "#eda100"), ("Weld metal", "#e87ba4"), ("Other", "#008300"),
]
GROUP_OF_FAMILY = {
    **{f: "Carbon & low-alloy" for f in ["carbon", "alloy", "boron", "spring", "bearing", "nitriding", "weathering"]},
    "stainless": "Stainless", "tool": "Tool & high-speed", "high_speed": "Tool & high-speed", "weld_metal": "Weld metal",
}
CLASS_LABEL = {0: "Low (< 300 MPa)", 1: "Medium (300-600 MPa)", 2: "High (> 600 MPa)"}


def family_group(family: str) -> str:
    if family in GROUP_OF_FAMILY:
        return GROUP_OF_FAMILY[family]
    return "Cast iron" if family.startswith("cast_iron") else "Other"


def ce_band(row: pd.Series) -> str:
    if row["family_group"] != "Carbon & low-alloy":
        return "Not applicable"
    ce = row["carbon_equivalent"]
    return "Readily weldable (CE <= 0.40)" if ce <= 0.40 else "Preheat advised (0.40-0.60)" if ce <= 0.60 else "Difficult (CE > 0.60)"


def main() -> None:
    g = pd.read_csv(SRC)
    rare = json.loads(META.read_text())["rare_elements"]
    g["family_group"] = g["family"].map(family_group)

    # PCA in the same composition space as notebook 03 and the web app (log1p, z-score, 20 features).
    feats = [el for el in ELEMENTS if el not in rare and el != "Fe"] + ["trace_total"]
    T = np.log1p(g[feats].to_numpy(dtype=float))
    sd = T.std(axis=0)
    X = (T - T.mean(axis=0)) / np.where(sd > 0, sd, 1.0)
    scores = PCA(random_state=42).fit(X).transform(X)[:, :2]

    grades = pd.DataFrame({
        "grade_id": g["grade_id"],
        "grade_name": g["display_name"],
        "family": g["family"],
        "product_form": g["product_form"],
        "designation_standard": g["naming_source"],
        "tensile_strength_mpa": g["tensile_strength_mpa"],
        "has_measured_strength": g["tensile_strength_mpa"].notna(),
        "strength_class": g["strength_class"].map(CLASS_LABEL),
        "strength_class_order": g["strength_class"],
        "liquidus_c": g["liquidus_c"],
        "liquidus_is_placeholder": g["liquidus_is_default"],
        "carbon_equivalent": g["carbon_equivalent"].round(4),
        "alloying_total_wt": g["alloying_total"].round(4),
        "cr_equivalent": g["cr_eq"].round(4),
        "ni_equivalent": g["ni_eq"].round(4),
        "carbon_wt": g["C"],
        "chromium_wt": g["Cr"],
        "nickel_wt": g["Ni"],
        "molybdenum_wt": g["Mo"],
        "pc1": scores[:, 0].round(4),
        "pc2": scores[:, 1].round(4),
    })
    grades["weldability_band"] = pd.concat([g["family_group"], g["carbon_equivalent"]], axis=1).apply(ce_band, axis=1)

    composition = (
        g.melt(id_vars="grade_id", value_vars=list(ELEMENTS), var_name="element", value_name="wt_pct")
        .query("wt_pct > 0")
        .sort_values(["grade_id", "element"])
    )

    group_order = {name: i + 1 for i, (name, _) in enumerate(GROUPS)}
    group_color = dict(GROUPS)
    families = (
        g[["family", "family_label", "family_group"]].drop_duplicates().assign(
            group_order=lambda d: d["family_group"].map(group_order),
            group_color=lambda d: d["family_group"].map(group_color),
        ).sort_values(["group_order", "family_label"])
    )
    elements = pd.DataFrame({
        "element": list(ELEMENTS), "element_name": list(ELEMENTS.values()),
        "is_rare_trace": [el in rare for el in ELEMENTS],
    })

    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in {"grades": grades, "composition": composition, "families": families, "elements": elements}.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name}.csv: {len(df)} rows x {df.shape[1]} columns")


if __name__ == "__main__":
    main()
