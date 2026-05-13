"""
ui.py
=====

Small UI helpers shared across every dashboard page:

* ``render_sidebar_filters()`` — the single source of truth for filter
  widgets. Each page calls this exactly once, then passes the returned
  dict into the query layer.
* ``fmt_*`` — formatting helpers for currency / large numbers.
* ``render_db_status()`` — sidebar health indicator with a refresh button
  that clears Streamlit's data cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db import healthcheck
import queries as q


# ---------------------------------------------------------------------------
# Filter state object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Filters:
    date_from: date
    date_to: date
    regions: list[str]
    categories: list[str]
    demand_levels: list[str]

    def as_kwargs(self) -> dict:
        """Convenience: spread directly into the query functions."""
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            # Treat empty multiselect as "no filter".
            "regions": self.regions or None,
            "categories": self.categories or None,
            "demand_levels": self.demand_levels or None,
        }


# ---------------------------------------------------------------------------
# Sidebar — filters + DB status
# ---------------------------------------------------------------------------

def render_sidebar_filters() -> Filters:
    """Render the shared sidebar and return the user's selections."""
    st.sidebar.markdown("### 🔎 Filters")

    dmin, dmax = q.get_date_bounds()

    # Default: show the most recent 90 days of data if range is wider.
    default_from = max(dmin, dmax - timedelta(days=90))

    date_range = st.sidebar.date_input(
        "Transaction date range",
        value=(default_from, dmax),
        min_value=dmin,
        max_value=dmax,
        help="Drag to focus on a specific window.",
    )

    # Streamlit returns a single date if the user only picks one endpoint.
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from, date_to = date_range
    else:
        date_from, date_to = dmin, dmax

    regions = st.sidebar.multiselect(
        "Regions",
        options=q.get_regions(),
        default=[],
        help="Leave empty to include every region.",
    )

    categories = st.sidebar.multiselect(
        "Product categories",
        options=q.get_categories(),
        default=[],
        help="Leave empty to include every category.",
    )

    demand_levels = st.sidebar.multiselect(
        "Demand level",
        options=q.get_demand_levels(),
        default=[],
        help="Filter to specific demand buckets (Low / Medium / High).",
    )

    st.sidebar.markdown("---")
    render_db_status()
    render_about_box()

    return Filters(
        date_from=date_from,
        date_to=date_to,
        regions=regions,
        categories=categories,
        demand_levels=demand_levels,
    )


def render_db_status() -> None:
    """Tiny health indicator + a manual cache-clear button."""
    ok, msg = healthcheck()
    if ok:
        st.sidebar.success(f"🟢 Database: {msg}")
    else:
        st.sidebar.error(f"🔴 Database: {msg}")

    if st.sidebar.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def render_about_box() -> None:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        ### About
        **Perishable Inventory & Supply Chain Platform**

        EAS 550 — Team 9 — Phase 3

        Live BI dashboard over a dbt-modelled Star Schema in Neon
        Postgres. All queries are parameterised, cached, and run through
        a pooled SQLAlchemy engine.
        """
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_currency(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value/1_000:,.1f}K"
    return f"${value:,.2f}"


def fmt_number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"{value/1_000:,.1f}K"
    return f"{value:,.0f}"


def fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{digits}f}%"


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str | None = None, icon: str = "📊") -> None:
    st.markdown(f"## {icon}  {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown("")
