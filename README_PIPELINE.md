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
