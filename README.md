# Perishable Inventory and Supply Chain Platform

This repository contains Phase 1 of the EAS 550 project: infrastructure provisioning, relational modeling, and data ingestion for a perishable goods dataset using Neon PostgreSQL, SQL, Python, Pandas, and SQLAlchemy.

## Project Overview

The goal of this phase was to take the raw perishable goods dataset and load it into a normalized PostgreSQL database hosted on Neon. The database schema was designed in Third Normal Form (3NF) to reduce redundancy, avoid update/insert/delete anomalies, and enforce data integrity using primary keys, foreign keys, unique constraints, and check constraints.

The raw dataset includes product, category, store, region, supplier, pricing, demand, waste, promotion, and date-related fields. These were transformed into a structured relational design suitable for analytics and future application development.

## What Has Been Completed

The following Phase 1 work has been completed:

- Created a Neon PostgreSQL database instance
- Designed an ERD for the dataset
- Built a normalized relational schema in PostgreSQL
- Wrote and ran `schema.sql` on Neon
- Wrote a Python ingestion pipeline in `ingest_data.py`
- Cleaned and transformed the raw CSV data using Pandas
- Loaded data into the database in the correct foreign key order
- Used `pandas.to_sql(..., if_exists="append")` as required
- Made the ingestion process idempotent using conflict-safe inserts
- Ran the ingestion script twice successfully
- Verified that the second run inserted 0 new inventory transaction rows
- Added an RBAC script in `security.sql` for the bonus requirement
- Used SQLAlchemy `NullPool` to avoid unnecessary idle Neon connections

## Database Design

The schema includes the following normalized tables:

- `regions`
- `categories`
- `stores`
- `suppliers`
- `products`
- `promotions`
- `product_promotions`
- `inventory_transactions`

### Design Notes

- `regions` stores unique region names
- `categories` stores unique product categories
- `stores` references `regions`
- `suppliers` stores supplier identifiers and supplier scores
- `products` stores product-level descriptive information and references `categories`
- `promotions` stores promotion names and discount percentages
- `product_promotions` resolves the many-to-many relationship between products and promotions
- `inventory_transactions` stores the main transactional records and references products, stores, and suppliers

The schema enforces data integrity using:

- `PRIMARY KEY`
- `FOREIGN KEY`
- `NOT NULL`
- `UNIQUE`
- `CHECK`

Additional indexes were created on `inventory_transactions` to improve lookup performance by product, store, supplier, and expiration date.

## Files in This Repository

- `schema.sql`  
  PostgreSQL schema definition for all project tables, constraints, indexes, and trigger

- `ingest_data.py`  
  Python ingestion pipeline that cleans, transforms, and loads the CSV data into Neon PostgreSQL

- `security.sql`  
  Bonus RBAC script that creates analyst and application roles with controlled privileges

- `3nf_justification.md`  
  Explanation of normalization and design choices

- `ERD.png`  
  Entity Relationship Diagram for the final schema

## Data Cleaning and Transformation

The ingestion pipeline performs the following steps:

- Reads the raw CSV file
- Standardizes column names
- Validates required columns
- Converts transaction and expiration date fields
- Removes rows with invalid dates
- Swaps incorrect date pairs where expiration is earlier than transaction date
- Converts numeric and boolean-like columns into proper types
- Fills missing values using safe defaults or medians where appropriate
- Buckets continuous demand values into `Low`, `Medium`, and `High`
- Buckets spoilage sensitivity into `Low`, `Medium`, and `High`
- Derives promotion flags based on promotion-related fields
- Maps raw dataset columns into the normalized schema fields
- Removes exact duplicate rows before loading

## Ingestion Strategy

The ingestion pipeline uses a temporary staging table called `stg_perishable_raw`.

The cleaned CSV data is first loaded into staging, and then inserted into the normalized tables in this order:

1. `regions`
2. `categories`
3. `stores`
4. `suppliers`
5. `products`
6. `promotions`
7. `product_promotions`
8. `inventory_transactions`

This order ensures that all foreign key dependencies are satisfied.

## Idempotency

The ingestion script is designed to be idempotent.

This means the script can be run multiple times without creating duplicate records or corrupting the database.

This was validated by running the script twice:

- first run: `inventory_transactions inserted this run: 100000`
- second run: `inventory_transactions inserted this run: 0`

Dimension and bridge table inserts also use conflict-safe logic to prevent duplication.

## Resource Monitoring and Connection Handling

Neon free-tier usage was considered during implementation.

To avoid keeping unnecessary idle connections open, the SQLAlchemy engine uses `NullPool`. This allows the connection to close after use and helps Neon auto-pause correctly instead of consuming compute hours due to open pooled connections.

## Security

Sensitive database credentials are not hardcoded in the Python script.

The ingestion script reads `DATABASE_URL` from environment variables using a local `.env` file.

The repository is intended to exclude `.env` from version control.

For the bonus requirement, `security.sql` creates two application roles:

- `perishable_analyst`  
  Select-only access

- `perishable_app_user`  
  Select, insert, and update access

## How to Run

### 1. Add environment variable

Create a `.env` file in the project root:

```env
DATABASE_URL= (our url that we got from neon 