# E-Commerce Sales Analytics – Automated Data Pipeline

A 5th-semester Data Engineering microproject (two-member team): a small, automated pipeline over real e-commerce transactions from the UCI Online Retail dataset.

## Pipeline

```
UCI sample CSV → Python loader → Snowflake RAW → dbt → Snowflake STAGING / ANALYTICS → Streamlit
                 Apache Airflow (local Docker) runs the loader, dbt run, dbt test, and validates
```

> **Airbyte Cloud ingestion was blocked by a billing restriction. An insufficient-credits message was observed during setup, and the connection was subsequently disabled by Airbyte Cloud due to a billing issue. The project therefore uses Python-based ingestion into Snowflake instead.** The team will not add a payment method. Evidence: [screenshot 05](screenshots/05_airbyte_configuration.png) shows the later billing-related disablement, not the original message. The Snowflake names `AIRBYTE_USER` / `AIRBYTE_ROLE` are historical and now belong to the loader.

Diagram: [architecture/pipeline_architecture.md](architecture/pipeline_architecture.md)

| Part | Technology | Scope for the college demo |
|---|---|---|
| Data | UCI Online Retail | 744-row sample (`dataset/sample/`) |
| Ingestion | Python (`ingestion/load_sample_to_snowflake.py`) | loads all 744 rows into `RAW.ONLINE_RETAIL_SAMPLE` in one transaction; safe to repeat (replaces rows, never duplicates, rolls back on error) |
| Warehouse | Snowflake (free trial) | schemas `RAW`, `STAGING`, `ANALYTICS`, key-pair service users |
| Transformation | dbt Core (`dbt-snowflake`) | `stg_online_retail`, `fct_sales`, 5 tests, plus a validation of the expected sample results |
| Orchestration | Apache Airflow (Docker) | one DAG: Python load → `dbt run` → `dbt test` → validate |
| Dashboard | Streamlit | three predefined questions, read-only role |

Revenue means gross valid sales (`Quantity × UnitPrice`) before returns; cancelled invoices and a bad-debt adjustment are excluded. Rules and findings from the full dataset: [documentation/dataset_description.md](documentation/dataset_description.md).

## Status (honest summary)

| Area | State |
|---|---|
| Business problem, dataset inspection (full 541,909-row dataset) | Done and documented |
| Local PostgreSQL warehouse (earlier approach, kept as a fallback) | Done; connection and permission test passed 26/26 |
| Sample CSV (744 rows) | Done; verified against the original workbook |
| Snowflake account, database, roles, key-pair users | Created by the team (30-day trial, no payment method) |
| Python loader | **Run against Snowflake:** loaded all 744 rows into `RAW.ONLINE_RETAIL_SAMPLE`; all five verification counts match the CSV. A second load (from Airflow) replaced the rows with no duplicates |
| dbt | **Run against Snowflake (from the Windows host):** `dbt debug` OK, `dbt run` created `STG_ONLINE_RETAIL` (view) and `FCT_SALES` (597 rows), 5 of 5 tests passed, and `validate_sample_results` confirmed 744 raw rows, 597 valid-sales rows, 72 orders, revenue 10,210.21 and 13 months |
| Streamlit | **Tested against Snowflake** as `READER_USER`: the three queries match the CSV and the validated dbt data, and the dashboard renders in a browser. Screenshots not yet taken |
| Airflow | **Working end to end.** The container starts (`http://localhost:8081`). An earlier run failed in `dbt_run` with a parse-cache `KeyError` (the Windows-made `partial_parse.msgpack` clashed with Linux). The DAG now sends dbt artifacts and logs to the container's `/tmp` (`DBT_TARGET_PATH` / `DBT_LOG_PATH`); the rerun passed all four tasks: loader 744 rows, `dbt run` 2/2 (597 rows), `dbt test` 5/5, validation OK (744 / 597 / 72 / 10210.21 / 13) |
| Airbyte Cloud | Configured, but **blocked by a billing restriction** (insufficient-credits message seen during setup; connection later disabled by Airbyte Cloud due to a billing issue); replaced by the Python loader |
| Screenshots | 11 of 12 captured in `screenshots/` (01 to 03 and 05 to 12); 04 (PostgreSQL fallback) is optional and skipped. 01 is a rendered Markdown preview and 02 a read-only pandas preview, not app screenshots; 05 shows the billing-related disablement. Details: [checklist](documentation/screenshot_checklist.md) |

Earlier history: BigQuery was dropped (needs billing), then a local Airbyte install failed on memory, then Airbyte Cloud + Snowflake was chosen, and finally Python ingestion replaced Airbyte Cloud. Details: [business_problem.md](documentation/business_problem.md) section 18. Teammate setup guide: [teammate_handover.md](documentation/teammate_handover.md).

## How to run it

Everything is in the **[runbook](documentation/runbook.md)**: local settings, the loader (offline dry-run, read-only check, then the load), dbt, the Airflow DAG and Streamlit. The Snowflake setup (`snowflake/setup.sql`, keys from `snowflake/make_keys.ps1`) is already done. Quick local setup:

```powershell
<python-3.12> -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env        # then fill in your own values; never commit .env
```

## Data attribution

The sample is a subset of the UCI Online Retail dataset: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes (subset of 744 rows, Excel converted to CSV, values unchanged) are listed in [dataset/sample/README.md](dataset/sample/README.md). The full workbook is not in the repository.

## Repository layout

```text
dataset/sample/        744-row sample CSV (public) and its attribution
dataset/original/      full UCI workbook (not in Git)
ingestion/             Python loader and its tests, sample CSV script, PostgreSQL fallback test (archive/ = retired BigQuery)
snowflake/             setup.sql (warehouse, schemas, roles, users) and make_keys.ps1 (key pairs)
dbt_project/           dbt models, tests, macros, profiles.yml.example
airflow/               DAG and Dockerfile (compose file: docker-compose.airflow.yml)
streamlit_app/         dashboard and question matcher
docker-compose.yml     local PostgreSQL fallback warehouse
architecture/ documentation/ screenshots/
```

## Security

`.env`, private keys, `profiles.yml`, the full workbook and virtual environments are excluded from Git. Snowflake login uses key pairs (no passwords); keep the key files outside the repository and never paste secrets into chat or documents.
