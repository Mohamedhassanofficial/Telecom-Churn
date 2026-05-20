"""Minimal Streamlit Cloud probe — temporary diagnostic.

The full dashboard at dashboards/churn_dashboard_app.py keeps hitting the
generic "Oh no" page on Streamlit Cloud without any visible traceback.
This file replaces the full app temporarily with a 20-line minimum that
exercises only the data path — no model loading, no plotly, no Streamlit
caching. If THIS works, the dashboard code (or the joblib unpickle) is
the issue; restore from streamlit_app_full.py and bisect from there.

To restore the full dashboard:
    cp streamlit_app_full.py streamlit_app.py && git add streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Resolve paths regardless of cwd
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

st.set_page_config(
    page_title="Telecom Churn — minimal probe",
    page_icon="🩺",
    layout="wide",
)

st.title("🩺 Telecom Churn — minimal probe")
st.caption(
    "If you see this page, Streamlit Cloud + the Python env + the data "
    "files are all working. The full dashboard issue is elsewhere."
)

# Show env info so we can diagnose
with st.expander("Environment details (debug)", expanded=False):
    import platform
    st.write({
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repo_root": str(_ROOT),
        "repo_root_contents": sorted([p.name for p in _ROOT.iterdir()
                                       if not p.name.startswith(".")])[:20],
    })

# Try to load the canonical predictions CSV that ships in the repo
csv_path = _ROOT / "outputs" / "predictions" / "churn_predictions_notebook.csv"
st.write(f"**Looking for predictions at:** `{csv_path}`")
st.write(f"**File exists:** {csv_path.exists()}")

if not csv_path.exists():
    st.error(f"Predictions CSV not found at {csv_path}")
    st.stop()

try:
    df = pd.read_csv(csv_path)
except Exception as exc:
    st.error(f"Failed to read CSV: {exc}")
    st.stop()

st.success(f"Loaded {len(df):,} rows × {len(df.columns)} columns")

col1, col2, col3 = st.columns(3)
col1.metric("Total customers", f"{len(df):,}")
col2.metric("Predicted churn", f"{df['churn_prediction'].sum():,}")
col3.metric("Mean P(churn)", f"{df['churn_probability'].mean():.2%}")

st.subheader("Risk segment distribution")
st.dataframe(df["risk_segment"].value_counts())

st.subheader("First 20 predictions")
st.dataframe(df.head(20))

st.caption(
    "This is a diagnostic probe. The full dashboard lives at "
    "`dashboards/churn_dashboard_app.py` — restore via "
    "`cp streamlit_app_full.py streamlit_app.py`."
)
