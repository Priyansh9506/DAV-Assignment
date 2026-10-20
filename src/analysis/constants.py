"""Paths and domain constants shared by every analysis module."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = ROOT / "data" / "raw" / "Alloys.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
CLEAN_GRADES_CSV = DATA_PROCESSED / "steels_clean.csv"
CLEAN_LISTINGS_CSV = DATA_PROCESSED / "steels_listings.csv"
DATA_DICTIONARY_MD = DATA_PROCESSED / "DATA_DICTIONARY.md"
PIPELINE_META_JSON = DATA_PROCESSED / "pipeline_meta.json"

REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
CLEANING_LOG_MD = REPORTS / "cleaning_log.md"
CLEANING_LOG_JSON = REPORTS / "cleaning_log.json"

EXPORTS_TABLEAU = ROOT / "exports" / "tableau"
EXPORTS_KNIME = ROOT / "exports" / "knime"

RANDOM_STATE = 42

# Raw column names
RAW_NAME = "Alloy"
RAW_TS = "Tensile Strength"
RAW_LIQUIDUS = "Melting Completion (Liquidus)"
RAW_CLASS = "Class"

ELEMENTS = [
    "Al", "As", "B", "C", "Ca", "Ce", "Co", "Cr", "Cu", "Fe", "La", "Mg", "Mn", "Mo", "N",
    "Nb", "Ni", "O", "P", "Pb", "S", "Se", "Si", "Sn", "Ta", "Ti", "V", "W", "Zn", "Zr",
]

# Tensile strength equal to the raw column mean marks a mean-imputed value, not a measurement.
IMPUTED_TS_VALUE = 652.482978
IMPUTED_TS_TOL = 1e-4

# Liquidus value that the source assigns as a family-typical default (see 01_cleaning).
DEFAULT_LIQUIDUS_C = 1460

# Elements non-zero in fewer than this many de-duplicated rows are summed into `trace_total`.
RARE_ELEMENT_MIN_ROWS = 30

# Strength-class bins reproduce the original `Class` column: 0 = 140-290, 1 = 300-600, 2 = 610-2450 MPa.
STRENGTH_CLASS_EDGES = (300.0, 600.0)
STRENGTH_CLASS_LABELS = {0: "Low (<300 MPa)", 1: "Medium (300-600 MPa)", 2: "High (>600 MPa)"}

# Thresholds above which EN 10020 classes a steel as alloyed (wt%). Used only as a fallback
# for grades whose name does not state a family.
EN10020_ALLOY_LIMITS = {
    "Al": 0.30, "B": 0.0008, "Co": 0.30, "Cr": 0.30, "Cu": 0.40, "Mn": 1.65, "Mo": 0.08,
    "Nb": 0.06, "Ni": 0.30, "Pb": 0.40, "Se": 0.10, "Si": 0.60, "Ti": 0.05, "V": 0.10,
    "W": 0.30, "Zr": 0.05,
}
STAINLESS_MIN_CR = 10.5
