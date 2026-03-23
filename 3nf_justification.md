# 3NF Design Justification Report
**EAS 550 – Perishable Inventory Intelligence Platform**  
Team 9: Harish Sondagar, Sidharth Saholiya, Akaash Vontivillu, Riddhi Vaghani

---

## 1. Overview

The raw dataset for this project is a flat CSV containing information about perishable products, stores, suppliers, pricing, waste, promotions, and transaction dates. While this format is convenient for analysis, it contains repeated descriptive information across many rows. For example, the same product, store, supplier, region, and category values appear again and again for different transactions.

To create a clean OLTP-ready PostgreSQL database, we decomposed the flat dataset into multiple related tables and designed the schema to satisfy **Third Normal Form (3NF)**. This reduces redundancy, improves data integrity, and prevents common anomalies during insertion, update, and deletion.

The final schema contains the following tables:

- `regions`
- `categories`
- `stores`
- `suppliers`
- `products`
- `promotions`
- `product_promotions`
- `inventory_transactions`

---

## 2. Raw Dataset Analysis

The original CSV includes columns such as:

- `product_id`
- `product_name`
- `category`
- `store_id`
- `region`
- `supplier_id`
- `transaction_date`
- `expiration_date`
- `shelf_life_days`
- `storage_temp`
- `daily_demand`
- `selling_price`
- `initial_quantity`
- `units_wasted`
- `profit`
- `supplier_score`
- `is_promoted`
- `markdown_applied`
- `discount_pct`
- `spoilage_sensitivity`

In the raw file, many of these attributes are repeated for each transaction row even when they belong to a single logical entity such as a product, supplier, or store. This makes the flat structure unsuitable as a final relational design.

---

## 3. Entity Identification

After analyzing the dataset, we identified the following core entities:

| Entity | Description | Natural Key from Source |
|---|---|---|
| Region | Geographic grouping of stores | `region` |
| Category | Product classification | `category` |
| Store | Retail location | `store_id` |
| Supplier | Source/vendor of the product | `supplier_id` |
| Product | Product or SKU definition | `product_id` |
| Promotion | Discount / promotional event | derived from promotion attributes |
| Transaction | Individual inventory / sales event | `(product, store, supplier, transaction_date)` |

These entities were separated into distinct tables so that each table represents one subject only.

---

## 4. First Normal Form (1NF)

A relation is in **First Normal Form (1NF)** when:

- each column contains atomic values
- there are no repeating groups
- each row can be uniquely identified

The source CSV mostly contains atomic values already, but before loading we still cleaned and standardized the data in `ingest_data.py` by:

- trimming string fields
- converting date strings to proper `DATE` values
- converting numeric columns to numeric types
- handling missing values
- removing exact duplicate rows

After these transformations, each attribute stored in the database is atomic, so the schema satisfies **1NF**.

---

## 5. Second Normal Form (2NF)

A relation is in **Second Normal Form (2NF)** if:

- it is already in 1NF
- every non-key attribute depends on the whole key, not just part of it

In the raw dataset, transaction rows naturally correspond to a composite business event such as:

`(product_id, store_id, supplier_id, transaction_date)`

However, many non-key attributes in the raw CSV do **not** depend on the whole transaction. Examples:

- `product_name`, `shelf_life_days`, `storage_temp`, and `spoilage_sensitivity` depend only on **product**
- `region` depends on **store**
- `supplier_score` depends on **supplier**
- `category` is a property of the **product**

If these attributes were left inside the transaction table, they would create **partial dependencies**.

To remove these partial dependencies, we decomposed the data as follows:

- product-related attributes moved to `products`
- store-related regional information split into `stores` and `regions`
- supplier-related attributes moved to `suppliers`
- category names moved to `categories`

This decomposition removes partial dependency problems and satisfies **2NF**.

---

## 6. Third Normal Form (3NF)

A relation is in **Third Normal Form (3NF)** if:

- it is already in 2NF
- no non-key attribute depends on another non-key attribute

We checked the schema for **transitive dependencies** and removed them by separating lookup and parent entities.

### Examples of transitive dependencies removed

#### a. Region dependency
If `region_name` were stored directly in `stores` or `inventory_transactions`, then store-related rows would repeat the same region value many times.

Instead:

- `regions(region_id, region_name)`
- `stores(store_id, store_code, region_id)`

Now store rows reference the region through a foreign key.

---

#### b. Category dependency
If `category_name` were stored repeatedly inside product rows or transaction rows, any category correction would need many updates.

Instead:

- `categories(category_id, category_name)`
- `products(..., category_id, ...)`

This removes the transitive dependency from product to category name.

---

