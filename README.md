# Perishable Inventory and Supply Chain Platform

EAS 550, Team 9. A three phase data engineering project that takes a raw perishable goods CSV, normalises it into a PostgreSQL database on Neon, builds a dbt Star Schema with tests and CI on top of it, and serves the result through a live Streamlit dashboard deployed on Render.

Live app: https://perishable-inventory-and-supply-chain.onrender.com/

Phase 1:  https://youtu.be/H3kzdN9K7yk  

Final Phase Demo Video: https://youtu.be/V4FKrAy5uCE  

---

## What is in the repo

```
.
├── app/                           Phase 3 dashboard
│   ├── streamlit_app.py           Entry point with all tabs
│   ├── db.py                      Pooled SQLAlchemy engine
│   ├── queries.py                 Cached, parameterised SQL
│   ├── theme.py                   CSS, colour tokens, Plotly template
│   └── ai_chat.py                 Gemini query assistant
├── dbt_project/                   Phase 2 dbt models, tests, analyses
├── .github/workflows/
│   ├── ci.yml                     Phase 2 dbt CI
│   └── streamlit-app.yml          Phase 3 Streamlit smoke test
├── docs/                          Architecture and dashboard diagrams
├── schema.sql                     Phase 1 OLTP DDL
├── security.sql                   Phase 1 RBAC roles
├── ingest_data.py                 Phase 1 ingestion pipeline
├── render.yaml                    Render Blueprint
├── Procfile                       Render start command
├── runtime.txt                    Python version pin
├── requirements.txt               Pinned Python dependencies
├── .env.example                   Template for environment variables
└── ai_usage.md                    AI tool disclosure
```

---


## Phase 1: OLTP Design and Data Ingestion

In Phase 1, we designed a normalized schema (3NF) to store the dataset efficiently and avoid redundancy.

The raw dataset includes product, category, store, region, supplier, pricing, demand, waste, promotion, and date-related fields. These were transformed into a structured relational design suitable for analytics and future application development.
### What we did

## What Has Been Completed
* Created a Neon PostgreSQL database
* Designed an ERD for the dataset
* Built a normalized schema using SQL
* Implemented data cleaning and ingestion using Python (Pandas + SQLAlchemy)
* Loaded data into the database in the correct order to maintain foreign key constraints
* Ensured the ingestion process was **idempotent** (running it multiple times does not create duplicates)
* Added role-based access control using SQL

The following Phase 1 work has been completed:
### Main tables

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
* `regions`
* `categories`
* `stores`
* `suppliers`
* `products`
* `promotions`
* `product_promotions`
* `inventory_transactions`

## Database Design
### Files

- `regions`
- `categories`
- `stores`
- `suppliers`
- `products`
- `promotions`
- `product_promotions`
- `inventory_transactions`
---

### Design Notes
## Phase 2: Analytics with dbt

- `regions` stores unique region names
- `categories` stores unique product categories
- `stores` references `regions`
- `suppliers` stores supplier identifiers and supplier scores
- `products` stores product-level descriptive information and references `categories`
- `promotions` stores promotion names and discount percentages
- `product_promotions` resolves the many-to-many relationship between products and promotions
- `inventory_transactions` stores the main transactional records and references products, stores, and suppliers
In Phase 2, we built an analytics layer on top of the normalized database using dbt.

The schema enforces data integrity using:
### Star Schema

- `PRIMARY KEY`
- `FOREIGN KEY`
- `NOT NULL`
- `UNIQUE`
- `CHECK`
We transformed the OLTP schema into a Star Schema to support analytical queries:

Additional indexes were created on `inventory_transactions` to improve lookup performance by product, store, supplier, and expiration date.
* `fact_inventory` (central fact table)
* `dim_product`
* `dim_store`
* `dim_supplier`

## Files in This Repository

- `schema.sql`  
  PostgreSQL schema definition for all project tables, constraints, indexes, and trigger
---

- `ingest_data.py`  
  Python ingestion pipeline that cleans, transforms, and loads the CSV data into Neon PostgreSQL
### dbt Models

- `security.sql`  
  Bonus RBAC script that creates analyst and application roles with controlled privileges
We used dbt to create modular SQL transformations:

- `3nf_justification.md`  
  Explanation of normalization and design choices
* Built dimension and fact tables inside `dbt_project/models`
* Used joins and transformations to create clean, analysis-ready data
* Organized everything in a structured and reusable way
---

## Data Cleaning and Transformation
### Data Quality Checks

