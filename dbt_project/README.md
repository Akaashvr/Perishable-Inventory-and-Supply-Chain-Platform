# dbt Project

This folder contains the dbt implementation for the analytics layer of the project.

## Contents

* `models/` – Dimension and fact tables (Star Schema)
* `analyses/` – Advanced analytical SQL queries
* `schema.yml` – Data quality tests (not_null, unique, relationships)

## Usage

```bash
dbt run
dbt test
```

This project transforms the OLTP schema into an analytics-ready Star Schema and validates data quality using dbt.
