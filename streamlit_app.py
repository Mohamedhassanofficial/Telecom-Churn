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
import traceback
from pathlib import Path

# Make `src` (and the project root) importable inside the Streamlit Cloud sandbox.
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("CHURN_BASE_DIR", str(_ROOT))


# ---------------------------------------------------------------------------
# Pre-import diagnostic — Streamlit Cloud redacts the actual ModuleNotFoundError
# message when shown in the browser; we surface it to stdout (visible in the
# "Manage app" panel) AND to the dashboard itself so the next failure is
# self-explanatory.
# ---------------------------------------------------------------------------
def _probe_imports() -> list[str]:
    """Try the heavy imports the dashboard does and capture any failures."""
    failures: list[str] = []
    for mod in [
        "streamlit",
        "pandas",
        "numpy",
        "joblib",
        "plotly.express",
        "plotly.graph_objects",
        "sklearn.metrics",
        "lightgbm",
        "category_encoders",
        "imblearn",
        "dill",
        "loky",
        "threadpoolctl",
        "cloudpickle",
    ]:
        try:
            __import__(mod)
            print(f"[probe] OK {mod}")
        except Exception as exc:
            msg = f"{mod}: {type(exc).__name__}: {exc}"
            print(f"[probe] FAIL {msg}")
            failures.append(msg)
    return failures


_failures = _probe_imports()

if _failures:
    # Render a Streamlit error page that is NOT redacted — we control the
    # text so Streamlit Cloud will show it verbatim.
    try:
        import streamlit as st
        st.set_page_config(page_title="Telecom Churn — import error",
                           page_icon="⚠")
        st.error("Some dependencies failed to import. Full traceback below.")
        st.code("\n".join(_failures), language="text")
        st.caption(
            "If you're on Streamlit Cloud: this means `requirements.txt` is "
            "missing one of these modules. Open `requirements.txt`, add the "
            "missing name (with a compatible version pin), commit and push. "
            "Streamlit Cloud auto-rebuilds in ~30s."
        )
        st.stop()
    except Exception:
        # Last resort: print and re-raise so the redacted error path fires.
        traceback.print_exc()
        raise ImportError("\n".join(_failures))


# Path the dashboard's @st.cache_data load_data() reads.
# The Streamlit Cloud build packs the repo into /app, so absolute paths
# below the repo root work out of the box.
runpy.run_path(str(_ROOT / "dashboards" / "churn_dashboard_app.py"),
               run_name="__main__")