The ingestion pipeline performs the following steps:
We added dbt tests to make sure the data is reliable:

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
* `not_null` tests on important fields
* `unique` tests on primary keys
* Basic checks to ensure consistency between fact and dimension tables

## Ingestion Strategy
---

The ingestion pipeline uses a temporary staging table called `stg_perishable_raw`.
### Analytical Queries

The cleaned CSV data is first loaded into staging, and then inserted into the normalized tables in this order:
We wrote three SQL queries to extract insights:

1. `regions`
2. `categories`
3. `stores`
4. `suppliers`
5. `products`
6. `promotions`
7. `product_promotions`
8. `inventory_transactions`
1. **Waste analysis** (using CTEs)
2. **Supplier ranking** (using window functions)
3. **Demand trends** (using moving averages over time)

This order ensures that all foreign key dependencies are satisfied.
These are located in `dbt_project/analyses`.

## Idempotency
---

The ingestion script is designed to be idempotent.
### Performance Optimization

This means the script can be run multiple times without creating duplicate records or corrupting the database.
We analyzed query performance using `EXPLAIN ANALYZE`.

This was validated by running the script twice:
* Initially, the query performed a sequential scan (~850 ms)
* We added an index on `(product_id, transaction_date)`
* After optimization, execution time reduced to ~140 ms (~6x faster)

- first run: `inventory_transactions inserted this run: 100000`
- second run: `inventory_transactions inserted this run: 0`
Details are included in `performance_report.md`.

Dimension and bridge table inserts also use conflict-safe logic to prevent duplication.
---

## Resource Monitoring and Connection Handling
### CI/CD Pipeline

Neon free-tier usage was considered during implementation.
We set up a CI/CD workflow using GitHub Actions:

To avoid keeping unnecessary idle connections open, the SQLAlchemy engine uses `NullPool`. This allows the connection to close after use and helps Neon auto-pause correctly instead of consuming compute hours due to open pooled connections.
* Runs automatically on pull requests
* Installs dbt and executes tests
* Helps ensure code quality before merging

## Security
Note: The pipeline may fail due to missing database credentials in GitHub. In a real-world setup, this would be handled using GitHub Secrets.

Sensitive database credentials are not hardcoded in the Python script.
---

The ingestion script reads `DATABASE_URL` from environment variables using a local `.env` file.
### dbt Documentation

The repository is intended to exclude `.env` from version control.
We generated interactive documentation using:

For the bonus requirement, `security.sql` creates two application roles:
```bash
dbt docs generate
dbt docs serve
```

- `perishable_analyst`  
  Select-only access
This allows us to view models, columns, and relationships in a UI.

- `perishable_app_user`  
  Select, insert, and update access
---

## How to Run
## How to Run the Project

### 1. Add environment variable
### 1. Set up environment variables

Create a `.env` file in the project root:
Create a `.env` file:

