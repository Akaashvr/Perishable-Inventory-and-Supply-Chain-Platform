from __future__ import annotations

import os
from typing import Any, Mapping

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your .env file locally or "
            "as an environment variable in Render."
        )
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
    except Exception as exc:
        return False, str(exc)
