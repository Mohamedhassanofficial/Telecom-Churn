# Telecom Customer Churn — Production Pipeline

End-to-end Airflow pipeline that converts the original Jupyter notebooks
into reusable Python modules and orchestrates them as a DAG, feeding the
existing Streamlit dashboard.

## Pipeline

```
sample_expresso ─┐
                 ├─→ build_telecom_churn ─→ run_eda ─┐
build_opencellid ┘                                    ├─→ train_model ─→ predict
                                                     ┘
```

| Step | Script                                | Source notebook                                                                           |
|------|---------------------------------------|-------------------------------------------------------------------------------------------|
| 0    | `scripts/00_download_raw.py` (opt.)   | —                                                                                         |
| 1    | `scripts/01_generate_expresso_sample.py` | `notebooks/generate_expresso_sample_100k.ipynb`                                        |
| 2    | `scripts/02_build_opencellid_senegal.py` | `notebooks/build_opencellid_senegal_90d_dataset.ipynb`                                |
| 3    | `scripts/03_build_telecom_churn.py`   | `notebooks/build_telecom_churn_dataset.ipynb`                                             |
| 4    | `scripts/04_run_eda.py`               | `notebooks/Telecom Customer Churn - Exploratory Data Analysis (EDA) - Project Team A.ipynb` |
| 5    | `scripts/05_train_model.py`           | `notebooks/Telecom Customer Churn - Training, Inference & Evaluation - Project Team A.ipynb` (training cells) |
| 6    | `scripts/06_predict.py`               | same notebook (inference cells)                                                           |

## Project layout

```
dags/churn_pipeline.py        # Airflow DAG (PythonOperator × 6)
scripts/                       # Thin CLI wrappers (one per step)
src/                           # Shared library — imported by DAG and scripts
  paths.py                     # CHURN_BASE_DIR-driven path helpers
  config.py                    # YAML-loaded constants (MCC, hyperparams, threshold)
  sampling.py / geo.py / ...
config/config.yaml             # All non-path configuration
outputs/                       # EDA plots, metrics, predictions (DAG output)
models/                        # Trained models — churn_model.joblib is the dashboard contract
dashboards/                    # Streamlit app (untouched)
requirements-pipeline.txt
Dockerfile.airflow
docker-compose.yaml
```

## Quickstart — Docker

```bash
# 1) Set the env file
cp .env.example .env

# 2) Build the custom Airflow image (~5 min on first build)
docker compose build

# 3) One-off DB init
docker compose up airflow-init

# 4) Run scheduler + webserver + Streamlit
docker compose up
```

Services:
* Airflow UI: <http://localhost:8080> (airflow / airflow)
* Streamlit:  <http://localhost:8501>

## Quickstart — local Windows

```powershell
# Inside an activated Python 3.11 venv:
pip install -r requirements-pipeline.txt
pip install -r dashboards/requirements.txt

# Tell the code where the project lives
$env:CHURN_BASE_DIR = "C:\Users\Lenovo\Downloads\04_requirements"

# Run any single step end-to-end
python scripts/01_generate_expresso_sample.py
python scripts/02_build_opencellid_senegal.py
python scripts/03_build_telecom_churn.py
python scripts/04_run_eda.py
python scripts/05_train_model.py --no-shap
python scripts/06_predict.py

# Launch the dashboard
streamlit run dashboards/churn_dashboard_app.py
```

## Configuration

| Setting               | Where                          | Default                                      |
|-----------------------|--------------------------------|----------------------------------------------|
| Project root          | env `CHURN_BASE_DIR`           | parent of `src/`                             |
| Use full dataset      | Airflow Variable `USE_FULL_DATASET` | `false` (uses 100k sample)              |
| MCC / MNC / window    | `config/config.yaml`           | 608 / 3 / 2019-04-01..2019-07-01             |
| Classification thr.   | `config/config.yaml` + model metadata | 0.42 (auto-tuned during training)     |

## Verification

```bash
# Static checks
python -m compileall scripts src dags
python -c "from src import paths, modeling, geo, eda, inference, sampling, network_kpis, feature_engineering"

# Each script in isolation
python scripts/04_run_eda.py --input datasets/telecom_churn/telecom_churn_100k.csv --output-dir /tmp/eda

# DAG parse + dry run
airflow dags list
airflow dags test telecom_churn_production_pipeline 2026-05-06
```

## Notes

* The dashboard's joblib contract is `{"model": ..., "metadata": {"threshold": float, ...}}`.
  `src/modeling.py` writes that schema; do not change it without updating
  `dashboards/churn_dashboard_app.py`.
