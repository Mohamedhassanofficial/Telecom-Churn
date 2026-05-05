"""Telecom Customer Churn — full production DAG (TaskFlow API).

Task graph
----------

    sample_expresso ─┐
                     ├─→ build_telecom_churn ─→ run_eda ─┐
    build_opencellid ┘                                    ├─→ train_model ─→ predict
                                                         ┘

Each task uses Airflow 2.x's @task decorator (TaskFlow API), which
gives:

* Automatic XCom for return values
* Type hints visible in the UI
* Cleaner Python (no PythonOperator boilerplate)

The tasks delegate to ``src/`` modules so the same code runs in CLI,
CI, and Airflow.

Configuration
-------------
* ``CHURN_BASE_DIR``     — env var. Project root. Resolved by ``src.paths``.
* ``USE_FULL_DATASET``   — Airflow Variable. ``"true"`` to train on the
                           full ``telecom_churn.csv`` instead of the 100k sample.
* ``CHURN_FORCE_REBUILD`` — env var. ``"1"`` to bypass idempotency caching.

The Streamlit dashboard runs as a separate service (see
docker-compose.yaml). The DAG's last task (``predict``) refreshes the
prediction CSV and the dashboard reads it on next page load.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable

# ---------------------------------------------------------------------------
# Make the project's ``src`` package importable from the DAG.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(
    os.environ.get("CHURN_BASE_DIR", Path(__file__).resolve().parents[1])
)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# DAG default args
# ---------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "data-team",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


@dag(
    dag_id="telecom_churn_production_pipeline",
    description=(
        "OpenCellID + Expresso → telecom_churn dataset → EDA → ML → "
        "predictions consumed by the Streamlit dashboard."
    ),
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 5, 1),
    schedule=None,                 # manual trigger; switch to "@weekly" once stable
    catchup=False,
    max_active_runs=1,
    tags=["churn", "telecom", "ml"],
    doc_md=__doc__,
)
def telecom_churn_pipeline():
    """TaskFlow DAG for the Telecom Customer Churn pipeline."""

    # -----------------------------------------------------------------------
    # Helper resolvers (lazy — imported inside tasks to avoid heavy imports
    # at DAG-parse time)
    # -----------------------------------------------------------------------
    def _use_full_dataset() -> bool:
        return str(Variable.get("USE_FULL_DATASET", default_var="false")).lower() == "true"

    # -----------------------------------------------------------------------
    # Task 1 — sample expresso
    # -----------------------------------------------------------------------
    @task(
        task_id="sample_expresso",
        execution_timeout=timedelta(minutes=30),
        retries=2,
    )
    def sample_expresso() -> str:
        """Stratified sample of expresso.csv → expresso_sample_100k.csv."""
        from src import idempotency, paths, sampling, validation

        @idempotency.skip_if_fresh(
            outputs=[paths.EXPRESSO_SAMPLE], max_age_hours=24 * 7,
        )
        def _run():
            out = sampling.run(
                input_path=paths.EXPRESSO_RAW,
                output_path=paths.EXPRESSO_SAMPLE,
            )
            validation.validate_csv(out, validation.EXPRESSO_SAMPLE)
            return out

        return str(_run() or paths.EXPRESSO_SAMPLE)

    # -----------------------------------------------------------------------
    # Task 2 — build OpenCellID Senegal
    # -----------------------------------------------------------------------
    @task(
        task_id="build_opencellid",
        execution_timeout=timedelta(hours=2),
        retries=2,
    )
    def build_opencellid() -> str:
        """Filter Africa_towers.csv to Senegal/Expresso (90-day window)."""
        from src import geo, idempotency, paths, validation

        @idempotency.skip_if_fresh(
            outputs=[paths.OPENCELLID_SENEGAL], max_age_hours=24 * 30,
        )
        def _run():
            out = geo.build_senegal_cells(
                input_path=paths.OPENCELLID_RAW,
                output_path=paths.OPENCELLID_SENEGAL,
            )
            validation.validate_csv(out, validation.OPENCELLID_SENEGAL)
            return out

        return str(_run() or paths.OPENCELLID_SENEGAL)

    # -----------------------------------------------------------------------
    # Task 3 — build telecom_churn
    # -----------------------------------------------------------------------
    @task(
        task_id="build_telecom_churn",
        execution_timeout=timedelta(hours=1),
        retries=1,
    )
    def build_telecom_churn(expresso_path: str, cells_path: str) -> dict[str, str]:
        """Spatial-join cells to GADM admin levels, merge with Expresso."""
        from src import geo, idempotency, paths, validation

        @idempotency.skip_if_fresh(
            outputs=[paths.TELECOM_CHURN_FULL, paths.TELECOM_CHURN_100K],
            max_age_hours=24 * 7,
        )
        def _run():
            out_full, out_100k = geo.build_telecom_churn(
                cells_path=Path(cells_path),
                expresso_path=Path(expresso_path),
                gadm_path=paths.GADM_GPKG,
                out_full=paths.TELECOM_CHURN_FULL,
                out_100k=paths.TELECOM_CHURN_100K,
            )
            validation.validate_csv(out_100k, validation.TELECOM_CHURN)
            return out_full, out_100k

        result = _run()
        if result is None:
            return {
                "full":   str(paths.TELECOM_CHURN_FULL),
                "sample": str(paths.TELECOM_CHURN_100K),
            }
        full, sample = result
        return {"full": str(full), "sample": str(sample)}

    # -----------------------------------------------------------------------
    # Task 4 — EDA
    # -----------------------------------------------------------------------
    @task(
        task_id="run_eda",
        execution_timeout=timedelta(minutes=30),
        retries=1,
    )
    def run_eda(telecom_paths: dict[str, str]) -> str:
        """Headless EDA report → outputs/eda/."""
        from src import eda, paths
        eda.run_eda(
            input_path=Path(telecom_paths["full"] if _use_full_dataset()
                            else telecom_paths["sample"]),
            output_dir=paths.EDA_DIR,
        )
        return str(paths.EDA_DIR)

    # -----------------------------------------------------------------------
    # Task 5 — train
    # -----------------------------------------------------------------------
    @task(
        task_id="train_model",
        execution_timeout=timedelta(hours=1),
        retries=1,
    )
    def train_model(telecom_paths: dict[str, str]) -> dict:
        """Train + calibrate LightGBM, write model + metrics."""
        from src import modeling, paths
        return modeling.train(
            input_path=Path(telecom_paths["full"] if _use_full_dataset()
                            else telecom_paths["sample"]),
            model_dir=paths.MODELS_DIR,
            metrics_dir=paths.METRICS_DIR,
            run_shap=True,
        )

    # -----------------------------------------------------------------------
    # Task 6 — predict
    # -----------------------------------------------------------------------
    @task(
        task_id="predict",
        execution_timeout=timedelta(minutes=30),
        retries=1,
    )
    def predict(train_result: dict, telecom_paths: dict[str, str]) -> str:
        """Batch inference → churn_predictions.csv (dashboard input)."""
        from src import inference, paths, validation
        out = inference.predict(
            model_path=Path(train_result["model_path"]),
            input_path=Path(telecom_paths["full"] if _use_full_dataset()
                            else telecom_paths["sample"]),
            output_path=paths.PREDICTIONS_CSV,
        )
        validation.validate_csv(out, validation.CHURN_PREDICTIONS)
        return str(out)

    # -----------------------------------------------------------------------
    # Wire the graph
    # -----------------------------------------------------------------------
    expresso_out = sample_expresso()
    cells_out = build_opencellid()
    telecom_paths = build_telecom_churn(expresso_out, cells_out)
    eda_out = run_eda(telecom_paths)
    train_result = train_model(telecom_paths)

    # ``run_eda`` is a quality gate but doesn't gate training. Keep both as
    # downstream of telecom_paths; force training to wait until EDA finishes
    # so EDA artefacts are ready before the dashboard refresh.
    eda_out >> train_result

    predict(train_result, telecom_paths)


telecom_churn_pipeline()