#### c. Supplier score dependency
`supplier_score` is a property of the supplier, not of an individual transaction.

Instead of storing it in every transaction row, it is stored once in:

- `suppliers(supplier_id, supplier_code, supplier_score)`

This avoids repeated updates and redundancy.

---

### Result
Each non-key attribute in each table depends only on the key of that table, the whole key, and nothing but the key. Therefore, the final schema is in **3NF**.

---

## 7. Many-to-Many Relationship Resolution

The dataset indicates that a product may be associated with promotions over time, and a promotion may apply to multiple products.

This creates a **many-to-many** relationship:

- one product can appear in many promotions
- one promotion can apply to many products

To resolve this, we introduced the bridge table:

- `product_promotions(product_id, promotion_id, valid_from, valid_to)`

This table:

- breaks the many-to-many relationship into two one-to-many relationships
- stores the time range of each promotion
- supports promotion history analysis

The composite primary key:

`(product_id, promotion_id, valid_from)`

ensures uniqueness for each product-promotion start date combination.

---

## 8. Fact Table Design

The table `inventory_transactions` is the central fact table of the OLTP schema. Each row represents a transaction-level inventory event.

It stores only attributes that belong to a specific transaction event, such as:

- product reference
- store reference
- supplier reference
- transaction date
- expiration date
- quantity
- unit price
- waste amount
- profit
- demand level
- promotion flag

The business key:

`(product_id, store_id, supplier_id, transaction_date)`

is enforced with a `UNIQUE` constraint so the ingestion process remains idempotent and duplicate transaction events are prevented.

---

## 9. Derived Attributes in the Load Process

Some values in the final schema are produced during ingestion from raw source columns:

- `demand_level` is derived from `daily_demand` by bucketing into `Low`, `Medium`, and `High`
- `spoilage_sensitivity` is standardized into `Low`, `Medium`, and `High`
- `unit_price` is mapped from `selling_price`
- `quantity` is mapped from `initial_quantity`
- `waste_amount` is mapped from `units_wasted`

These transformations happen in `ingest_data.py` before insertion into the normalized schema. This keeps the database structure consistent and easier to query.

---

## 10. Anomaly Prevention

The normalized design prevents the major anomalies found in flat files.

### Insertion anomaly
A new supplier, region, category, or product can be added without inserting a fake transaction row.

### Update anomaly
If a supplier score changes, only one row in `suppliers` needs to be updated.  
If a region name changes, only one row in `regions` needs to be updated.  
If a category name changes, only one row in `categories` needs to be updated.

### Deletion anomaly
Deleting a transaction row does not accidentally remove the only stored description of a product, supplier, store, or category.

---

## 11. Data Integrity Enforcement

The physical schema enforces integrity using PostgreSQL constraints:

- **PRIMARY KEY** on every main table
- **FOREIGN KEY** constraints between fact and dimension tables
- **UNIQUE** constraints on natural business identifiers such as:
  - `region_name`
  - `category_name`
  - `store_code`
  - `supplier_code`
  - `product_code`
  - `promotion_name`
- **CHECK** constraints for:
  - valid numeric ranges
  - positive quantity
  - valid spoilage and demand levels
  - valid date ordering (`expiration_date >= transaction_date`)
- **NOT NULL** constraints for required attributes
- **TIMESTAMPTZ** fields in `inventory_transactions` for auditing

These constraints ensure that the schema is not only normalized but also reliable and production-ready.

---

## 12. Design Trade-offs

A few practical choices were made in the final schema:

### `is_promotion` in `inventory_transactions`
The fact table stores a boolean `is_promotion` flag for quick filtering of transaction rows. This is useful for reporting and analysis, while detailed promotion membership is still preserved separately through `product_promotions`.

### Promotion abstraction
The raw dataset does not provide a full standalone promotion master table, so promotions are represented using promotion-related source fields such as discount percentage and promotion flags. This keeps the design relational while still supporting promotional analysis.

### Derived categorical buckets
Instead of storing raw continuous values everywhere, some fields are converted into analysis-friendly categories such as `Low`, `Medium`, and `High`. This improves consistency for downstream analytics and reporting.

---

## 13. Conclusion

The final PostgreSQL schema is a normalized design derived from the raw perishable inventory dataset. The design:

- separates core business entities into distinct tables
- resolves many-to-many relationships through a bridge table
- removes partial and transitive dependencies
- prevents insertion, update, and deletion anomalies
- enforces integrity with relational constraints
- supports idempotent ingestion into Neon using Pandas and SQLAlchemy

Therefore, the final schema satisfies the requirements of **Third Normal Form (3NF)** and is appropriate for the OLTP foundation of the project.