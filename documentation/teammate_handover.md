# Teammate Handover

Last updated: 2026-11-15. A short setup guide for the **current** pipeline:

```
UCI sample CSV (744 rows) -> Python loader -> Snowflake RAW -> dbt -> STAGING / ANALYTICS -> Streamlit
                              Apache Airflow (local Docker) runs: load -> dbt run -> dbt test -> validate
```

All commands live in the **[runbook](runbook.md)**; this page only says what to prepare and what to watch for. The overall status table is in the [README](../README.md).

## 1. Required software
- Windows 11, **Docker Desktop** (WSL2), **Git** (its OpenSSL is used by `snowflake\make_keys.ps1`) and **Python 3.12**.
- About 3 GB of free RAM for the Airflow image build (close browsers first).
- Two Python environments, both Git-ignored:
  - `.venv`: `pip install -r requirements.txt` (loader, Streamlit, tests)
  - `.venv-dbt`: `pip install -r dbt_project\requirements.txt` (dbt-core 1.11.17, dbt-snowflake 1.12.5)

## 2. Snowflake and key-pair login
- Use your own free trial (30 days, no payment method), or get the account identifier from the project owner and have your own public keys added to the existing users.
- Run `snowflake\make_keys.ps1`. It creates three key pairs in `C:\Users\<you>\.snowflake\` (outside the repo, never overwritten) and writes `setup_filled.sql`. Run that SQL in a Snowsight worksheet (**Run All**).
- It creates database `ECOMMERCE_ANALYTICS` (schemas `RAW`, `STAGING`, `ANALYTICS`), warehouse `ECOMMERCE_WH`, and three key-pair service users with separate roles:

| User | Role | Used by | Access |
|---|---|---|---|
| `AIRBYTE_USER` (historical name) | `AIRBYTE_ROLE` | Python loader | writes `RAW` |
| `TRANSFORM_USER` | `TRANSFORM_ROLE` | dbt | reads `RAW`, writes `STAGING`, `ANALYTICS` |
| `READER_USER` | `READER_ROLE` | Streamlit | read-only on `ANALYTICS` |

## 3. Local configuration (both files are Git-ignored)
- `.env`: copy `.env.example` and set `SNOWFLAKE_ACCOUNT` plus the three private-key paths (forward slashes). The PostgreSQL block is only for the old fallback and can be ignored.
- `dbt_project\profiles.yml`: copy `profiles.yml.example`. It holds only environment-variable references, no secrets.

## 4. Running it
Follow the [runbook](runbook.md) in order: loader `--dry-run`, then `--check` (read-only), then the load; dbt `run`, `test`, `run-operation validate_sample_results`; Streamlit (always with `--server.address 127.0.0.1`); Airflow on `http://localhost:8081` (`docker compose -f docker-compose.airflow.yml up -d --build`, then trigger DAG `ecommerce_pipeline` once). Never run `docker compose down -v`.

## 5. Expected results
| Check | Expected |
|---|---|
| Raw rows | 744 |
| Valid-sales rows (`fct_sales`) | 597 |
| Distinct orders | 72 |
| Total revenue | 10,210.21 |
| Months with valid sales | 13 |

`validate_sample_results` fails if any value differs. Rules and the per-month table: [runbook](runbook.md), [dataset_description.md](dataset_description.md).

## 6. Security precautions
- Private keys (`*.p8`, `*.pem`), `.env` and `profiles.yml` must never be committed, pasted into chat or emailed. Keep keys outside the repository; the Airflow compose file mounts them read-only and never copies them into the image.
- One key per user: do not reuse the loader key for dbt or Streamlit. Share keys only through a secure channel, or better, generate your own.
- Streamlit uses the read-only role and fixed queries only. Do not remove `--server.address 127.0.0.1`.
- No grant or Snowflake object changes without the project owner's approval.

## 7. Current limitations
- **Sample only:** 744 rows (CC BY 4.0, see `dataset/sample/README.md`), not the full 541,909-row dataset. The full workbook is not in Git.
- **Airbyte Cloud ingestion was blocked by a billing restriction. An insufficient-credits message was observed during setup, and the connection was subsequently disabled by Airbyte Cloud due to a billing issue. The project therefore uses Python-based ingestion into Snowflake instead.** The team will not add a payment method. The `AIRBYTE_*` Snowflake names are historical. Local Airbyte (`abctl`) also failed on RAM and is abandoned; a stopped `airbyte-abctl-control-plane` container may exist on the original machine.
- **Airflow:** the container starts and `dbt run` previously failed with a `KeyError` because the Windows-made dbt cache (`dbt_project/target/partial_parse.msgpack`) was read by the Linux container. The DAG now writes dbt artifacts and logs to the container's own `/tmp`, and the rerun passed all four tasks (loader, `dbt run`, `dbt test`, validation with the expected results).
- The Snowflake trial ends 30 days after signup. Screenshots (see [screenshot_checklist.md](screenshot_checklist.md)) and a short screen recording must be captured before then. Screenshot 05 (Airbyte Cloud Timeline: connection disabled due to a billing issue) is already captured; it is not the original insufficient-credits message.
- The PostgreSQL warehouse (`docker-compose.yml`, port 5434) is a verified fallback and not part of this path.
- The full history of changes of plan is in section 18 of [business_problem.md](business_problem.md).
