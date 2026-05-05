"""CLI entrypoint: train + calibrate the LightGBM churn pipeline.

Wraps :func:`src.modeling.train`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from src import modeling, paths


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=paths.TELECOM_CHURN_100K,
                   help="Training dataset CSV")
    p.add_argument("--model-dir", type=Path, default=paths.MODELS_DIR)
    p.add_argument("--metrics-dir", type=Path, default=paths.METRICS_DIR)
    p.add_argument("--no-shap", action="store_true",
                   help="Skip the SHAP explainability step (faster).")
    args = p.parse_args()

    modeling.train(
        input_path=args.input,
        model_dir=args.model_dir,
        metrics_dir=args.metrics_dir,
        run_shap=not args.no_shap,
    )


if __name__ == "__main__":
    main()
