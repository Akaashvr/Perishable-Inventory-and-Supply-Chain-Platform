
from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd
import streamlit as st

from db import run_query

DEFAULT_TTL = 600


# Filter option queries (cheap, low-cardinality lookups for the sidebar)

@st.cache_data(ttl=DEFAULT_TTL, show_spinner=False)
def get_date_bounds() -> tuple[date, date]:
    """Return the min/max transaction_date in fact_inventory."""
    df = run_query(
        "SELECT MIN(transaction_date) AS dmin, MAX(transaction_date) AS dmax "
        "FROM fact_inventory"
    )
    if df.empty or pd.isna(df.iloc[0]["dmin"]):
        today = date.today()
        return today, today
    return df.iloc[0]["dmin"], df.iloc[0]["dmax"]


@st.cache_data(ttl=DEFAULT_TTL, show_spinner=False)
def get_regions() -> list[str]:
    df = run_query("SELECT DISTINCT region_name FROM dim_store ORDER BY 1")
    if df.empty or "region_name" not in df.columns:
        return []
    return df["region_name"].dropna().tolist()


@st.cache_data(ttl=DEFAULT_TTL, show_spinner=False)
def get_categories() -> list[str]:
    df = run_query("SELECT DISTINCT category_name FROM dim_product ORDER BY 1")
    if df.empty or "category_name" not in df.columns:
        return []
    return df["category_name"].dropna().tolist()


@st.cache_data(ttl=DEFAULT_TTL, show_spinner=False)
def get_demand_levels() -> list[str]:
    df = run_query(
        "SELECT DISTINCT demand_level FROM fact_inventory "
        "WHERE demand_level IS NOT NULL ORDER BY 1"
    )
    if df.empty or "demand_level" not in df.columns:
        return []
    return df["demand_level"].tolist()


