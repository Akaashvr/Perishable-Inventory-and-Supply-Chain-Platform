# Perishable Inventory and Supply Chain Platform

This repository contains our EAS 550 project, where we built a complete data pipeline for a perishable goods dataset. The project is divided into two phases:

* **Phase 1:** Database design, normalization, and data ingestion
* **Phase 2:** Data transformation, analytics, quality checks, and CI/CD

---

## Project Overview

The goal of this project was to take a raw perishable goods dataset and turn it into a structured system that supports both reliable storage and analytical queries.

In Phase 1, we focused on building a clean relational database using PostgreSQL. In Phase 2, we transformed that data into an analytics-friendly format using dbt and added testing, performance improvements, and automation.

---

## Phase 1: OLTP Design and Data Ingestion

In Phase 1, we designed a normalized schema (3NF) to store the dataset efficiently and avoid redundancy.

### What we did

* Created a Neon PostgreSQL database
* Designed an ERD for the dataset
* Built a normalized schema using SQL
* Implemented data cleaning and ingestion using Python (Pandas + SQLAlchemy)
* Loaded data into the database in the correct order to maintain foreign key constraints
* Ensured the ingestion process was **idempotent** (running it multiple times does not create duplicates)
* Added role-based access control using SQL

### Main tables

* `regions`
* `categories`
* `stores`
* `suppliers`
* `products`
* `promotions`
* `product_promotions`
* `inventory_transactions`

### Files

* `schema.sql` – database schema
* `ingest_data.py` – data ingestion pipeline
* `security.sql` – RBAC setup
* `3nf_justification.md` – normalization explanation
* `ERD.png` – database design diagram

---

## Phase 2: Analytics with dbt

In Phase 2, we built an analytics layer on top of the normalized database using dbt.

### Star Schema

We transformed the OLTP schema into a Star Schema to support analytical queries:

* `fact_inventory` (central fact table)
* `dim_product`
* `dim_store`
* `dim_supplier`

The diagram is available in **`star_schema.png`**.

---

### dbt Models

We used dbt to create modular SQL transformations:

* Built dimension and fact tables inside `dbt_project/models`
* Used joins and transformations to create clean, analysis-ready data
* Organized everything in a structured and reusable way

---

### Data Quality Checks

We added dbt tests to make sure the data is reliable:

* `not_null` tests on important fields
* `unique` tests on primary keys
* Basic checks to ensure consistency between fact and dimension tables

---

### Analytical Queries

We wrote three SQL queries to extract insights:

1. **Waste analysis** (using CTEs)
2. **Supplier ranking** (using window functions)
3. **Demand trends** (using moving averages over time)

These are located in `dbt_project/analyses`.

---

### Performance Optimization

We analyzed query performance using `EXPLAIN ANALYZE`.

* Initially, the query performed a sequential scan (~850 ms)
* We added an index on `(product_id, transaction_date)`
* After optimization, execution time reduced to ~140 ms (~6x faster)

Details are included in `performance_report.md`.

---

### CI/CD Pipeline

We set up a CI/CD workflow using GitHub Actions:

* Runs automatically on pull requests
* Installs dbt and executes tests
* Helps ensure code quality before merging

Note: The pipeline may fail due to missing database credentials in GitHub. In a real-world setup, this would be handled using GitHub Secrets.

---

### dbt Documentation

We generated interactive documentation using:

```bash
dbt docs generate
dbt docs serve
```

This allows us to view models, columns, and relationships in a UI.

---

## How to Run the Project

### 1. Set up environment variables

Create a `.env` file:

```env
DATABASE_URL=your_neon_database_url
```

---

### 2. Run ingestion

```bash
python ingest_data.py
```

---

### 3. Run dbt models

```bash
cd dbt_project
dbt run
```

---

### 4. Run tests

```bash
dbt test
```

---

## Summary

This project demonstrates a complete data pipeline:

* Structured OLTP design (Phase 1)
* Star Schema transformation (Phase 2)
* Data validation using dbt tests
* Analytical query development
* Performance optimization using indexing
* CI/CD automation using GitHub Actions

---

## Demo

YouTube link: https://youtu.be/H3kzdN9K7yk
