"""CLI entrypoint: run headless EDA and write plots + JSON summary.

Wraps :func:`src.eda.run_eda`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from src import eda, paths


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=paths.TELECOM_CHURN_100K,
                   help="Path to telecom_churn_100k.csv")
    p.add_argument("--output-dir", type=Path, default=paths.EDA_DIR,
                   help="Directory to write EDA artefacts into")
    args = p.parse_args()

    eda.run_eda(input_path=args.input, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
