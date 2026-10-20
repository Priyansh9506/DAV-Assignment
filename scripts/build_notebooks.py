"""Build and execute the project notebooks.

    python scripts/build_notebooks.py            # all notebooks
    python scripts/build_notebooks.py 01 04      # selected notebooks

Notebooks only orchestrate and display: all logic lives in src/analysis. Each notebook is
regenerated from the cell lists below and executed top to bottom with nbclient, so the saved
outputs always correspond to the current code and data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
sys.path.insert(0, str(ROOT / "scripts"))

from notebook_cells import NOTEBOOKS  # noqa: E402


def build(key: str) -> Path:
    name, cells = NOTEBOOKS[key]
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    for kind, src in cells:
        src = src.strip("\n")
        nb.cells.append(nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src))
    client = NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": str(NB_DIR)}})
    client.execute()
    path = NB_DIR / name
    nbformat.write(nb, path)
    print(f"built + executed {path.relative_to(ROOT)}")
    return path


if __name__ == "__main__":
    keys = sys.argv[1:] or list(NOTEBOOKS)
    for k in keys:
        build(k)
