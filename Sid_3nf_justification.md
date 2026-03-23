# 3NF Design Justification Report
**EAS 550 – Perishable Inventory Intelligence Platform**  
Team 9: Harish Sondagar, Sidharth Saholiya, Akaash Vontivillu, Riddhi Vaghani

---

## 1. Overview

Our schema transforms the flat Kaggle CSV into eight relational tables. The design
targets Third Normal Form (3NF) for the OLTP layer, eliminating update anomalies
and redundancy while preserving the information content needed for downstream
analytics models in dbt.

---

## 2. Entity Identification

From the raw dataset we identified seven natural entity clusters:

| Entity | Natural Key in CSV | Role |
|---|---|---|
| Region | region (string) | Geography of stores |
| Category | category (string) | Product classification |
| Store | store_id | Physical retail location |
| Supplier | supplier_id | Goods provider |
| Product | product_id | SKU definition |
| Promotion | promotion_name | Marketing event |
| Transaction | (product, store, supplier, date) | Operational event |

---

## 3. Normalization Walk-through

### First Normal Form (1NF)
The flat CSV already satisfies atomicity — each field holds a single, indivisible
value. We standardised categorical fields (e.g. 'Low'/'Medium'/'High') and
converted date strings to proper `DATE` types, eliminating any implicit encoding.

### Second Normal Form (2NF)
In the original flat file, attributes like `shelf_life`, `storage_temperature`,
and `spoilage_sensitivity` are properties of the *product*, yet they repeat on
every transaction row. They are partially dependent on the composite natural key
`(product_id, store_id, supplier_id, transaction_date)` — specifically, they
depend only on `product_id`. Moving them to the `products` table removes this
partial dependency.

Similarly, `region_name` depends only on `store_id` (not on the full transaction
key), so it was extracted into `stores → regions`.

### Third Normal Form (3NF)
After reaching 2NF, we audited for transitive dependencies:

- **region_name → region_id → store_id**: If `region_name` were stored in
  `stores`, updating a region's name would require touching every store row in
  that region. The `regions` table eliminates this transitive dependency.

- **category_name → category_id → product_id**: Same reasoning as above;
  `categories` holds the canonical category name.

- **supplier_score → supplier_id → transaction_id**: Supplier score is an
  attribute of the supplier, not of any individual transaction. It lives in
  `suppliers` so a score update requires changing exactly one row.

---

## 4. Many-to-Many Relationship Resolution

The dataset implies a M:M relationship between **products** and **promotions**:
a single product can appear in multiple promotions across time, and a promotion
can cover multiple products.

This is resolved via the `product_promotions` bridge table with the composite
primary key `(product_id, promotion_id, valid_from)`. The `valid_from` / `valid_to`
date columns allow temporal tracking of which products were on promotion and when,
supporting markdown-effectiveness analysis.

---

## 5. Schema Anomaly Prevention

| Anomaly | How our design prevents it |
|---|---|
| **Insertion** | Dimension rows (regions, categories, etc.) can be inserted without requiring a transaction row. No forced null values. |
| **Update** | Changing a supplier's score requires updating one row in `suppliers`. Changing a region name requires one row in `regions`. No fan-out updates. |
| **Deletion** | Deleting a transaction does not remove product or supplier records. Cascade rules are intentionally absent from fact-to-dimension FKs. |

---

## 6. Data Integrity Constraints

Every table uses the full set of PostgreSQL constraint mechanisms:

- **PRIMARY KEY**: Surrogate SERIAL keys on all tables; natural keys enforced via UNIQUE.
- **FOREIGN KEY**: All dimension references in `inventory_transactions` use FK constraints.
  Load order in `ingest_data.py` respects dependency order to satisfy these at runtime.
- **NOT NULL**: Applied to every non-optional attribute.
- **UNIQUE**: Applied to all natural keys (`store_code`, `product_code`, `supplier_code`,
  `category_name`, `region_name`, `promotion_name`).
- **CHECK**: Domain constraints on enumerated values (`demand_level`, `spoilage_sensitivity`,
  `spoilage_sensitivity`), numeric ranges (`supplier_score BETWEEN 0 AND 100`,
  `quantity > 0`, `unit_price >= 0`), and temporal logic
  (`expiration_date >= transaction_date`).
- **TIMESTAMPTZ**: Used for `created_at` / `updated_at` audit columns; timezone-aware
  to avoid ambiguity in distributed cloud environments.

---

## 7. Design Trade-offs and Decisions

**Supplier score in `suppliers`, not denormalised into transactions**  
Storing `supplier_score` per-transaction would allow historical score tracking but
would bloat the fact table and cause update anomalies. Our current design stores
the current score; a future SCD Type 2 extension in the dbt layer can track history
without changing the OLTP schema.

**`is_promotion` boolean in transactions**  
We retain a denormalised `is_promotion` flag on the fact table for OLAP query
performance (filtering promoted vs. non-promoted transactions without a join).
This controlled redundancy is intentional and documented; it is consistent with
the `product_promotions` bridge table but avoids a mandatory join for the most
common analytical query pattern.

**No `price` column in `products`**  
Unit price varies per transaction (markdown, promotion, negotiated rate). Storing
it in `products` would create an update anomaly every time pricing changes.
It lives exclusively in `inventory_transactions`.

**NullPool for SQLAlchemy**  
Neon's free tier provides 100 CU-hours/month. Idle connections prevent the
serverless compute from pausing. `NullPool` ensures every connection is closed
immediately after use, allowing Neon to pause after 5 minutes of inactivity.

---

## 8. Summary Table Count

| Table | Type | Rows (estimated) |
|---|---|---|
| regions | Dimension | ~10 |
| categories | Dimension | ~5 |
| stores | Dimension | ~100 |
| suppliers | Dimension | ~50 |
| products | Dimension | ~200 |
| promotions | Dimension | ~5 |
| product_promotions | Bridge | ~500 |
| inventory_transactions | Fact | ~50,000+ |
