"""Data Explorer page — searchable, downloadable transaction-level grid."""

import streamlit as st

import queries as q
from ui import (
    page_header,
    render_sidebar_filters,
)

st.set_page_config(
    page_title="Data Explorer — Perishable Dashboard",
    page_icon="🔎",
    layout="wide",
)

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Data explorer",
    "Inspect the raw fact_inventory rows behind every chart.",
    icon="🔎",
)

limit = st.slider(
    "Row limit",
    min_value=100,
    max_value=2000,
    value=500,
    step=100,
    help="Cap on rows returned by the query — keeps the page snappy.",
)

df = q.get_sample_transactions(limit=limit, **fkw)

if df.empty:
    st.info("No transactions match the current filters.")
    st.stop()

st.caption(f"Showing **{len(df):,}** rows (most recent first).")

# Quick text search across product / region / store
search = st.text_input(
    "Quick search (product, category, region, store)",
    placeholder="e.g. donut, west, store_042",
)

if search:
    needle = search.strip().lower()
    mask = (
        df["product_name"].str.lower().str.contains(needle, na=False)
        | df["category_name"].str.lower().str.contains(needle, na=False)
        | df["region_name"].str.lower().str.contains(needle, na=False)
        | df["store_code"].str.lower().str.contains(needle, na=False)
    )
    df = df[mask]
    st.caption(f"Filtered to **{len(df):,}** rows matching `{search}`.")

st.dataframe(
    df.rename(columns={
        "transaction_date": "Date",
        "product_name":     "Product",
        "category_name":    "Category",
        "region_name":      "Region",
        "store_code":       "Store",
        "quantity":         "Qty",
        "unit_price":       "Unit price",
        "waste_amount":     "Waste",
        "profit":           "Profit",
        "demand_level":     "Demand",
        "is_promotion":     "Promo?",
    }),
    use_container_width=True,
    hide_index=True,
)

# Download as CSV
st.download_button(
    "⬇️  Download as CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name="perishable_transactions.csv",
    mime="text/csv",
    use_container_width=True,
)
