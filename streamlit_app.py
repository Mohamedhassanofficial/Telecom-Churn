"""PHASE 2.1 probe -- data + viz stack.

Proves on Streamlit Cloud that pandas + numpy + plotly + scikit-learn +
joblib all install and that the committed predictions CSV is readable.

If you see the histogram + the green "Phase 2.1 OK" badge in the
browser, this layer is healthy and we move on to Phase 2.2 (heavy ML
stack: lightgbm + category_encoders + imbalanced-learn + dill).

If you see an error message instead of "Oh no", the probe caught the
exception and shows it verbatim -- read it and fix in requirements.txt.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

st.set_page_config(
    page_title="Telecom Churn -- Phase 2.1 probe",
    page_icon="2",
    layout="wide",
)

st.title("Phase 2.1 probe -- data + viz stack")
st.caption(
    "Tests that pandas + numpy + plotly + scikit-learn + joblib all "
    "install on Streamlit Cloud and that the committed predictions CSV "
    "is readable."
)

# ---------------------------------------------------------------------------
# Import probe -- surface ANY missing module verbatim instead of "Oh no"
# ---------------------------------------------------------------------------
_failures: list[str] = []
for mod in ["pandas", "numpy", "joblib", "plotly.express", "sklearn"]:
    try:
        __import__(mod)
    except Exception as exc:
        _failures.append(f"{mod}: {type(exc).__name__}: {exc}")

if _failures:
    st.error("Some dependencies failed to import:")
    st.code("\n".join(_failures), language="text")
    st.stop()

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402

# ---------------------------------------------------------------------------
# CSV probe
# ---------------------------------------------------------------------------
csv_path = _ROOT / "outputs" / "predictions" / "churn_predictions_notebook.csv"
st.write(f"**Looking for predictions at:** `{csv_path.relative_to(_ROOT)}`")
st.write(f"**File exists:** {csv_path.exists()}")

if not csv_path.exists():
    st.error(f"Predictions CSV not found at {csv_path}")
    st.stop()

try:
    df = pd.read_csv(csv_path)
except Exception:
    st.error("pandas.read_csv raised an exception:")
    st.code(traceback.format_exc(), language="text")
    st.stop()

st.success(f"Loaded {len(df):,} rows x {len(df.columns)} columns")

col1, col2, col3 = st.columns(3)
col1.metric("Total customers", f"{len(df):,}")
col2.metric("Predicted churn", f"{int(df['churn_prediction'].sum()):,}")
col3.metric("Mean P(churn)", f"{df['churn_probability'].mean():.2%}")

# ---------------------------------------------------------------------------
# Plotly probe -- render one chart end-to-end
# ---------------------------------------------------------------------------
st.subheader("Churn-probability distribution (plotly histogram)")
try:
    fig = px.histogram(df, x="churn_probability", nbins=40,
                       title="Phase 2.1 -- plotly works")
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.error("plotly histogram raised an exception:")
    st.code(traceback.format_exc(), language="text")
    st.stop()

st.subheader("First 10 predictions")
st.dataframe(df.head(10), use_container_width=True)

st.success("Phase 2.1 OK -- pandas + numpy + plotly + sklearn + joblib all working")
st.caption(
    "Next: Phase 2.2 adds lightgbm + category_encoders + imbalanced-learn "
    "+ dill and tests joblib.load() of the trained model."
)
