# Runbook: college demo (Python ingestion + Snowflake)

Status: the loader (744 rows), dbt (run, 5 tests, validation) and Streamlit have run against Snowflake and passed. **Airflow is partly working:** the ingestion task succeeds, but `dbt run` fails inside the container with a dbt parse-cache `KeyError`, because the Windows-made `dbt_project/target/partial_parse.msgpack` clashes with the Linux container. Until the DAG is fixed (add `--no-partial-parse`, or delete that cache file before running Airflow), run the dbt steps in section 4 from the host. Do the steps in order. Never paste keys, secrets or `.env` values into chat or commits.

**Why Python and not Airbyte:** Airbyte Cloud was configured (File source to Snowflake) but could not sync because of an insufficient-credits restriction. The team will not add a payment method, so a Python loader replaced Airbyte. The Snowflake names `AIRBYTE_USER` and `AIRBYTE_ROLE` are historical: they are now the Python loader's identity, with the `airbyte` key.

## 1. Snowflake (already done)
`snowflake/setup.sql` created the warehouse, database `ECOMMERCE_ANALYTICS`, schemas `RAW`, `AIRBYTE_INTERNAL`, `STAGING`, `ANALYTICS`, three roles and three key-pair service users. Keys are in `C:\Users\<you>\.snowflake\` (outside the repo), created by `snowflake\make_keys.ps1`. The Snowflake trial lasts 30 days from signup; after that the account is suspended.

## 2. Local settings
Copy `.env.example` to `.env` and fill in `SNOWFLAKE_ACCOUNT` (Snowsight: your name > Account > View account details) and the three key paths (forward slashes). Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml`.

## 3. Check the loader offline, then read-only
```powershell
.\.venv\Scripts\python.exe ingestion\load_sample_to_snowflake.py --dry-run   # offline: validates the 744-row CSV
.\.venv\Scripts\python.exe ingestion\test_load_sample.py                      # offline tests with a fake connection
.\.venv\Scripts\python.exe ingestion\load_sample_to_snowflake.py --check     # first Snowflake contact: READ-ONLY
```
`--check` logs in as `AIRBYTE_USER`, prints the user, role, database and warehouse, lists the table names in `RAW` and `AIRBYTE_INTERNAL`, and says whether `RAW.ONLINE_RETAIL_SAMPLE` is absent, created by the loader, or unexpected. It changes nothing.

## 4. Load, transform, validate
```powershell
# load RAW.ONLINE_RETAIL_SAMPLE (creates it if absent; replaces all rows in one transaction; safe to repeat)
.\.venv\Scripts\python.exe ingestion\load_sample_to_snowflake.py

# dbt (separate environment)
<python-3.12> -m venv .venv-dbt
.\.venv-dbt\Scripts\python.exe -m pip install -r dbt_project\requirements.txt
cd dbt_project
..\.venv-dbt\Scripts\dbt.exe run
..\.venv-dbt\Scripts\dbt.exe test
..\.venv-dbt\Scripts\dbt.exe run-operation validate_sample_results
cd ..
```
The loader refuses to touch a table it did not create, and it never uses `CREATE OR REPLACE`. If it reports an unexpected table, stop and ask the project owner.

## 5. Airflow and Streamlit
```powershell
# Airflow (Docker Desktop must be running; build takes several minutes)
docker compose -f docker-compose.airflow.yml up -d --build
# open http://localhost:8081 (host port 8081; 8080 was already used on the original machine),
# unpause and trigger the DAG "ecommerce_pipeline" once

# Streamlit
.\.venv\Scripts\streamlit.exe run streamlit_app\app.py --server.address 127.0.0.1
```
Always pass `--server.address 127.0.0.1`: without it Streamlit listens on every network interface and prints a LAN and an external URL, which would expose a page that can query Snowflake. Open http://127.0.0.1:8501.
The DAG runs: `ingest_sample` → `dbt_run` → `dbt_test` → `validate_results`. Airflow mounts the dbt key and the ingestion key as two separate read-only files; their contents are never copied or logged.

## 6. Expected results for the sample
`validate_sample_results` fails if any of these differ (from `python ingestion\make_sample_csv.py` and an independent pandas check):

| Check | Expected |
|---|---|
| Raw rows | **744** |
| Valid-sales rows (`fct_sales`) | **597** (15 are non-product charges) |
| Distinct orders | **72** |
| Total revenue | **10,210.21** |
| Months with valid sales | **13** |

| Month | Revenue | Month | Revenue | Month | Revenue |
|---|---|---|---|---|---|
| 2010-12 | 348.44 | 2011-05 | 1,516.52 | 2011-10 | 1,037.66 |
| 2011-01 | 353.19 | 2011-06 | 920.60 | 2011-11 | 503.70 |
| 2011-02 | 836.60 | 2011-07 | 639.31 | 2011-12 | 925.76 (partial month) |
| 2011-03 | 675.88 | 2011-08 | 1,009.18 | | |
| 2011-04 | 1,147.94 | 2011-09 | 295.43 | | |

## 7. Before the trial ends
Capture the screenshots in [screenshot_checklist.md](screenshot_checklist.md) (including the Airbyte Cloud credit error as evidence) and, if possible, a short screen recording, while the Snowflake account is active.
