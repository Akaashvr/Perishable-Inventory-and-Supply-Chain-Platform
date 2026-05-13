"""Suppliers page — performance ranking using window functions."""

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_currency,
    fmt_number,
    page_header,
    render_sidebar_filters,
)

st.set_page_config(page_title="Suppliers — Perishable Dashboard", page_icon="🚚", layout="wide")

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Supplier performance",
    "Suppliers ranked by profit contribution and waste minimisation.",
    icon="🚚",
)

sup_df = q.get_supplier_rankings(**fkw)

if sup_df.empty:
    st.info("No supplier data for the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------

c1, c2, c3 = st.columns(3)
c1.metric("👥 Suppliers in window", fmt_number(len(sup_df)))
c2.metric("🥇 Top-ranked supplier", str(sup_df.iloc[0]["supplier_code"]))
c3.metric(
    "💵 Top-supplier profit",
    fmt_currency(float(sup_df.iloc[0]["profit"])) if sup_df.iloc[0]["profit"] is not None else "—",
)

st.markdown("---")


# ---------------------------------------------------------------------------
# Scatter: supplier score vs profit
# ---------------------------------------------------------------------------

page_header(
    "Score vs profit",
    "Does a higher supplier score correlate with higher profit?",
    icon="🎯",
)

fig = px.scatter(
    sup_df,
    x="supplier_score",
    y="profit",
    size="revenue",
    color="waste",
    hover_name="supplier_code",
    color_continuous_scale="RdYlGn_r",
    labels={
        "supplier_score": "Supplier score (0–100)",
        "profit": "Total profit",
        "revenue": "Revenue (size)",
        "waste": "Waste",
    },
)
fig.update_layout(
    height=480,
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Full leaderboard
# ---------------------------------------------------------------------------

page_header("Supplier leaderboard", icon="🏆")

display = sup_df.copy()
display["revenue"] = display["revenue"].astype(float).map(fmt_currency)
display["profit"]  = display["profit"].astype(float).map(fmt_currency)
display["waste"]   = display["waste"].astype(float).round(0)

st.dataframe(
    display.rename(columns={
        "supplier_code":   "Supplier",
        "supplier_score":  "Score",
        "revenue":         "Revenue",
        "profit":          "Profit",
        "waste":           "Waste",
        "txn_count":       "Transactions",
        "profit_rank":     "Profit rank",
        "waste_rank":      "Waste rank (low = good)",
    }),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Ranks are computed in SQL with `RANK() OVER (...)` window functions — "
    "see `app/queries.py::get_supplier_rankings`."
)
