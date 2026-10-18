"""End-to-end pipeline without notebooks: clean -> evaluate + train -> exports.

    python -m src.analysis.pipeline            # everything (~10 min, includes nested tuning)
    python -m src.analysis.pipeline --fast     # skip nested tuning and UMAP
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from . import cleaning, evaluation, exports, train
from .constants import CLEAN_LISTINGS_CSV


def run(fast: bool = False) -> None:
    result = cleaning.run_cleaning()
    cleaning.save_outputs(result)
    grades = cleaning.load_clean_grades()
    rare = cleaning.load_pipeline_meta()["rare_elements"]
    ev = evaluation.run_evaluation(grades, pd.read_csv(CLEAN_LISTINGS_CSV), rare, with_tuned=not fast, with_umap=not fast)
    evaluation.save_evaluation(ev)
    train.train_and_save(grades, rare, ev)
    exports.build_all()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fast", action="store_true", help="skip nested GBM tuning and UMAP")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(fast=args.fast)


if __name__ == "__main__":
    main()
