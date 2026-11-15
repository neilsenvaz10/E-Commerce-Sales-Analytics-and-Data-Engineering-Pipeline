# E-Commerce Sales Analytics – Automated Data Pipeline

A 5th-semester Data Engineering microproject (two-member team): a small, automated pipeline over real e-commerce transactions from the UCI Online Retail dataset.

## Pipeline

```
UCI sample CSV (public GitHub URL) → Airbyte Cloud → Snowflake RAW → dbt → Snowflake STAGING / ANALYTICS → Streamlit
                              Apache Airflow (local Docker) triggers Airbyte, runs dbt, validates
```

Diagram: [architecture/pipeline_architecture.md](architecture/pipeline_architecture.md)

| Part | Technology | Scope for the college demo |
|---|---|---|
| Data | UCI Online Retail | 744-row sample (`dataset/sample/`) |
| Ingestion | Airbyte Cloud (free trial) | one File → Snowflake connection, Full Refresh Overwrite |
| Warehouse | Snowflake (free trial) | schemas `RAW`, `STAGING`, `ANALYTICS`, key-pair service users |
| Transformation | dbt Core (`dbt-snowflake`) | `stg_online_retail`, `fct_sales`, 5 tests |
| Orchestration | Apache Airflow (Docker) | one DAG: trigger sync → wait → `dbt run` → `dbt test` → validate |
| Dashboard | Streamlit | three predefined questions, read-only role |

Revenue means gross valid sales (`Quantity × UnitPrice`) before returns; cancelled invoices and a bad-debt adjustment are excluded. Rules and findings from the full dataset: [documentation/dataset_description.md](documentation/dataset_description.md).

## Status (honest summary)

| Area | State |
|---|---|
| Business problem, dataset inspection (full 541,909-row dataset) | Done and documented |
| Local PostgreSQL warehouse (earlier approach, kept as a fallback) | Done; connection and permission test passed 26/26 |
| Sample CSV (744 rows) | Done; verified against the original workbook |
| Snowflake setup SQL, dbt project, Airflow DAG, Streamlit app | **Written and checked offline only.** dbt parses (2 models, 5 tests, 1 source); the SQL parses as Snowflake SQL; the app and question matcher pass local tests |
| Airbyte Cloud and Snowflake accounts | **Not created.** Nothing has run against them, so there are no sync, dbt, Airflow or dashboard results yet |
| Screenshots | None captured yet ([checklist](documentation/screenshot_checklist.md)) |

Earlier history: BigQuery was dropped (needs billing), then a local Airbyte install failed on memory, then the plan was simplified to Airbyte Cloud + Snowflake. Details: [business_problem.md](documentation/business_problem.md) section 18 and [teammate_handover.md](documentation/teammate_handover.md) (the handover describes the earlier local-Airbyte attempt, which is no longer the plan).

## How to run it

Everything is in the **[runbook](documentation/runbook.md)**: create the two trial accounts, generate keys, run `snowflake/setup.sql`, configure Airbyte Cloud, then run dbt, the Airflow DAG and Streamlit. Quick local setup:

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
ingestion/             sample and CSV scripts, PostgreSQL fallback test (archive/ = retired BigQuery)
snowflake/setup.sql    warehouse, schemas, roles, users
dbt_project/           dbt models, tests, macros, profiles.yml.example
airflow/               DAG and Dockerfile (compose file: docker-compose.airflow.yml)
streamlit_app/         dashboard and question matcher
docker-compose.yml     local PostgreSQL fallback warehouse
architecture/ documentation/ screenshots/
```

## Security

`.env`, private keys, `profiles.yml`, the full workbook and virtual environments are excluded from Git. Snowflake login uses key pairs (no passwords); keep the key files outside the repository and never paste secrets into chat or documents.
