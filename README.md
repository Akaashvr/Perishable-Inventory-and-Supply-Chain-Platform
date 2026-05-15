# Perishable Inventory and Supply Chain Platform

EAS 550, Team 9. A three phase data engineering project that takes a raw perishable goods CSV, normalises it into a PostgreSQL database on Neon, builds a dbt Star Schema with tests and CI on top of it, and serves the result through a live Streamlit dashboard deployed on Render.

Live app: https://perishable-inventory-and-supply-chain.onrender.com/

Phase 1  https://youtu.be/H3kzdN9K7yk
Final phase demo:

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

## Phase 1 recap

Phase 1 produced a PostgreSQL schema in third normal form, an idempotent Python ingestion pipeline, and a two role security model.

The tables are regions, categories, stores, suppliers, products, promotions, product_promotions, and inventory_transactions. Integrity is enforced through primary keys, foreign keys, NOT NULL, UNIQUE, and CHECK constraints. The justification for the normalisation choices is written up in `3nf_justification.md` and `Team9_ProjectPhase_1.pdf`.

The ingestion script (`ingest_data.py`) cleans the raw CSV, validates rows, buckets demand and spoilage into Low, Medium, and High, stages everything into a temporary table, and then loads the dimensions and the fact table with ON CONFLICT DO NOTHING. Reruns never duplicate data.

For security, `security.sql` defines two roles. `perishable_analyst` only has SELECT permissions, which is what the dashboard uses. `perishable_app_user` has SELECT, INSERT, and UPDATE for write workflows.

## Phase 2 recap

Phase 2 built a Star Schema on top of the OLTP tables using dbt Core. The fact table is `fact_inventory`. It joins to `dim_product`, `dim_store`, and `dim_supplier`. The relationships are shown in `star_schema.png`.

Three analytical SQL files in `dbt_project/analyses/` answer business questions. There is a waste analysis that uses a CTE, a supplier ranking built on `RANK() OVER (...)`, and a 7 day rolling average for demand. After adding a composite index on `(product_id, transaction_date)`, the moving average query dropped from around 850 ms to around 140 ms. The numbers are in `dbt_project/performance_report.md`.

For data quality, dbt tests for not_null, unique, and relationships run on every pull request through `.github/workflows/ci.yml`. The same workflow also lints SQL with SQLFluff.

## Phase 3, the live dashboard

Phase 3 wraps the Star Schema in a Streamlit application and ships it to Render with continuous deployment from GitHub.

### How it looks

The app uses a dark theme that runs through the supply chain visual cues: fresh produce green, ripeness orange, cold chain blue, and a deep navy hex grid background that suggests a distribution network. Icons come from Remixicon and the typography is Inter. No images in the background, only CSS gradients.

The layout has three regions. A collapsible left sidebar holds the filters. The main column has a top tab navigation with seven pages. The right column hosts a query assistant powered by Gemini that can read the database and switch tabs on your behalf.

![Dashboard preview](docs/dashboard_preview.svg)

### The seven pages

Overview is the landing page. Eight KPI cards (revenue, profit, waste units, units moved, transactions, products, stores, suppliers) sit above two charts: a smoothed spline showing daily revenue, profit and waste, and a 7 day moving average for revenue.

Products ranks products by revenue, profit, units, or waste, with a slider to pick the top N. Underneath is a category breakdown with a grouped bar chart and a donut for revenue share.

Suppliers is built around a window function. The leaderboard table includes profit rank and waste rank computed with `RANK() OVER (...)`. A bubble chart above it plots supplier score against profit, sized by revenue and coloured by waste.

Regions shows a grouped bar chart per region, a summary table, and a Region by Category revenue heatmap.

Waste opens with three KPIs (total waste units, total units moved, overall waste rate). Two bars compare absolute waste and waste rate across the spoilage sensitivity buckets. Below that is a ranking of the worst offending products.

Promotions is the simplest page. Two side by side cards for promoted versus non-promoted, plus a grouped bar comparing revenue, profit, and waste across the two groups.

Data Explorer is a transaction level grid. Search by product, category, region, or store, adjust the row limit, and download the current selection as CSV.

### How the spec is met

Step 3.1 asked for two dynamic visualisations and one interactive widget. The Overview page alone has two charts. Across all pages there are over ten Plotly visualisations and at least six interactive widgets. Every query function in `app/queries.py` is wrapped in `@st.cache_data(ttl=600)`, and the SQLAlchemy engine is wrapped in `@st.cache_resource`.

Step 3.2 asked for secure connection pooling and a live query against the database, not flat files. The engine in `app/db.py` uses SQLAlchemy QueuePool with a pool size of 5, a max overflow of 5, `pool_pre_ping=True`, `pool_recycle=300`, and `sslmode=require`. `DATABASE_URL` comes from `os.getenv`, never from source code. The dashboard does not use `pd.read_csv` anywhere. Every chart fetches from Postgres.

Step 3.3 asked for continuous deployment on Render with environment variable based secrets. The `render.yaml` Blueprint sets `autoDeploy: true`, so every push to main rebuilds. `DATABASE_URL` is marked `sync: false`, which means Render stores it only inside the dashboard, not in the repo.

Step 3.4 asked for a professional README. That is this file, along with the architecture diagram in `docs/architecture.svg`.

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

![End to end architecture](docs/architecture.svg)

Raw CSV becomes normalised tables through `ingest_data.py`. dbt turns the OLTP tables into a Star Schema. The Streamlit app reads the Star Schema through a pooled SQLAlchemy engine and renders it with Plotly. Render rebuilds the app on every push to main.

---

## Screenshots

Once the app is live, capture the seven pages and save them under `docs/` as `screenshot_overview.png`, `screenshot_products.png`, and so on, then drop them into this section.

---

## Team and AI disclosure

EAS 550, Team 9. The per phase breakdown of where generative AI was used is in `ai_usage.md`. Schema design, dimensional modelling, query authoring, and final code were owned by the team. AI was used for boilerplate generation, prose review, and specific syntax help.
