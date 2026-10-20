"""End-to-end pipeline without notebooks: clean -> Tableau / KNIME exports.

    python -m src.analysis.pipeline
"""
from __future__ import annotations

import logging

from . import cleaning, exports, viz_exports


def run() -> None:
    result = cleaning.run_cleaning()
    cleaning.save_outputs(result)
    exports.build_all()
    viz_exports.save(viz_exports.build_viz_exports())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()


if __name__ == "__main__":
    main()
