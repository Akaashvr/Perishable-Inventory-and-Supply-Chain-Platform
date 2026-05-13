"""Regions & Stores page — geographical performance with a heatmap."""

import plotly.express as px
import streamlit as st

import queries as q
from ui import (
    fmt_currency,
    fmt_number,
    page_header,
    render_sidebar_filters,
)

st.set_page_config(page_title="Regions — Perishable Dashboard", page_icon="🗺️", layout="wide")

filters = render_sidebar_filters()
fkw = filters.as_kwargs()

page_header(
    "Regions & stores",
    "Where the business is firing and where it is leaking.",
    icon="🗺️",
)

reg_df = q.get_region_performance(**fkw)

if reg_df.empty:
    st.info("No regional data for the current filters.")
    st.stop()


# ---------------------------------------------------------------------------
# Regional bar chart
# ---------------------------------------------------------------------------

long_df = reg_df.melt(
    id_vars="region_name",
    value_vars=["revenue", "profit", "waste"],
    var_name="metric",
    value_name="value",
)

fig = px.bar(
    long_df,
    x="region_name",
    y="value",
    color="metric",
    barmode="group",
    labels={"region_name": "Region", "value": "Amount", "metric": "Metric"},
)
fig.update_layout(
    height=420,
    legend_title_text="",
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Regional summary
# ---------------------------------------------------------------------------

display = reg_df.copy()
display["revenue"] = display["revenue"].astype(float).map(fmt_currency)
display["profit"]  = display["profit"].astype(float).map(fmt_currency)
display["waste"]   = display["waste"].astype(float).round(0)
display["units"]   = display["units"].astype(int).map(fmt_number)

st.dataframe(
    display.rename(columns={
        "region_name": "Region",
        "stores":      "Stores",
        "revenue":     "Revenue",
        "profit":      "Profit",
        "waste":       "Waste (units)",
        "units":       "Units sold",
    }),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")


# ---------------------------------------------------------------------------
# Region × Category revenue heatmap
# ---------------------------------------------------------------------------

page_header(
    "Region × Category revenue heatmap",
    "Spot strong category-region pockets at a glance.",
    icon="🌡️",
)

heat_df = q.get_region_category_heatmap(**fkw)

if heat_df.empty:
    st.info("No data for the heatmap with the current filters.")
else:
    pivot = heat_df.pivot(
        index="region_name",
        columns="category_name",
        values="revenue",
    ).fillna(0)

    fig2 = px.imshow(
        pivot,
        text_auto=".2s",
        aspect="auto",
        color_continuous_scale="Greens",
        labels=dict(x="Category", y="Region", color="Revenue"),
    )
    fig2.update_layout(
        height=max(360, 60 * len(pivot.index) + 80),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)
