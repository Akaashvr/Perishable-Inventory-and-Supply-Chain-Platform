"""Products page — top performers and category breakdown."""

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_currency,
    page_header,
    render_sidebar_filters,
)

st.set_page_config(page_title="Products — Perishable Dashboard", page_icon="🥦", layout="wide")

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Product analytics",
    "Best and worst performers, broken down by category.",
    icon="🥦",
)

# ---------------------------------------------------------------------------
# Controls specific to this page
# ---------------------------------------------------------------------------

c1, c2 = st.columns([1, 1])
metric = c1.selectbox(
    "Rank products by",
    options=["revenue", "profit", "units", "waste"],
    format_func=str.capitalize,
)
limit = c2.slider("Number of products to show", min_value=5, max_value=30, value=10, step=5)


# ---------------------------------------------------------------------------
# Top products bar chart
# ---------------------------------------------------------------------------

top_df = q.get_top_products(metric=metric, limit=limit, **fkw)

if top_df.empty:
    st.info("No products match the current filters.")
else:
    fig = px.bar(
        top_df.sort_values("metric_value", ascending=True),
        x="metric_value",
        y="product_name",
        color="category_name",
        orientation="h",
        labels={
            "metric_value": metric.capitalize(),
            "product_name": "Product",
            "category_name": "Category",
        },
    )
    fig.update_layout(
        height=max(420, 28 * len(top_df) + 100),
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------

page_header(
    "Category breakdown",
    "How each product category contributes to revenue, profit and waste.",
    icon="🧁",
)

cat_df = q.get_category_breakdown(**fkw)

if cat_df.empty:
    st.info("No category data for the current filters.")
else:
    left, right = st.columns([2, 1])

    long_df = cat_df.melt(
        id_vars="category_name",
        value_vars=["revenue", "profit", "waste"],
        var_name="metric",
        value_name="value",
    )

    with left:
        fig2 = px.bar(
            long_df,
            x="category_name",
            y="value",
            color="metric",
            barmode="group",
            labels={"category_name": "Category", "value": "Amount", "metric": "Metric"},
        )
        fig2.update_layout(
            height=420,
            legend_title_text="",
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        fig3 = px.pie(
            cat_df,
            names="category_name",
            values="revenue",
            hole=0.4,
            title="Revenue share",
        )
        fig3.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=40, b=10),
            showlegend=True,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Tidy summary table
    display_df = cat_df.copy()
    display_df["revenue"] = display_df["revenue"].astype(float).map(fmt_currency)
    display_df["profit"] = display_df["profit"].astype(float).map(fmt_currency)
    display_df["waste"] = display_df["waste"].astype(float).round(0)

    st.dataframe(
        display_df.rename(columns={
            "category_name": "Category",
            "revenue": "Revenue",
            "profit": "Profit",
            "waste": "Waste (units)",
            "units": "Units",
        }),
        use_container_width=True,
        hide_index=True,
    )
