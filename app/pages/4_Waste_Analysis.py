"""Waste Analysis page — where is product spoiling and why."""

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_number,
    fmt_pct,
    page_header,
    render_sidebar_filters,
)

st.set_page_config(page_title="Waste — Perishable Dashboard", page_icon="🗑️", layout="wide")

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Waste & spoilage",
    "How much product is being wasted and which categories are driving it.",
    icon="🗑️",
)

sens_df = q.get_waste_by_sensitivity(**fkw)

if sens_df.empty:
    st.info("No waste data for the current filters.")
    st.stop()


# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------

total_waste = float(sens_df["waste"].sum())
total_units = float(sens_df["units"].sum())
overall_rate = (total_waste / total_units * 100) if total_units else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("🗑️ Total waste units", fmt_number(total_waste))
c2.metric("📦 Total units moved", fmt_number(total_units))
c3.metric("📉 Overall waste rate", fmt_pct(overall_rate))


st.markdown("---")


# ---------------------------------------------------------------------------
# Waste by spoilage sensitivity
# ---------------------------------------------------------------------------

page_header(
    "Waste by spoilage sensitivity",
    "Products are bucketed Low/Medium/High during ingestion.",
    icon="🌡️",
)

c1, c2 = st.columns(2)

with c1:
    fig = px.bar(
        sens_df,
        x="spoilage_sensitivity",
        y="waste",
        color="spoilage_sensitivity",
        labels={"spoilage_sensitivity": "Spoilage sensitivity", "waste": "Total waste"},
    )
    fig.update_layout(
        height=380,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    sens_df["waste_rate_pct"] = (sens_df["waste_rate"].astype(float) * 100).round(2)
    fig2 = px.bar(
        sens_df,
        x="spoilage_sensitivity",
        y="waste_rate_pct",
        color="spoilage_sensitivity",
        labels={
            "spoilage_sensitivity": "Spoilage sensitivity",
            "waste_rate_pct": "Waste rate (%)",
        },
    )
    fig2.update_layout(
        height=380,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)


st.markdown("---")


# ---------------------------------------------------------------------------
# Top wasted products
# ---------------------------------------------------------------------------

page_header(
    "Top wasted products",
    "Tightly controlled here = direct margin improvement.",
    icon="🥇",
)

limit = st.slider("Number of products", 5, 30, 15, step=5)

top_waste = q.get_top_wasted_products(limit=limit, **fkw)

if top_waste.empty:
    st.info("No wasted-product data for the current filters.")
else:
    fig3 = px.bar(
        top_waste.sort_values("total_waste", ascending=True),
        x="total_waste",
        y="product_name",
        color="spoilage_sensitivity",
        orientation="h",
        hover_data=["category_name", "shelf_life_days"],
        labels={
            "total_waste": "Total waste",
            "product_name": "Product",
            "spoilage_sensitivity": "Sensitivity",
        },
    )
    fig3.update_layout(
        height=max(420, 28 * len(top_waste) + 100),
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(
        top_waste.rename(columns={
            "product_name":         "Product",
            "category_name":        "Category",
            "spoilage_sensitivity": "Sensitivity",
            "shelf_life_days":      "Shelf life (days)",
            "total_waste":          "Total waste",
            "total_units":          "Units moved",
        }),
        use_container_width=True,
        hide_index=True,
    )
