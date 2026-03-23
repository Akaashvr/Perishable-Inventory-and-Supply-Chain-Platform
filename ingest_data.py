import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "product_id",
    "product_name",
    "category",
    "store_id",
    "region",
    "supplier_id",
    "transaction_date",
    "expiration_date",
    "shelf_life_days",
    "storage_temp",
    "daily_demand",
    "selling_price",
    "initial_quantity",
    "units_wasted",
    "profit",
    "supplier_score",
    "is_promoted",
    "markdown_applied",
    "discount_pct",
    "spoilage_sensitivity",
}


def get_engine():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        log.error("DATABASE_URL not found in environment or .env")
        sys.exit(1)

    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args={"connect_timeout": 10},
        future=True,
    )
    log.info("Connected engine created with NullPool.")
    return engine


def bucket_demand_level(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")

    if s.isna().all():
        return pd.Series(["Medium"] * len(series), index=series.index)

    s = s.fillna(s.median())
    q1 = s.quantile(0.33)
    q2 = s.quantile(0.66)

    return pd.Series(
        np.select(
            [s <= q1, (s > q1) & (s <= q2), s > q2],
            ["Low", "Medium", "High"],
            default="Medium",
        ),
        index=series.index,
    )


def bucket_spoilage_sensitivity(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.7)

    return pd.Series(
        np.select(
            [s <= 0.55, (s > 0.55) & (s <= 0.80), s > 0.80],
            ["Low", "Medium", "High"],
            default="Medium",
        ),
        index=series.index,
    )


def clean_dataframe(csv_path: str) -> pd.DataFrame:
    log.info(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    object_cols = df.select_dtypes(include="object").columns
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"": None, "nan": None, "None": None})

    for col in ["transaction_date", "expiration_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    before = len(df)
    df = df.dropna(subset=["transaction_date", "expiration_date"])
    log.info(f"Dropped {before - len(df)} rows with invalid dates.")

    bad_dates = df["expiration_date"] < df["transaction_date"]
    if bad_dates.any():
        log.warning(f"Swapping {int(bad_dates.sum())} rows where expiration_date < transaction_date.")
        df.loc[bad_dates, ["transaction_date", "expiration_date"]] = (
            df.loc[bad_dates, ["expiration_date", "transaction_date"]].to_numpy()
        )

    numeric_cols = [
        "shelf_life_days",
        "storage_temp",
        "daily_demand",
        "selling_price",
        "initial_quantity",
        "units_wasted",
        "profit",
        "supplier_score",
        "discount_pct",
        "spoilage_sensitivity",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bool_like_cols = ["is_promoted", "markdown_applied"]
    for col in bool_like_cols:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
            .clip(0, 1)
            .astype(bool)
        )

    df["shelf_life_days"] = df["shelf_life_days"].fillna(1).clip(lower=1).round().astype(int)
    df["storage_temp"] = df["storage_temp"].round(2)
    df["daily_demand"] = df["daily_demand"].fillna(df["daily_demand"].median()).clip(lower=0)
    df["selling_price"] = df["selling_price"].fillna(0).clip(lower=0).round(2)
    df["initial_quantity"] = df["initial_quantity"].fillna(1).clip(lower=1).round().astype(int)
    df["units_wasted"] = df["units_wasted"].fillna(0).clip(lower=0).round(2)
    df["profit"] = df["profit"].round(2)
    df["supplier_score"] = df["supplier_score"].fillna(0).clip(lower=0, upper=100).round(2)
    df["discount_pct"] = df["discount_pct"].fillna(0).clip(lower=0, upper=100).round(2)
    df["spoilage_sensitivity"] = df["spoilage_sensitivity"].fillna(df["spoilage_sensitivity"].median())

    df["demand_level"] = bucket_demand_level(df["daily_demand"])
    df["spoilage_sensitivity_label"] = bucket_spoilage_sensitivity(df["spoilage_sensitivity"])

    df["is_promotion"] = (
        df["is_promoted"].fillna(False)
        | df["markdown_applied"].fillna(False)
        | (df["discount_pct"].fillna(0) > 0)
    )

    # Map actual CSV fields into your normalized schema fields
    df["quantity"] = df["initial_quantity"]
    df["unit_price"] = df["selling_price"]
    df["waste_amount"] = df["units_wasted"]

    before = len(df)
    df = df.drop_duplicates()
    log.info(f"Dropped {before - len(df)} exact duplicate rows.")

    df = df.dropna(
        subset=[
            "product_id",
            "product_name",
            "category",
            "store_id",
            "region",
            "supplier_id",
            "transaction_date",
            "expiration_date",
        ]
    )

    cleaned = df[
        [
            "product_id",
            "product_name",
            "category",
            "store_id",
            "region",
            "supplier_id",
            "transaction_date",
            "expiration_date",
            "shelf_life_days",
            "storage_temp",
            "supplier_score",
            "spoilage_sensitivity_label",
            "quantity",
            "unit_price",
            "waste_amount",
            "profit",
            "demand_level",
            "is_promotion",
            "discount_pct",
        ]
    ].copy()

    log.info(f"Clean shape: {cleaned.shape}")
    return cleaned


def recreate_staging_table(engine):
    ddl = """
    DROP TABLE IF EXISTS stg_perishable_raw;

    CREATE TABLE stg_perishable_raw (
        product_id VARCHAR(100),
        product_name VARCHAR(255),
        category VARCHAR(100),
        store_id VARCHAR(100),
        region VARCHAR(100),
        supplier_id VARCHAR(100),
        transaction_date DATE,
        expiration_date DATE,
        shelf_life_days INTEGER,
        storage_temp NUMERIC(10,2),
        supplier_score NUMERIC(10,2),
        spoilage_sensitivity_label VARCHAR(20),
        quantity INTEGER,
        unit_price NUMERIC(10,2),
        waste_amount NUMERIC(10,2),
        profit NUMERIC(10,2),
        demand_level VARCHAR(20),
        is_promotion BOOLEAN,
        discount_pct NUMERIC(5,2)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))


def load_staging(df: pd.DataFrame, engine):
    log.info("Loading cleaned data into staging via pandas.to_sql(..., append)")
    df.to_sql(
        "stg_perishable_raw",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )


def load_dimensions_and_facts(engine):
    promotion_name_expr = """
    CASE
        WHEN COALESCE(st.discount_pct, 0) > 0
            THEN 'Discount ' || TRIM(TO_CHAR(st.discount_pct, 'FM999990.00')) || '%'
        ELSE 'Promoted - No Discount'
    END
    """

    with engine.begin() as conn:
        log.info("Loading regions...")
        conn.execute(text("""
            INSERT INTO regions (region_name)
            SELECT DISTINCT region
            FROM stg_perishable_raw
            WHERE region IS NOT NULL
            ON CONFLICT (region_name) DO NOTHING;
        """))

        log.info("Loading categories...")
        conn.execute(text("""
            INSERT INTO categories (category_name)
            SELECT DISTINCT category
            FROM stg_perishable_raw
            WHERE category IS NOT NULL
            ON CONFLICT (category_name) DO NOTHING;
        """))

        log.info("Loading stores...")
        conn.execute(text("""
            INSERT INTO stores (store_code, region_id)
            SELECT DISTINCT st.store_id, r.region_id
            FROM stg_perishable_raw st
            JOIN regions r
              ON r.region_name = st.region
            WHERE st.store_id IS NOT NULL
            ON CONFLICT (store_code) DO NOTHING;
        """))

        log.info("Loading suppliers...")
        conn.execute(text("""
            INSERT INTO suppliers (supplier_code, supplier_score)
            SELECT supplier_id, MAX(COALESCE(supplier_score, 0))
            FROM stg_perishable_raw
            WHERE supplier_id IS NOT NULL
            GROUP BY supplier_id
            ON CONFLICT (supplier_code) DO NOTHING;
        """))

        conn.execute(text("""
            UPDATE suppliers s
            SET supplier_score = src.max_score
            FROM (
                SELECT supplier_id, MAX(COALESCE(supplier_score, 0)) AS max_score
                FROM stg_perishable_raw
                WHERE supplier_id IS NOT NULL
                GROUP BY supplier_id
            ) src
            WHERE s.supplier_code = src.supplier_id;
        """))

        log.info("Loading products...")
        conn.execute(text("""
            INSERT INTO products (
                product_code,
                product_name,
                category_id,
                shelf_life_days,
                storage_temp_celsius,
                spoilage_sensitivity
            )
            SELECT DISTINCT ON (st.product_id)
                st.product_id,
                st.product_name,
                c.category_id,
                st.shelf_life_days,
                st.storage_temp,
                st.spoilage_sensitivity_label
            FROM stg_perishable_raw st
            JOIN categories c
              ON c.category_name = st.category
            WHERE st.product_id IS NOT NULL
              AND st.product_name IS NOT NULL
            ORDER BY st.product_id, st.transaction_date
            ON CONFLICT (product_code) DO NOTHING;
        """))

        log.info("Loading promotions...")
        conn.execute(text(f"""
            INSERT INTO promotions (promotion_name, discount_pct)
            SELECT DISTINCT
                {promotion_name_expr} AS promotion_name,
                COALESCE(st.discount_pct, 0) AS discount_pct
            FROM stg_perishable_raw st
            WHERE st.is_promotion = TRUE
            ON CONFLICT (promotion_name) DO NOTHING;
        """))

        log.info("Loading product_promotions...")
        conn.execute(text(f"""
            INSERT INTO product_promotions (product_id, promotion_id, valid_from, valid_to)
            SELECT DISTINCT
                p.product_id,
                pr.promotion_id,
                st.transaction_date,
                st.expiration_date
            FROM stg_perishable_raw st
            JOIN products p
              ON p.product_code = st.product_id
            JOIN promotions pr
              ON pr.promotion_name = {promotion_name_expr}
            WHERE st.is_promotion = TRUE
            ON CONFLICT (product_id, promotion_id, valid_from) DO NOTHING;
        """))

        log.info("Loading inventory_transactions...")
        result = conn.execute(text("""
            INSERT INTO inventory_transactions (
                product_id,
                store_id,
                supplier_id,
                transaction_date,
                expiration_date,
                quantity,
                unit_price,
                waste_amount,
                profit,
                demand_level,
                is_promotion
            )
            SELECT
                p.product_id,
                s.store_id,
                sp.supplier_id,
                st.transaction_date,
                st.expiration_date,
                st.quantity,
                st.unit_price,
                st.waste_amount,
                st.profit,
                st.demand_level,
                st.is_promotion
            FROM stg_perishable_raw st
            JOIN products p
              ON p.product_code = st.product_id
            JOIN stores s
              ON s.store_code = st.store_id
            JOIN suppliers sp
              ON sp.supplier_code = st.supplier_id
            ON CONFLICT (product_id, store_id, supplier_id, transaction_date) DO NOTHING;
        """))
        log.info(f"inventory_transactions inserted this run: {result.rowcount}")


def drop_staging(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS stg_perishable_raw;"))


def main():
    parser = argparse.ArgumentParser(
        description="Load perishable_goods_management.csv into Neon PostgreSQL."
    )
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        log.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    engine = get_engine()
    df = clean_dataframe(args.csv)
    recreate_staging_table(engine)
    load_staging(df, engine)
    load_dimensions_and_facts(engine)
    drop_staging(engine)

    log.info("Ingestion complete.")


if __name__ == "__main__":
    main()