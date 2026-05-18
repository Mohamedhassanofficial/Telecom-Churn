"""Streamlit Cloud entrypoint shim.

Streamlit Cloud expects a single Python file at the repo root (or a
manifest pointing at one). The actual dashboard lives at
``dashboards/churn_dashboard_app.py``; this file simply re-executes it
so we don't duplicate code.

Local dev still runs ``streamlit run dashboards/churn_dashboard_app.py``
directly. Both paths read the same predictions CSV + model joblib.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

# Make `src` (and the project root) importable inside the Streamlit Cloud sandbox.
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("CHURN_BASE_DIR", str(_ROOT))

# Path the dashboard's @st.cache_data load_data() reads.
# The Streamlit Cloud build packs the repo into /app, so absolute paths
# below the repo root work out of the box.
runpy.run_path(str(_ROOT / "dashboards" / "churn_dashboard_app.py"),
               run_name="__main__")
