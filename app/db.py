"""
db.py
=====

Secure, pooled connection layer to the Neon PostgreSQL database.

Design notes
------------
* `DATABASE_URL` is read from the environment (loaded from `.env` locally,
  injected as a Render secret in production). It is **never** hardcoded.
* The SQLAlchemy engine is created exactly once per Streamlit worker process
  (via `@st.cache_resource`) and uses `QueuePool` so concurrent dashboard
  visitors share a small, bounded set of connections instead of opening a
  new TCP socket per query.
* `pool_pre_ping=True` recycles dead connections silently, which matters on
  Neon's serverless free tier where the compute can auto-pause and tear
  down idle TCP connections.
* `pool_recycle=300` proactively recycles connections older than 5 minutes
  so we never hand a half-dead connection to a page render.
* All queries should go through `run_query()` so caching and error
  handling are centralised.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Load .env once at import time. In production (Render) the env vars are
# already injected by the platform, so load_dotenv() is a no-op.
load_dotenv()


def _get_database_url() -> str:
    """Return the DATABASE_URL or raise a clear error.

    We also normalise the historical ``postgres://`` scheme to
    ``postgresql+psycopg2://`` so SQLAlchemy picks the right driver.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your .env file locally or "
            "as an environment variable in Render."
        )

    # Neon sometimes hands out URLs starting with `postgres://`; SQLAlchemy
    # prefers `postgresql://`. We also force the psycopg2 driver explicitly.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]

    return url


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    """Create and cache a pooled SQLAlchemy engine for the app lifetime."""
    database_url = _get_database_url()

    engine = create_engine(
        database_url,
        # --- Connection pooling configuration ---
        pool_size=5,            # baseline pool of warm connections
        max_overflow=5,         # extra connections if pool is exhausted
        pool_timeout=30,        # seconds to wait for a free connection
        pool_recycle=300,       # recycle connections older than 5 minutes
        pool_pre_ping=True,     # transparently replace dead connections
        # --- Driver behaviour ---
        connect_args={
            "connect_timeout": 10,
            "sslmode": "require",      # Neon requires SSL
            "application_name": "perishable-streamlit-dashboard",
        },
        future=True,
    )
    return engine


def run_query(
    sql: str,
    params: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Execute a parameterised SELECT and return a DataFrame.

    Always use bind parameters (``:name``) rather than f-strings to avoid
    SQL injection — Streamlit widgets feed user input straight into here.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=dict(params or {}))
    except SQLAlchemyError as exc:
        st.error(f"Database error while running query: {exc}")
        return pd.DataFrame()


def healthcheck() -> tuple[bool, str]:
    """Lightweight DB ping used by the sidebar status indicator."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connected"
    except Exception as exc:  # noqa: BLE001 — we want broad reporting here
        return False, str(exc)
