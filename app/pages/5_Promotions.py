"""Promotions page — promoted vs non-promoted side-by-side."""

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_currency,
    fmt_number,
    page_header,
    render_sidebar_filters,
)

st.set_page_config(page_title="Promotions — Perishable Dashboard", page_icon="🎯", layout="wide")

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Promotion impact",
    "Side-by-side: are promotions actually moving the needle?",
    icon="🎯",
)

promo_df = q.get_promo_vs_nonpromo(**fkw)

if promo_df.empty:
    st.info("No promotion data for the current filters.")
    st.stop()

promo_df = promo_df.copy()
promo_df["bucket"] = promo_df["is_promotion"].map(
    {True: "🎯 Promoted", False: "🛒 Non-promoted"}
)


# ---------------------------------------------------------------------------
# Side-by-side KPI cards
# ---------------------------------------------------------------------------

cols = st.columns(len(promo_df))
for col, (_, row) in zip(cols, promo_df.iterrows()):
    with col:
        st.subheader(row["bucket"])
        st.metric("Transactions", fmt_number(int(row["transactions"])))
        st.metric("Revenue",      fmt_currency(float(row["revenue"])))
        st.metric("Profit",       fmt_currency(float(row["profit"])))
        st.metric("Waste",        fmt_number(float(row["waste"])))
        st.metric("Avg unit price",
                  fmt_currency(float(row["avg_unit_price"]) if row["avg_unit_price"] is not None else 0))

st.markdown("---")


# ---------------------------------------------------------------------------
# Grouped bar comparison
# ---------------------------------------------------------------------------

long_df = promo_df.melt(
    id_vars="bucket",
    value_vars=["revenue", "profit", "waste"],
    var_name="metric",
    value_name="value",
)

fig = px.bar(
    long_df,
    x="metric",
    y="value",
    color="bucket",
    barmode="group",
    labels={"metric": "Metric", "value": "Amount", "bucket": ""},
)
fig.update_layout(
    height=440,
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Filtered by your current sidebar selections. To compare a specific "
    "category's response to promotions, narrow the **Product categories** "
    "filter and watch how the bars rebalance."
)