* `dashboards/requirements.txt` pins `pandas==3.0.2` and `numpy==2.4.4` —
  those versions don't exist on PyPI. Align them with
  `requirements-pipeline.txt` when re-installing.
* The five existing notebooks remain untouched in `notebooks/` for reference.

---

## Milestone 3 — Verification & deployment summary

### DAG ↔ Notebook output parity

Both the Airflow DAG and the local notebook-derived run drive the same
`src/` library (sampling → geo → modeling → inference), so the produced
`outputs/predictions/churn_predictions.csv` is **bit-identical** when the
same input and same seed are used:

```
$ python scripts/compare_dag_vs_notebook.py
============================================================
DAG CSV:      outputs/predictions/churn_predictions.csv  (md5 d8abfb0c)
Baseline:     outputs/predictions/churn_predictions_notebook.csv  (md5 d8abfb0c)
Rows:         dag=100000  baseline=100000
------------------------------------------------------------
  row_count_match: True
  column_set_match: True
  user_id_set_match: True
  user_id_overlap_pct: 100.0
  churn_prediction_agreement: 1.0
  churn_probability_mean_abs_delta: 0.0
  risk_segment_max_delta: 0.0
------------------------------------------------------------
OVERALL: PASS
```

The detailed JSON report lives at `outputs/dag_vs_notebook_comparison.json`.

To re-run the same check after a fresh DAG run:

```bash
python scripts/compare_dag_vs_notebook.py \
    --dag-csv     outputs/predictions/churn_predictions.csv \
    --baseline    outputs/predictions/churn_predictions_notebook.csv \
    --output-json outputs/dag_vs_notebook_comparison.json
```

### Streamlit Cloud deployment

The dashboard is deployable to **share.streamlit.io** on the free tier
(repo is public).

1. Sign in at https://share.streamlit.io with the GitHub account that
   owns this repo.
2. Click "Create app" → pick `Mohamedhassanofficial/Telecom-Churn`.
3. Main file: `streamlit_app.py` (root-level shim that re-execs
   `dashboards/churn_dashboard_app.py`).
4. Python version: 3.11.
5. (Optional) In the Secrets editor paste the contents of
   `dashboards/.streamlit/secrets.toml.example`.
6. Click Deploy. First build takes 5-7 min.

Once live, the URL is `https://<your-slug>.streamlit.app/` and reads the
same `outputs/predictions/churn_predictions.csv` baked into the repo —
so it matches the local Streamlit (port 8501) and the Azure Streamlit
(`telechurn-streamlit.*.azurecontainerapps.io`) byte-for-byte.

### Notification DAG (`dags/notify_on_new_data.py`)

Demonstrates the Milestone 3 "Notification عند وصول بيانات جديدة" bullet.

* `FileSensor` polls `datasets/incoming/*.csv` every 10 min (mode=`reschedule`).
* When a file lands, `report_files` task logs the arrival (file names + sizes).
* `EmailOperator` fires next — if Airflow's `[smtp]` section is configured
  it sends a real email; otherwise the scheduler logs "smtp not configured"
  and the DAG run still succeeds.

To enable real email sending, add to `airflow.cfg` (or set the equivalent
env vars on the scheduler container):

```ini
[smtp]
smtp_host = smtp.gmail.com
smtp_starttls = True
smtp_ssl = False
smtp_user = your-bot@gmail.com
smtp_password = <app-password>
smtp_port = 587
smtp_mail_from = your-bot@gmail.com
```

To override the recipient, set `CHURN_NOTIFY_EMAIL` on the scheduler.

To exercise the DAG manually:

```bash
mkdir -p datasets/incoming
cp datasets/expresso/expresso_sample_100k.csv datasets/incoming/new_batch.csv
docker compose exec -T airflow-scheduler \
    airflow dags unpause notify_on_new_data
docker compose exec -T airflow-scheduler \
    airflow dags trigger notify_on_new_data
```

### Live deployments

| Surface | URL | Status |
|---|---|---|
| Local Streamlit | http://localhost:8501 | ✅ |
| Azure Streamlit | https://telechurn-streamlit.thankfulsand-f5821563.eastus.azurecontainerapps.io | ✅ |
| Azure Flask REST API | https://telechurn-flask.thankfulsand-f5821563.eastus.azurecontainerapps.io | ✅ |
| Azure Flask Swagger UI | https://telechurn-flask.thankfulsand-f5821563.eastus.azurecontainerapps.io/ | ✅ |
| Streamlit Cloud | (deploy via the steps above) | manual |
| GitHub repo (public) | https://github.com/Mohamedhassanofficial/Telecom-Churn | ✅ public |