```env
DATABASE_URL= (our url that we got from neon)
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
![Neon Preview 1](images/neondb.png)
![Neon Preview 1](images/neonoverview.png)
![Neon Preview 1](images/neontable.png)
---

## Phase 1 recap

Phase 1 produced a PostgreSQL schema in third normal form, an idempotent Python ingestion pipeline, and a two role security model.

The tables are regions, categories, stores, suppliers, products, promotions, product_promotions, and inventory_transactions. Integrity is enforced through primary keys, foreign keys, NOT NULL, UNIQUE, and CHECK constraints. The justification for the normalisation choices is written up in `3nf_justification.md` and `Team9_ProjectPhase_1.pdf`.

The ingestion script (`ingest_data.py`) cleans the raw CSV, validates rows, buckets demand and spoilage into Low, Medium, and High, stages everything into a temporary table, and then loads the dimensions and the fact table with ON CONFLICT DO NOTHING. Reruns never duplicate data.

For security, `security.sql` defines two roles. `perishable_analyst` only has SELECT permissions, which is what the dashboard uses. `perishable_app_user` has SELECT, INSERT, and UPDATE for write workflows.

## Phase 2 recap

Phase 2 built a Star Schema on top of the OLTP tables using dbt Core. The fact table is `fact_inventory`. It joins to `dim_product`, `dim_store`, and `dim_supplier`. 

Three analytical SQL files in `dbt_project/analyses/` answer business questions. There is a waste analysis that uses a CTE, a supplier ranking built on `RANK() OVER (...)`, and a 7 day rolling average for demand. After adding a composite index on `(product_id, transaction_date)`, the moving average query dropped from around 850 ms to around 140 ms. The numbers are in `dbt_project/performance_report.md`.

For data quality, dbt tests for not_null, unique, and relationships run on every pull request through `.github/workflows/ci.yml`. The same workflow also lints SQL with SQLFluff.

## Phase 3, the live dashboard

Phase 3 wraps the Star Schema in a Streamlit application and ships it to Render with continuous deployment from GitHub.

### How it looks

The app uses a dark theme that runs through the supply chain visual cues: fresh produce green, ripeness orange, cold chain blue, and a deep navy hex grid background that suggests a distribution network. Icons come from Remixicon and the typography is Inter. No images in the background, only CSS gradients.

The layout has three regions. A collapsible left sidebar holds the filters. The main column has a top tab navigation with seven pages. The right column hosts a query assistant powered by Gemini that can read the database and switch tabs on your behalf.

![Dashboard preview](images/dashboard_preview.png)

### The seven pages

Overview is the landing page. Eight KPI cards (revenue, profit, waste units, units moved, transactions, products, stores, suppliers) sit above two charts: a smoothed spline showing daily revenue, profit and waste, and a 7 day moving average for revenue.

Products ranks products by revenue, profit, units, or waste, with a slider to pick the top N. Underneath is a category breakdown with a grouped bar chart and a donut for revenue share.

Suppliers is built around a window function. The leaderboard table includes profit rank and waste rank computed with `RANK() OVER (...)`. A bubble chart above it plots supplier score against profit, sized by revenue and coloured by waste.

Regions shows a grouped bar chart per region, a summary table, and a Region by Category revenue heatmap.

Waste opens with three KPIs (total waste units, total units moved, overall waste rate). Two bars compare absolute waste and waste rate across the spoilage sensitivity buckets. Below that is a ranking of the worst offending products.

Promotions is the simplest page. Two side by side cards for promoted versus non-promoted, plus a grouped bar comparing revenue, profit, and waste across the two groups.

Data Explorer is a transaction level grid. Search by product, category, region, or store, adjust the row limit, and download the current selection as CSV.

### How the spec is met

The first step here is for two dynamic visualisations and one interactive widget. The Overview page alone has two charts. Across all pages there are over ten Plotly visualisations and at least six interactive widgets. Every query function in `app/queries.py` is wrapped in `@st.cache_data(ttl=600)`, and the SQLAlchemy engine is wrapped in `@st.cache_resource`.

So the next step is for secure connection pooling and a live query against the database, not flat files. The engine in `app/db.py` uses SQLAlchemy QueuePool with a pool size of 5, a max overflow of 5, `pool_pre_ping=True`, `pool_recycle=300`, and `sslmode=require`. `DATABASE_URL` comes from `os.getenv`, never from source code. The dashboard does not use `pd.read_csv` anywhere. Every chart fetches from Postgres.

Then asked for continuous deployment on Render with environment variable based secrets. The `render.yaml` Blueprint sets `autoDeploy: true`, so every push to main rebuilds. `DATABASE_URL` is marked `sync: false`, which means Render stores it only inside the dashboard, not in the repo.

### The query assistant

The right panel is a Gemini 2.5 Flash chatbot that knows the Star Schema and the dashboard structure. It has two tools available through function calling: `query_database` for read only SELECT or WITH statements, and `navigate_to_tab` for opening a specific tab with optional filters applied.

A few example prompts that work:

* "Which region has the highest waste?" runs a SQL aggregation and answers with the actual number.
* "Open the Waste tab for the West region" switches to the Waste tab and pre fills the regions filter.
* "What does spoilage_sensitivity mean?" answers from the schema description without hitting the database.

The SQL it generates is sandboxed. INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, COPY, EXECUTE, VACUUM, ANALYZE, LOCK, and MERGE are all rejected before the query reaches the database. Multi statement attempts (anything with a semicolon) are also rejected. Every accepted query is capped at 50 rows.

The API key for Gemini sits in `app/ai_chat.py`. For production use, swap it out for `os.getenv("GEMINI_API_KEY", "")`.

---

## Run it locally

Clone the repo, create a virtual environment, and install the dependencies.

```bash
git clone https://github.com/Akaashvr/Perishable-Inventory-and-Supply-Chain-Platform.git
cd Perishable-Inventory-and-Supply-Chain-Platform

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Copy the env template and paste your Neon connection string.

```bash
cp .env.example .env
```

