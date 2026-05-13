"""
streamlit_app.py — entry point for the Perishable Inventory dashboard.

This file is what Streamlit loads first (`streamlit run streamlit_app.py`).
It defines the global page config and serves as the **Overview** page;
the other pages live in `pages/` and are auto-discovered by Streamlit's
multi-page app feature.
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_currency,
    fmt_number,
    page_header,
    render_sidebar_filters,
)


# ---------------------------------------------------------------------------
# Global page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Perishable Inventory Dashboard",
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**Perishable Inventory & Supply Chain Platform**\n\n"
            "EAS 550 — Team 9 — Phase 3.\n\n"
            "A live BI dashboard built with Streamlit, Plotly, dbt and a "
            "pooled SQLAlchemy connection to a Neon serverless Postgres "
            "Star Schema."
        ),
    },
)


# ---------------------------------------------------------------------------
# Sidebar filters (shared across pages)
# ---------------------------------------------------------------------------

filters = render_sidebar_filters()
fkw = filters.as_kwargs()


# ---------------------------------------------------------------------------
# Hero / header
# ---------------------------------------------------------------------------

st.markdown(
    """
    # 🥬 Perishable Inventory & Supply Chain Platform
    *Live analytics over a dbt Star Schema in Neon Postgres.*
    """
)
st.markdown(
    """
    Use the sidebar to narrow by date range, region, category, or demand
    level. Each page below drills into a different slice of the business —
    products, suppliers, regions, waste, and promotions.
    """
)
st.markdown("---")


# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------

page_header(
    "Executive overview",
    "Headline metrics for the selected period.",
    icon="🚀",
)

kpis_df = q.get_kpis(**fkw)

if kpis_df.empty:
    st.info("No data matches the current filters. Try widening the date range.")
else:
    row = kpis_df.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Revenue",      fmt_currency(float(row["revenue"])))
    c2.metric("📈 Profit",       fmt_currency(float(row["profit"])))
    c3.metric("🗑️ Waste (units)", fmt_number(float(row["waste_units"])))
    c4.metric("📦 Units moved",  fmt_number(int(row["units_moved"])))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("🧾 Transactions",   fmt_number(int(row["transactions"])))
    c6.metric("🥦 Distinct products", fmt_number(int(row["distinct_products"])))
    c7.metric("🏬 Stores active",  fmt_number(int(row["distinct_stores"])))
    c8.metric("🚚 Suppliers active", fmt_number(int(row["distinct_suppliers"])))

st.markdown("---")


# ---------------------------------------------------------------------------
# Daily trend chart
# ---------------------------------------------------------------------------

page_header(
    "Daily revenue, profit & waste",
    "Stacked time series — drag inside the plot to zoom.",
    icon="📈",
)

trend_df = q.get_daily_trend(**fkw)

if trend_df.empty:
    st.info("No trend data for the current filters.")
else:
    long_df = trend_df.melt(
        id_vars="day",
        value_vars=["revenue", "profit", "waste"],
        var_name="metric",
        value_name="value",
    )
    fig = px.line(
        long_df,
        x="day",
        y="value",
        color="metric",
        labels={"day": "Date", "value": "Amount", "metric": "Metric"},
        title=None,
    )
    fig.update_layout(
        height=420,
        legend_title_text="",
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# 7-day moving-average chart
# ---------------------------------------------------------------------------

page_header(
    "Revenue: daily vs 7-day moving average",
    "Smoothed view that highlights underlying trends and seasonality.",
    icon="📉",
)

ma_df = q.get_moving_avg(**fkw)

if ma_df.empty:
    st.info("Not enough data for a moving average. Try widening the date range.")
else:
    fig2 = px.line(
        ma_df,
        x="day",
        y=["revenue", "revenue_ma7"],
        labels={"day": "Date", "value": "Revenue", "variable": "Series"},
    )
    fig2.update_layout(
        height=420,
        legend_title_text="",
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
    )
    # rename the auto-generated legend entries to be friendlier
    fig2.for_each_trace(
        lambda t: t.update(
            name={
                "revenue": "Daily revenue",
                "revenue_ma7": "7-day moving average",
            }.get(t.name, t.name)
        )
    )
    st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------------------------
# Where-to-next pointers
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    """
    ### 👉 Drill deeper
    - **Products** — top products by revenue, profit, and units moved
    - **Suppliers** — ranked supplier performance with window functions
    - **Regions & Stores** — geographical heatmap by category
    - **Waste Analysis** — spoilage by sensitivity tier and product
    - **Promotions** — promoted vs non-promoted side-by-side
    - **Data Explorer** — interactive transaction-level grid + CSV export
    """
)
