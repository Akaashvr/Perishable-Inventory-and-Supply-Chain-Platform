"""
streamlit_app.py — Perishable Supply Chain Dashboard
=====================================================

Layout
------
  [Left Sidebar]  collapsible, filters only
  [Main Column]   top-tab navigation → page content
  [Right Column]  Query assistant chat panel
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import healthcheck, run_query
import queries as q
from theme import C, CHART_COLORS, inject_css, plotly_layout, section_header, app_header
from ai_chat import render_ai_chat

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Perishable Supply Chain",
    page_icon="https://cdn.jsdelivr.net/npm/remixicon@3.5.0/icons/Nature/leaf-line.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


# ─── Session state defaults ───────────────────────────────────────────────────
for _k, _v in {"chat_history": [], "ai_input": ""}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─── Sidebar — filters only ───────────────────────────────────────────────────
with st.sidebar:
    ok, _ = healthcheck()
    dot = "ri-checkbox-blank-circle-fill"
    badge_cls = "db-badge-ok" if ok else "db-badge-err"
    badge_lbl = "Connected" if ok else "Disconnected"

    st.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="sb-logo"><i class="ri-leaf-line" style="color:#070D18"></i></div><br>
          <div class="sb-title">Supply Chain</div>
          <div class="sb-sub">Perishable Inventory Platform</div>
          <div class="{badge_cls}">
            <i class="{dot}"></i>&nbsp;DB {badge_lbl}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Date range
    dmin, dmax = q.get_date_bounds()
    default_from = max(dmin, dmax - timedelta(days=90))

    date_range = st.date_input(
        "Date range",
        value=(default_from, dmax),
        min_value=dmin,
        max_value=dmax,
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_from, date_to = date_range
    else:
        date_from, date_to = dmin, dmax

    # Region
    regions = st.multiselect(
        "Region",
        options=q.get_regions(),
        placeholder="All regions",
    )

    # Category
    categories = st.multiselect(
        "Category",
        options=q.get_categories(),
        placeholder="All categories",
    )

    # Demand level
    demand_levels = st.multiselect(
        "Demand level",
        options=q.get_demand_levels(),
        placeholder="All levels",
    )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()


# Build filter kwargs
fkw = dict(
    date_from=date_from,
    date_to=date_to,
    regions=regions or None,
    categories=categories or None,
    demand_levels=demand_levels or None,
)


# ─── Chart helpers ────────────────────────────────────────────────────────────

def _fig(fig_obj: go.Figure, height: int = 400) -> go.Figure:
    """Apply the shared dark layout to any Plotly figure."""
    fig_obj.update_layout(**plotly_layout(height=height))
    return fig_obj


def _line(df: pd.DataFrame, x: str, y: str | list, title: str = "",
          height: int = 380, names: dict | None = None) -> go.Figure:
    """Spline line chart with area fill."""
    cols = y if isinstance(y, list) else [y]
    color_iter = iter(CHART_COLORS)

    traces = []
    for col in cols:
        c = next(color_iter)
        label = (names or {}).get(col, col.replace("_", " ").title())
        traces.append(
            go.Scatter(
                x=df[x], y=df[col],
                name=label,
                mode="lines",
                line=dict(color=c, width=2.5, shape="spline", smoothing=1.2),
                fill="tozeroy",
                fillcolor=c.replace(")", ", 0.08)").replace("rgb", "rgba")
                          if c.startswith("rgb") else f"{c}14",
                hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:,.0f}}<extra></extra>",
            )
        )

    fig = go.Figure(data=traces)
    fig.update_layout(**plotly_layout(height=height))
    return fig


def _bar(df: pd.DataFrame, x: str, y: str, color: str | None = None,
         orientation: str = "v", height: int = 380,
         rounded: bool = True) -> go.Figure:
    marker = dict(
        color=color or C["green"],
        cornerradius=8 if rounded else 0,
        line=dict(width=0),
    )
    if color and color in df.columns:
        fig = px.bar(df, x=x, y=y, color=color, orientation=orientation,
                     color_discrete_sequence=CHART_COLORS,
                     barmode="group")
    else:
        fig = px.bar(df, x=x, y=y, orientation=orientation,
                     color_discrete_sequence=CHART_COLORS)

    fig.update_traces(marker_cornerradius=8 if rounded else 0)
    fig.update_layout(**plotly_layout(height=height))
    return fig


def _pie(df: pd.DataFrame, names: str, values: str,
         height: int = 360) -> go.Figure:
    fig = px.pie(
        df, names=names, values=values,
        hole=0.52,
        color_discrete_sequence=CHART_COLORS,
    )
    fig.update_traces(
        textfont_color=C["text"],
        marker=dict(line=dict(color=C["border"], width=2)),
    )
    fig.update_layout(**plotly_layout(height=height))
    return fig


def _scatter(df: pd.DataFrame, x: str, y: str, size: str | None = None,
             color: str | None = None, hover_name: str | None = None,
             height: int = 400) -> go.Figure:
    fig = px.scatter(
        df, x=x, y=y,
        size=size,
        color=color,
        hover_name=hover_name,
        color_continuous_scale=["#00C896", "#FFD60A", "#FF4560"],
    )
    fig.update_traces(marker=dict(line=dict(color=C["border"], width=1)))
    fig.update_layout(**plotly_layout(height=height))
    return fig


def _heatmap(pivot: pd.DataFrame, height: int = 400) -> go.Figure:
    fig = px.imshow(
        pivot,
        text_auto=".2s",
        aspect="auto",
        color_continuous_scale=[[0, C["bg"]], [0.5, C["green_dim"]], [1, C["green"]]],
    )
    fig.update_layout(**plotly_layout(height=height))
    return fig


def _no_data() -> None:
    st.info("No data matches the current filters. Try widening the date range.")


# ─── Page renders ─────────────────────────────────────────────────────────────

def page_overview() -> None:
    # KPIs
    section_header("Executive snapshot", "Headline metrics for the selected period.",
                   "ri-dashboard-3-line")
    kpis = q.get_kpis(**fkw)
    if kpis.empty:
        _no_data(); return

    r = kpis.iloc[0]

    def _rev(v): return f"${float(v)/1e6:.2f}M" if float(v)>=1e6 else f"${float(v)/1e3:.1f}K"
    def _num(v): return f"{float(v)/1e6:.2f}M" if float(v)>=1e6 else f"{float(v)/1e3:.0f}K" if float(v)>=1e3 else f"{int(float(v)):,}"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue",        _rev(r["revenue"]))
    c2.metric("Profit",         _rev(r["profit"]))
    c3.metric("Waste units",    _num(r["waste_units"]))
    c4.metric("Units moved",    _num(r["units_moved"]))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Transactions",       f"{int(r['transactions']):,}")
    c6.metric("Distinct products",  str(int(r["distinct_products"])))
    c7.metric("Stores active",      str(int(r["distinct_stores"])))
    c8.metric("Suppliers active",   str(int(r["distinct_suppliers"])))

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Trend
    section_header("Revenue, Profit & Waste over time",
                   "Smoothed spline curves — hover to inspect.",
                   "ri-line-chart-line",
                   icon_bg="rgba(0,200,150,.15)")

    trend = q.get_daily_trend(**fkw)
    if trend.empty:
        _no_data()
    else:
        st.plotly_chart(
            _line(trend, "day", ["revenue", "profit", "waste"],
                  names={"revenue": "Revenue", "profit": "Profit", "waste": "Waste"}),
            use_container_width=True,
        )

    # Moving average
    section_header("7-Day Revenue Moving Average",
                   "Smoothed view isolating the underlying trend.",
                   "ri-funds-line",
                   icon_bg="rgba(0,168,232,.12)")

    ma = q.get_moving_avg(**fkw)
    if ma.empty:
        _no_data()
    else:
        fig = _line(ma, "day", ["revenue", "revenue_ma7"],
                    names={"revenue": "Daily revenue", "revenue_ma7": "7-day avg"})
        # Make daily line thinner and lighter
        fig.data[0].update(line=dict(width=1.2, color=C["border2"]), fill=None)
        fig.data[1].update(line=dict(width=3, color=C["orange"]))
        st.plotly_chart(fig, use_container_width=True)


def page_products() -> None:
    section_header("Top products", "Ranked by your chosen metric.",
                   "ri-plant-line", icon_bg="rgba(0,200,150,.12)")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        metric = st.selectbox(
            "Rank by",
            ["revenue", "profit", "units", "waste"],
            format_func=str.capitalize,
        )
    with col_b:
        limit = st.slider("Top N", 5, 30, 10, step=5)

    top = q.get_top_products(metric=metric, limit=limit, **fkw)
    if top.empty:
        _no_data()
    else:
        top_sorted = top.sort_values("metric_value", ascending=True)
        fig = px.bar(
            top_sorted,
            x="metric_value", y="product_name",
            color="category_name",
            orientation="h",
            labels={"metric_value": metric.capitalize(),
                    "product_name": "", "category_name": "Category"},
            color_discrete_sequence=CHART_COLORS,
        )
        fig.update_traces(marker_cornerradius=6)
        fig.update_layout(**plotly_layout(
            height=max(380, 28 * len(top_sorted) + 100),
            yaxis=dict(automargin=True, tickfont=dict(size=11)),
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Category breakdown",
                   "Revenue share and per-metric comparison.",
                   "ri-pie-chart-line", icon_bg="rgba(255,133,51,.12)")

    cat = q.get_category_breakdown(**fkw)
    if cat.empty:
        _no_data()
    else:
        cl, cr = st.columns([3, 2])
        with cl:
            long = cat.melt(
                id_vars="category_name",
                value_vars=["revenue", "profit", "waste"],
                var_name="metric", value_name="value",
            )
            fig2 = px.bar(
                long, x="category_name", y="value", color="metric",
                barmode="group",
                labels={"category_name": "Category", "value": "Amount", "metric": ""},
                color_discrete_sequence=[C["green"], C["blue"], C["red"]],
            )
            fig2.update_traces(marker_cornerradius=6)
            fig2.update_layout(**plotly_layout(height=360))
            st.plotly_chart(fig2, use_container_width=True)
        with cr:
            st.plotly_chart(_pie(cat, "category_name", "revenue"), use_container_width=True)

        def _fmt(v): return f"${float(v)/1e3:.1f}K"
        disp = cat.copy()
        disp["revenue"] = disp["revenue"].astype(float).map(_fmt)
        disp["profit"]  = disp["profit"].astype(float).map(_fmt)
        disp["waste"]   = disp["waste"].astype(float).round(0)
        st.dataframe(
            disp.rename(columns={
                "category_name": "Category", "revenue": "Revenue",
                "profit": "Profit", "waste": "Waste", "units": "Units",
            }),
            use_container_width=True, hide_index=True,
        )


def page_suppliers() -> None:
    section_header("Supplier leaderboard",
                   "Ranked by profit with window functions in SQL.",
                   "ri-truck-line", icon_bg="rgba(0,168,232,.12)")

    sup = q.get_supplier_rankings(**fkw)
    if sup.empty:
        _no_data(); return

    c1, c2, c3 = st.columns(3)
    c1.metric("Suppliers tracked",  str(len(sup)))
    c2.metric("Top supplier",       str(sup.iloc[0]["supplier_code"]))
    c3.metric("Top profit",
              f"${float(sup.iloc[0]['profit'])/1e3:.1f}K"
              if sup.iloc[0]["profit"] else "—")

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Score vs Profit",
                   "Bubble size = revenue.  Colour = waste level.",
                   "ri-bubble-chart-line", icon_bg="rgba(155,89,245,.12)")

    fig = _scatter(
        sup, x="supplier_score", y="profit",
        size="revenue", color="waste", hover_name="supplier_code",
    )
    fig.update_layout(
        xaxis_title="Supplier score (0–100)",
        yaxis_title="Total profit",
        coloraxis_colorbar=dict(title="Waste"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Full supplier table", icon="ri-table-line",
                   icon_bg="rgba(0,200,150,.1)")

    def _f(v): return f"${float(v)/1e3:.1f}K"
    disp = sup.copy()
    disp["revenue"] = disp["revenue"].astype(float).map(_f)
    disp["profit"]  = disp["profit"].astype(float).map(_f)
    disp["waste"]   = disp["waste"].astype(float).round(0)
    st.dataframe(
        disp.rename(columns={
            "supplier_code":  "Supplier",
            "supplier_score": "Score",
            "revenue":        "Revenue",
            "profit":         "Profit",
            "waste":          "Waste",
            "txn_count":      "Transactions",
            "profit_rank":    "Profit rank",
            "waste_rank":     "Waste rank",
        }),
        use_container_width=True, hide_index=True,
    )


def page_regions() -> None:
    section_header("Regional performance",
                   "Revenue, profit and waste by region.",
                   "ri-map-2-line", icon_bg="rgba(0,168,232,.12)")

    reg = q.get_region_performance(**fkw)
    if reg.empty:
        _no_data(); return

    long = reg.melt(
        id_vars="region_name",
        value_vars=["revenue", "profit", "waste"],
        var_name="metric", value_name="value",
    )
    fig = px.bar(
        long, x="region_name", y="value", color="metric",
        barmode="group",
        labels={"region_name": "Region", "value": "Amount", "metric": ""},
        color_discrete_sequence=[C["green"], C["blue"], C["red"]],
    )
    fig.update_traces(marker_cornerradius=8)
    fig.update_layout(**plotly_layout(height=380))
    st.plotly_chart(fig, use_container_width=True)

    def _f(v): return f"${float(v)/1e3:.1f}K"
    disp = reg.copy()
    disp["revenue"] = disp["revenue"].astype(float).map(_f)
    disp["profit"]  = disp["profit"].astype(float).map(_f)
    disp["waste"]   = disp["waste"].astype(float).round(0)
    st.dataframe(
        disp.rename(columns={
            "region_name": "Region", "stores": "Stores",
            "revenue": "Revenue", "profit": "Profit",
            "waste": "Waste", "units": "Units",
        }),
        use_container_width=True, hide_index=True,
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Region × Category revenue heatmap",
                   "Spot strong pockets at a glance.",
                   "ri-grid-line", icon_bg="rgba(255,133,51,.1)")

    heat = q.get_region_category_heatmap(**fkw)
    if heat.empty:
        _no_data()
    else:
        pivot = heat.pivot(
            index="region_name", columns="category_name", values="revenue"
        ).fillna(0)
        st.plotly_chart(
            _heatmap(pivot, height=max(340, 56 * len(pivot.index) + 80)),
            use_container_width=True,
        )


def page_waste() -> None:
    section_header("Spoilage overview",
                   "Headline waste figures for the period.",
                   "ri-recycle-line", icon_bg="rgba(255,69,96,.12)")

    sens = q.get_waste_by_sensitivity(**fkw)
    if sens.empty:
        _no_data(); return

    tot_w = float(sens["waste"].sum())
    tot_u = float(sens["units"].sum())
    rate  = (tot_w / tot_u * 100) if tot_u else 0.0

    def _n(v): return f"{v/1e3:.1f}K" if v >= 1e3 else f"{v:.0f}"

    c1, c2, c3 = st.columns(3)
    c1.metric("Total waste units", _n(tot_w))
    c2.metric("Total units moved", _n(tot_u))
    c3.metric("Overall waste rate", f"{rate:.1f}%")

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Waste by spoilage sensitivity",
                   "Products bucketed Low / Medium / High during ingestion.",
                   "ri-temp-hot-line", icon_bg="rgba(255,133,51,.12)")

    cl, cr = st.columns(2)
    with cl:
        fig1 = px.bar(
            sens, x="spoilage_sensitivity", y="waste",
            color="spoilage_sensitivity",
            labels={"spoilage_sensitivity": "Sensitivity", "waste": "Waste"},
            color_discrete_sequence=[C["green"], C["orange"], C["red"]],
        )
        fig1.update_traces(marker_cornerradius=10)
        fig1.update_layout(**plotly_layout(height=340, showlegend=False))
        st.plotly_chart(fig1, use_container_width=True)
    with cr:
        sens["waste_rate_pct"] = (sens["waste_rate"].astype(float) * 100).round(2)
        fig2 = px.bar(
            sens, x="spoilage_sensitivity", y="waste_rate_pct",
            color="spoilage_sensitivity",
            labels={"spoilage_sensitivity": "Sensitivity", "waste_rate_pct": "Waste rate (%)"},
            color_discrete_sequence=[C["green"], C["orange"], C["red"]],
        )
        fig2.update_traces(marker_cornerradius=10)
        fig2.update_layout(**plotly_layout(height=340, showlegend=False))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Top wasted products",
                   "Controlling these directly improves margin.",
                   "ri-error-warning-line", icon_bg="rgba(255,69,96,.1)")

    limit = st.slider("Products to show", 5, 30, 15, step=5)
    top_w = q.get_top_wasted_products(limit=limit, **fkw)
    if top_w.empty:
        _no_data()
    else:
        fig3 = px.bar(
            top_w.sort_values("total_waste", ascending=True),
            x="total_waste", y="product_name",
            color="spoilage_sensitivity",
            orientation="h",
            hover_data=["category_name", "shelf_life_days"],
            labels={"total_waste": "Total waste", "product_name": "",
                    "spoilage_sensitivity": "Sensitivity"},
            color_discrete_sequence=[C["green"], C["orange"], C["red"]],
        )
        fig3.update_traces(marker_cornerradius=6)
        fig3.update_layout(**plotly_layout(
            height=max(380, 28 * len(top_w) + 100),
            yaxis=dict(automargin=True),
        ))
        st.plotly_chart(fig3, use_container_width=True)


def page_promotions() -> None:
    section_header("Promotion impact",
                   "Promoted vs non-promoted side by side.",
                   "ri-price-tag-3-line", icon_bg="rgba(155,89,245,.12)")

    promo = q.get_promo_vs_nonpromo(**fkw)
    if promo.empty:
        _no_data(); return

    promo = promo.copy()
    promo["bucket"] = promo["is_promotion"].map(
        {True: "Promoted", False: "Non-promoted"}
    )

    def _f(v): return f"${float(v)/1e3:.1f}K" if float(v) >= 1e3 else f"${float(v):.0f}"

    # Side-by-side cards
    cols = st.columns(len(promo))
    palette = [C["purple"], C["green"]]
    for i, (col, (_, row)) in enumerate(zip(cols, promo.iterrows())):
        accent = palette[i % 2]
        col.markdown(
            f"""
            <div style="background:{C['surface']};border:1px solid {C['border']};
                        border-top:3px solid {accent};border-radius:12px;padding:16px">
              <div style="font-size:14px;font-weight:700;color:{accent};
                          margin-bottom:10px">{row['bucket']}</div>
              <div style="font-size:11px;color:{C['muted']};
                          text-transform:uppercase;letter-spacing:.7px">Transactions</div>
              <div style="font-size:20px;font-weight:700;color:{C['text']};
                          margin-bottom:6px">{int(row['transactions']):,}</div>
              <div style="font-size:11px;color:{C['muted']}">Revenue</div>
              <div style="font-size:18px;font-weight:600;color:{C['text']};
                          margin-bottom:6px">{_f(row['revenue'])}</div>
              <div style="font-size:11px;color:{C['muted']}">Profit</div>
              <div style="font-size:18px;font-weight:600;color:{C['text']};
                          margin-bottom:6px">{_f(row['profit'])}</div>
              <div style="font-size:11px;color:{C['muted']}">Waste</div>
              <div style="font-size:18px;font-weight:600;color:{C['red']}">{float(row['waste']):.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    section_header("Side-by-side comparison", icon="ri-bar-chart-grouped-line",
                   icon_bg="rgba(155,89,245,.1)")

    long = promo.melt(
        id_vars="bucket",
        value_vars=["revenue", "profit", "waste"],
        var_name="metric", value_name="value",
    )
    fig = px.bar(
        long, x="metric", y="value", color="bucket",
        barmode="group",
        labels={"metric": "Metric", "value": "Amount", "bucket": ""},
        color_discrete_sequence=[C["purple"], C["green"]],
    )
    fig.update_traces(marker_cornerradius=8)
    fig.update_layout(**plotly_layout(height=380))
    st.plotly_chart(fig, use_container_width=True)


def page_explorer() -> None:
    section_header("Data explorer",
                   "Live transaction grid — search, filter, export.",
                   "ri-search-eye-line", icon_bg="rgba(0,168,232,.1)")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("Search product, category, region or store",
                               placeholder="e.g. donut, west, store_042")
    with col_b:
        limit = st.slider("Row limit", 100, 2000, 500, step=100)

    df = q.get_sample_transactions(limit=limit, **fkw)
    if df.empty:
        _no_data(); return

    if search and search.strip():
        needle = search.strip().lower()
        mask = (
            df["product_name"].str.lower().str.contains(needle, na=False)
            | df["category_name"].str.lower().str.contains(needle, na=False)
            | df["region_name"].str.lower().str.contains(needle, na=False)
            | df["store_code"].str.lower().str.contains(needle, na=False)
        )
        df = df[mask]

    st.caption(f"Showing **{len(df):,}** rows (most recent first).")

    st.dataframe(
        df.rename(columns={
            "transaction_date": "Date", "product_name": "Product",
            "category_name": "Category", "region_name": "Region",
            "store_code": "Store", "quantity": "Qty",
            "unit_price": "Unit price", "waste_amount": "Waste",
            "profit": "Profit", "demand_level": "Demand",
            "is_promotion": "Promo",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="perishable_transactions.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ─── Main layout ──────────────────────────────────────────────────────────────
col_main, col_ai = st.columns([5, 1.8], gap="medium")

with col_main:
    # App header bar
    app_header(db_ok=ok)

    # Top navigation via tabs
    t_ov, t_pr, t_su, t_re, t_wa, t_pm, t_ex = st.tabs([
        "Overview",
        "Products",
        "Suppliers",
        "Regions",
        "Waste",
        "Promotions",
        "Data Explorer",
    ])

    with t_ov: page_overview()
    with t_pr: page_products()
    with t_su: page_suppliers()
    with t_re: page_regions()
    with t_wa: page_waste()
    with t_pm: page_promotions()
    with t_ex: page_explorer()

with col_ai:
    render_ai_chat()
