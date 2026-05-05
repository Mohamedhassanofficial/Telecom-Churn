"""CLI entrypoint: batch-score a CSV with the saved churn model.

Wraps :func:`src.inference.predict`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from src import inference, paths


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, default=paths.CHURN_MODEL_JOBLIB,
                   help="Path to churn_model.joblib")
    p.add_argument("--input", type=Path, default=paths.TELECOM_CHURN_100K,
                   help="CSV to score")
    p.add_argument("--output", type=Path, default=paths.PREDICTIONS_CSV,
                   help="Destination CSV (read by Streamlit dashboard)")
    p.add_argument("--threshold", type=float, default=None,
                   help="Override the threshold from model metadata")
    args = p.parse_args()

    inference.predict(
        model_path=args.model,
        input_path=args.input,
        output_path=args.output,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
