-- SCHEMA
DROP TABLE IF EXISTS inventory_transactions CASCADE;
DROP TABLE IF EXISTS product_promotions CASCADE;
DROP TABLE IF EXISTS promotions CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS stores CASCADE;
DROP TABLE IF EXISTS regions CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

CREATE TABLE regions (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE stores (
    store_id SERIAL PRIMARY KEY,
    store_code VARCHAR(50) NOT NULL UNIQUE,
    region_id INTEGER NOT NULL REFERENCES regions(region_id),
    CONSTRAINT chk_store_code_nonempty CHECK (LENGTH(TRIM(store_code)) > 0)
);

CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_code VARCHAR(50) NOT NULL UNIQUE,
    supplier_score NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT chk_supplier_score CHECK (supplier_score BETWEEN 0 AND 100)
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    shelf_life_days INTEGER NOT NULL,
    storage_temp_celsius NUMERIC(6,2),
    spoilage_sensitivity VARCHAR(20) NOT NULL,
    CONSTRAINT chk_shelf_life CHECK (shelf_life_days > 0),
    CONSTRAINT chk_spoilage_sens CHECK (spoilage_sensitivity IN ('Low', 'Medium', 'High'))
);

CREATE TABLE promotions (
    promotion_id SERIAL PRIMARY KEY,
    promotion_name VARCHAR(200) NOT NULL UNIQUE,
    discount_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT chk_discount CHECK (discount_pct BETWEEN 0 AND 100)
);

CREATE TABLE product_promotions (
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    promotion_id INTEGER NOT NULL REFERENCES promotions(promotion_id),
    valid_from DATE NOT NULL,
    valid_to DATE,
    PRIMARY KEY (product_id, promotion_id, valid_from),
    CONSTRAINT chk_promo_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE TABLE inventory_transactions (
    transaction_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    store_id INTEGER NOT NULL REFERENCES stores(store_id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),

    transaction_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    waste_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    profit NUMERIC(10,2),
    demand_level VARCHAR(20) NOT NULL,
    is_promotion BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_quantity CHECK (quantity > 0),
    CONSTRAINT chk_unit_price CHECK (unit_price >= 0),
    CONSTRAINT chk_waste CHECK (waste_amount >= 0),
    CONSTRAINT chk_dates CHECK (expiration_date >= transaction_date),
    CONSTRAINT chk_demand_level CHECK (demand_level IN ('Low', 'Medium', 'High')),
    CONSTRAINT uq_inventory_business_key
        UNIQUE (product_id, store_id, supplier_id, transaction_date)
);

CREATE INDEX idx_txn_product_date ON inventory_transactions(product_id, transaction_date);
CREATE INDEX idx_txn_store_date ON inventory_transactions(store_id, transaction_date);
CREATE INDEX idx_txn_supplier ON inventory_transactions(supplier_id);
CREATE INDEX idx_txn_expiration ON inventory_transactions(expiration_date);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_txn_updated_at
BEFORE UPDATE ON inventory_transactions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();