Your `.env` should look like this. Use the pooled connection string from the Neon dashboard (the hostname contains `-pooler`).

```env
DATABASE_URL=postgresql://perishable_analyst:****@ep-xxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

If your Neon database is empty, run Phase 1 and Phase 2 first.

```bash
psql "$DATABASE_URL" -f schema.sql
psql "$DATABASE_URL" -f security.sql
python ingest_data.py --csv perishable_goods_management.csv

cd dbt_project
dbt run
dbt test
cd ..
```

Then launch the dashboard.

```bash
streamlit run app/streamlit_app.py
```

The app opens at http://localhost:8501. If you see "Database: Connected" in the sidebar and the KPI cards show numbers, the local setup is good.

---

## Deploy to Render

The Blueprint option is faster, so try that first.

![Render Preview](images/render.png)

### Blueprint

Push the repo to GitHub. In Render, click New, then Blueprint, and pick the repo. Render reads `render.yaml` automatically and proposes a service called `perishable-dashboard`. When prompted, paste your Neon `DATABASE_URL`. Click Apply.

The first build takes three to five minutes. After that, every push to main triggers a rebuild because `autoDeploy: true` is set in the Blueprint.

### Manual Web Service

For manual setup, click New, then Web Service, and connect the repo. Set the environment to Python 3.

Build command:

```
pip install --upgrade pip && pip install -r requirements.txt
```

Start command:

```
streamlit run app/streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false
```

Set the health check path to `/_stcore/health`. Add `DATABASE_URL` in the Environment tab.

### Cold starts on the free tier

Render's free tier shuts the container down after a period of inactivity. The first request after a long pause takes 30 to 60 seconds while the service wakes up. This is normal. Do not panic during the demo, just wait.

---

## Security notes

No secrets in the repo. `DATABASE_URL` is read from `os.getenv`, loaded from `.env` locally, and injected by Render in production. `.env` is in `.gitignore`. The `render.yaml` Blueprint uses `sync: false` on the database URL so the value stays in the Render dashboard only.

SSL is enforced through `connect_args={"sslmode": "require"}` in `db.py`. Neon requires this anyway, and the engine refuses any unencrypted attempt.

The QueuePool keeps five warm connections and allows up to five more on burst, so the dashboard cannot accidentally drain Neon's free tier compute budget.

Every SQL query in `app/queries.py` uses bind parameters through SQLAlchemy `text()`. No user input is ever string formatted into a query, including the values coming out of the sidebar filters.

The dashboard only reads. Pointing `DATABASE_URL` at the `perishable_analyst` role enforces least privilege.

When the database is briefly unreachable (Neon's free tier compute waking up, for example), `run_query()` catches the error, shows a Streamlit error message, and returns an empty DataFrame. The dashboard itself stays up.

---

## Performance notes

The SQLAlchemy engine is cached for the lifetime of the Streamlit worker through `@st.cache_resource`, so the pool is not recreated on every interaction. Query results are cached with `@st.cache_data(ttl=600)`. Ten minutes is plenty for batch ingested data and keeps Neon CU usage low.

`pool_pre_ping=True` quietly replaces dead connections, which matters because Neon auto pauses idle compute on the free tier. `pool_recycle=300` rotates connections older than five minutes so the pool stays fresh.

All aggregation, ranking, and moving averages run in Postgres. Streamlit only receives small result frames and hands them to Plotly. No large DataFrames cross the network.

---

## Continuous integration

Two workflows live in `.github/workflows/`.

`ci.yml` lints SQL with SQLFluff and runs `dbt test` on every pull request against main. It needs `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, and `DB_NAME` set as GitHub Actions secrets.

`streamlit-app.yml` compiles every Python file and runs a smoke import test on the helper modules whenever anything under `app/`, `requirements.txt`, or `.streamlit/` changes. Syntax errors get caught before they reach Render.

---

## Architecture

![End to end architecture](images/architecture.svg)

Raw CSV becomes normalised tables through `ingest_data.py`. dbt turns the OLTP tables into a Star Schema. The Streamlit app reads the Star Schema through a pooled SQLAlchemy engine and renders it with Plotly. Render rebuilds the app on every push to main.

---


## Team and AI disclosure

EAS 550, Team 9. The per phase breakdown of where generative AI was used is in `ai_usage.md`. Schema design, dimensional modelling, query authoring, and final code were owned by the team. AI was used for boilerplate generation, prose review, and specific syntax help.
