"""Pins the verified facts about data/raw/Alloys.csv so a pipeline change cannot silently alter them."""
import pytest

from src.analysis.cleaning import run_cleaning
from src.analysis.constants import DATA_RAW
from src.analysis.quality import irreducible_error

pytestmark = pytest.mark.skipif(not DATA_RAW.exists(), reason="raw dataset not present")


@pytest.fixture(scope="module")
def result():
    return run_cleaning()


def test_known_row_counts(result):
    log = result.log
    assert log.get("load_raw").rows_after == 2672
    assert log.get("drop_exact_duplicates").rows_after == 2610
    assert log.get("flag_imputed_ts").metrics["n_imputed"] == 469
    assert log.get("add_canonical_grade").metrics["n_canonical"] == 1389
    assert log.get("collapse_to_grades").metrics["n_recovered_from_twin"] == 459
    assert log.get("collapse_to_grades").metrics["n_grades_without_measured_ts"] == 7


def test_composition_groups(result):
    m = result.log.get("audit_processing_variants").metrics
    assert m["n_compositions"] == 1299
    assert m["groups_multi_ts_listing_level"] == 476
    assert m["groups_multi_ts_measured_only"] == 28
    assert result.grades["composition_group_id"].nunique() == 1299


def test_class_recompute_matches_original(result):
    assert result.log.get("recompute_strength_class").metrics["agreement_on_measured_listings"] == 1.0


def test_every_grade_has_family_and_no_unexpected_nulls(result):
    g = result.grades
    assert g["family"].notna().all()
    assert g["tensile_strength_mpa"].isna().sum() == g["is_imputed_ts"].sum() == 7
    assert (g["liquidus_is_default"] == (g["liquidus_c"] == 1460)).all()


def test_irreducible_error_is_bounded(result):
    ie = irreducible_error(result.grades)
    assert 0.9 < ie.oracle_r2 < 1.0
    assert ie.groups_with_spread == 28
