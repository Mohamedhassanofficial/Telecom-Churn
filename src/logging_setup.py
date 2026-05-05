"""Centralised logging configuration.

Every module in ``src`` and every script grabs its logger via::

    from src.logging_setup import get_logger
    log = get_logger(__name__)

Output goes to stdout by default. Inside Airflow, the task logger
captures stdout into the per-task log file automatically.

Set ``CHURN_LOG_LEVEL=DEBUG`` in the environment to turn on debug logs.
"""
from __future__ import annotations

import logging
import os
import sys

_FMT = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_CONFIGURED: bool = False


def _configure_root() -> None:
    """Idempotently configure the root logger with stdout handler."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.environ.get("CHURN_LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    # Wipe pre-existing handlers (Airflow installs its own; we add ours).
    has_stream_handler = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "_churn", False)
        for h in root.handlers
    )
    if not has_stream_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))
        handler._churn = True  # type: ignore[attr-defined]
        root.addHandler(handler)

    # Tame chatty third-parties.
    for noisy in ("dask", "distributed", "matplotlib", "fiona", "rasterio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a configured logger. Safe to call from any module."""
    _configure_root()
    return logging.getLogger(name or "churn")