# Helper: turn list filters into safe SQL fragments
def _build_filter_clauses(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> tuple[str, dict]:
    """Return a ``WHERE ...`` fragment and the matching bind-parameter dict.

    We use ``ANY(:list)`` rather than ``IN (...)`` so the parameter list
    length doesn't change the prepared statement and the driver can bind
    arrays safely.
    """
    clauses = ["f.transaction_date BETWEEN :date_from AND :date_to"]
    params: dict = {"date_from": date_from, "date_to": date_to}

    if regions:
        clauses.append("ds.region_name = ANY(:regions)")
        params["regions"] = list(regions)
    if categories:
        clauses.append("dp.category_name = ANY(:categories)")
        params["categories"] = list(categories)
    if demand_levels:
        clauses.append("f.demand_level = ANY(:demand_levels)")
        params["demand_levels"] = list(demand_levels)

    where = "WHERE " + " AND ".join(clauses)
    return where, params


# KPI / summary queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Computing KPIs…")
def get_kpis(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            COUNT(*)                                              AS transactions,
            COALESCE(SUM(f.quantity * f.unit_price), 0)::numeric  AS revenue,
            COALESCE(SUM(f.profit), 0)::numeric                   AS profit,
            COALESCE(SUM(f.waste_amount), 0)::numeric             AS waste_units,
            COALESCE(SUM(f.quantity), 0)                          AS units_moved,
            COUNT(DISTINCT f.product_id)                          AS distinct_products,
            COUNT(DISTINCT f.store_id)                            AS distinct_stores,
            COUNT(DISTINCT f.supplier_id)                         AS distinct_suppliers
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
    """
    return run_query(sql, params)


# Time-series queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Loading trend data…")
def get_daily_trend(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            f.transaction_date                            AS day,
            SUM(f.quantity * f.unit_price)::numeric       AS revenue,
            SUM(f.profit)::numeric                        AS profit,
            SUM(f.waste_amount)::numeric                  AS waste,
            SUM(f.quantity)                               AS units
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY f.transaction_date
        ORDER BY f.transaction_date
    """
    return run_query(sql, params)


@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Computing 7-day moving averages…")
def get_moving_avg(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    """7-day moving average of revenue — uses a window function."""
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        WITH daily AS (
            SELECT
                f.transaction_date AS day,
                SUM(f.quantity * f.unit_price)::numeric AS revenue
            FROM fact_inventory f
            JOIN dim_product dp ON dp.product_id = f.product_id
            JOIN dim_store   ds ON ds.store_id   = f.store_id
            {where}
            GROUP BY f.transaction_date
        )
        SELECT
            day,
            revenue,
            AVG(revenue) OVER (
                ORDER BY day
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) AS revenue_ma7
        FROM daily
        ORDER BY day
    """
    return run_query(sql, params)


# Product / category queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Ranking products…")
def get_top_products(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
    metric: str = "revenue",
    limit: int = 10,
) -> pd.DataFrame:
    metric_expr = {
        "revenue": "SUM(f.quantity * f.unit_price)",
        "profit": "SUM(f.profit)",
        "waste":   "SUM(f.waste_amount)",
        "units":   "SUM(f.quantity)",
    }.get(metric, "SUM(f.quantity * f.unit_price)")

    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    params["row_limit"] = int(limit)

    sql = f"""
        SELECT
            dp.product_name,
            dp.category_name,
            {metric_expr}::numeric AS metric_value
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY dp.product_name, dp.category_name
        ORDER BY metric_value DESC NULLS LAST
        LIMIT :row_limit
    """
    return run_query(sql, params)


@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Summarising by category…")
def get_category_breakdown(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            dp.category_name,
            SUM(f.quantity * f.unit_price)::numeric  AS revenue,
            SUM(f.profit)::numeric                   AS profit,
            SUM(f.waste_amount)::numeric             AS waste,
            SUM(f.quantity)                          AS units
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY dp.category_name
        ORDER BY revenue DESC
    """
    return run_query(sql, params)


# Supplier queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Ranking suppliers…")
def get_supplier_rankings(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    """Supplier ranking — uses a window function for the RANK column."""
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        WITH agg AS (
            SELECT
                dsup.supplier_code,
                MAX(dsup.supplier_score)::numeric AS supplier_score,
                SUM(f.quantity * f.unit_price)::numeric  AS revenue,
                SUM(f.profit)::numeric                   AS profit,
                SUM(f.waste_amount)::numeric             AS waste,
                COUNT(*)                                 AS txn_count
            FROM fact_inventory f
            JOIN dim_supplier dsup ON dsup.supplier_id = f.supplier_id
            JOIN dim_product  dp   ON dp.product_id    = f.product_id
            JOIN dim_store    ds   ON ds.store_id      = f.store_id
            {where}
            GROUP BY dsup.supplier_code
        )
        SELECT
            supplier_code,
            supplier_score,
            revenue,
            profit,
            waste,
            txn_count,
            RANK() OVER (ORDER BY profit DESC NULLS LAST) AS profit_rank,
            RANK() OVER (ORDER BY waste  ASC  NULLS LAST) AS waste_rank
        FROM agg
        ORDER BY profit DESC NULLS LAST
    """
    return run_query(sql, params)


# Store / region queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Summarising stores…")
def get_region_performance(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            ds.region_name,
            COUNT(DISTINCT ds.store_id)              AS stores,
            SUM(f.quantity * f.unit_price)::numeric  AS revenue,
            SUM(f.profit)::numeric                   AS profit,
            SUM(f.waste_amount)::numeric             AS waste,
            SUM(f.quantity)                          AS units
        FROM fact_inventory f
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        JOIN dim_product dp ON dp.product_id = f.product_id
        {where}
        GROUP BY ds.region_name
        ORDER BY revenue DESC
    """
    return run_query(sql, params)


@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Building heatmap…")
def get_region_category_heatmap(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            ds.region_name,
            dp.category_name,
            SUM(f.quantity * f.unit_price)::numeric AS revenue
        FROM fact_inventory f
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        JOIN dim_product dp ON dp.product_id = f.product_id
        {where}
        GROUP BY ds.region_name, dp.category_name
        ORDER BY ds.region_name, dp.category_name
    """
    return run_query(sql, params)


# Waste analysis queries

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Computing waste analytics…")
def get_waste_by_sensitivity(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            dp.spoilage_sensitivity,
            SUM(f.waste_amount)::numeric AS waste,
            SUM(f.quantity)              AS units,
            CASE
                WHEN SUM(f.quantity) > 0
                    THEN (SUM(f.waste_amount) / NULLIF(SUM(f.quantity), 0))::numeric
                ELSE 0
            END AS waste_rate
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY dp.spoilage_sensitivity
        ORDER BY waste DESC
    """
    return run_query(sql, params)


@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Ranking top wasted products…")
def get_top_wasted_products(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
    limit: int = 15,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    params["row_limit"] = int(limit)
    sql = f"""
        SELECT
            dp.product_name,
            dp.category_name,
            dp.spoilage_sensitivity,
            dp.shelf_life_days,
            SUM(f.waste_amount)::numeric AS total_waste,
            SUM(f.quantity)              AS total_units
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY dp.product_name, dp.category_name, dp.spoilage_sensitivity, dp.shelf_life_days
        ORDER BY total_waste DESC NULLS LAST
        LIMIT :row_limit
    """
    return run_query(sql, params)

# Promotion impact

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Comparing promotional impact…")
def get_promo_vs_nonpromo(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    sql = f"""
        SELECT
            f.is_promotion,
            COUNT(*)                                AS transactions,
            SUM(f.quantity)                         AS units,
            SUM(f.quantity * f.unit_price)::numeric AS revenue,
            SUM(f.profit)::numeric                  AS profit,
            SUM(f.waste_amount)::numeric            AS waste,
            AVG(f.unit_price)::numeric              AS avg_unit_price
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        GROUP BY f.is_promotion
        ORDER BY f.is_promotion
    """
    return run_query(sql, params)


# Raw sample (for the data-explorer tab)

@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Fetching sample rows…")
def get_sample_transactions(
    date_from: date,
    date_to: date,
    regions: Sequence[str] | None,
    categories: Sequence[str] | None,
    demand_levels: Sequence[str] | None,
    limit: int = 500,
) -> pd.DataFrame:
    where, params = _build_filter_clauses(
        date_from, date_to, regions, categories, demand_levels
    )
    params["row_limit"] = int(limit)
    sql = f"""
        SELECT
            f.transaction_date,
            dp.product_name,
            dp.category_name,
            ds.region_name,
            ds.store_code,
            f.quantity,
            f.unit_price,
            f.waste_amount,
            f.profit,
            f.demand_level,
            f.is_promotion
        FROM fact_inventory f
        JOIN dim_product dp ON dp.product_id = f.product_id
        JOIN dim_store   ds ON ds.store_id   = f.store_id
        {where}
        ORDER BY f.transaction_date DESC
        LIMIT :row_limit
    """
    return run_query(sql, params)
