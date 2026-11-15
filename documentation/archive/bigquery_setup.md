> **ARCHIVED (2026-11-15).** This BigQuery plan is superseded by the PostgreSQL warehouse; see [../postgres_setup.md](../postgres_setup.md) and the stack revision note in [../business_problem.md](../business_problem.md). BigQuery was never set up: no Google Cloud project, datasets or credentials were ever created, and no connection was ever tested. This file is kept as a record only.

# BigQuery Setup (Phase 3: preparation only)

## 0. Status: what is real and what is not

| Item | Status |
|---|---|
| Google Cloud project | **Does not exist** |
| Billing account / payment method | **Not created, not linked** (by team decision) |
| BigQuery API | **Not enabled** |
| BigQuery datasets | **Not created** (names below are proposals) |
| Service accounts and keys | **Not created** |
| Authentication / connection | **Not configured, not tested** |
| Google Cloud CLI (`gcloud`) | Not installed on this machine |
| Python packages in `.venv` | Installed: `google-cloud-bigquery 3.47.0`, `python-dotenv 1.2.4`, `db-dtypes 1.9.0`; `pip check` clean |
| Connection test script | Written; run only without `.env`, where it correctly stops with "set these in .env first" |
| `.env.example`, `dbt_project/profiles.yml.example` | Dummy placeholders only |

Everything under "Proposed configuration" is a **plan**. Nothing in this document has been created or verified in Google Cloud.

## 1. Proposed configuration (not created)

| Setting | Proposed value |
|---|---|
| Project ID | `your-gcp-project-id` (placeholder; to be chosen when a real project exists) |
| Location | `asia-south1` (Mumbai), one location for all datasets |
| Raw dataset | `raw_online_retail` |
| Staging dataset | `staging_online_retail` |
| Analytics dataset | `analytics_online_retail` |

The location is fixed when a dataset is created and cannot be changed later. Every dataset must use the same location, otherwise queries that join them fail.

## 2. Billing decision and Sandbox limitations

The team decided **not to link a billing account or use a payment method**. The only route without billing is the **BigQuery Sandbox**.

Documented Sandbox limits ([Google: Enable the BigQuery sandbox](https://cloud.google.com/bigquery/docs/sandbox)):

- Free usage limits only (10 GB active storage and 1 TB of query processing per month). The dataset here is about 23 MB.
- Tables, views and partitions expire after 60 days by default.
- No streaming inserts, no DML (`INSERT`, `UPDATE`, `DELETE`, `MERGE`), and no Data Transfer Service.

I did not re-check the current wording of these limits in this phase beyond a web search summary, so confirm them on the official page before relying on them.

**Possible effects on this project (all unverified until tried):**

| Area | Risk |
|---|---|
| Airbyte to BigQuery | I could not find official wording on whether Airbyte's BigQuery destination works in the Sandbox. If the connector uses a method the Sandbox blocks, ingestion would fail. Check the connector version and test early in Phase 4. |
| dbt | `table` and `view` models use DDL and `SELECT`. Incremental `merge` models use DML and would not work. Plan full-refresh `table` models; this is enough for 541,909 rows. |
| 60-day expiry | Raw and analytics tables would disappear after 60 days, so the pipeline must be re-runnable (it is designed to be). Re-run it before the demonstration. |
| Service accounts and keys | Believed to work in a Sandbox project, but not confirmed. An organisation policy can also block key creation. |

**Fallbacks if the Sandbox blocks a required step** (each needs a new team decision):
1. Use a billing-linked project (needs a payment method) with a small budget alert.
2. Use another approved free route, such as the free-trial credit, if the team is willing to provide billing details.

Neither is chosen or assumed. If neither is acceptable, the BigQuery phases cannot run against real BigQuery, and the Master Prompt's fixed stack would need to be revisited with your approval.

## 3. Proposed security model

Use two service accounts with the least privilege that works. **Not created yet.**

| Account | Used by | Roles (proposed) |
|---|---|---|
| Pipeline account | Airbyte, dbt, Airflow | BigQuery Data Editor on the three datasets; BigQuery Job User on the project |
| Dashboard account | Streamlit | BigQuery Data Viewer on the analytics dataset only; BigQuery Job User on the project |

Airbyte's documentation also names BigQuery User and Data Editor, and a community report says the connector may need `bigquery.datasets.create` ([Airbyte docs](https://docs.airbyte.com/integrations/destinations/bigquery), [forum thread](https://discuss.airbyte.io/t/workaround-for-bigquery-datasets-create-permission/6921)). Create the datasets by hand first, and add permissions only if Airbyte reports a specific missing one.

Rules:
- Key files stay **outside** the project folder (for example `C:\Users\<you>\.gcp\`). `.gitignore` also blocks common key filenames as a safety net.
- Never paste keys or tokens into chat, documents, screenshots or commits.
- Real values go in `.env` (Git-ignored). `.env.example` holds placeholders only.
- No fake keys are stored anywhere in the project.

## 4. Planned table structures (no data ingested)

These are plans for Phases 4 and 5. They will be revised against the real ingested schema.

### Raw layer: `raw_online_retail`

Airbyte will create the raw table from the source. Fields from the real workbook (Phase 2):

| Column | Source type | Note |
|---|---|---|
| InvoiceNo | mixed number/text | Must be treated as a string |
| StockCode | text | |
| Description | text | 1,454 nulls |
| Quantity | integer | |
| InvoiceDate | datetime | |
| UnitPrice | float | |
| CustomerID | float | 135,080 nulls |
| Country | text | |

Airbyte also adds its own metadata columns. Their exact names depend on the connector version and are not assumed here. All 541,909 rows are kept.

### Staging layer: `staging_online_retail`

| Planned model | Purpose |
|---|---|
| `stg_online_retail` | Standardised names, cast types (`InvoiceNo` string, `CustomerID` integer), flags for cancellation, non-product stock code and financial adjustment |
| `stg_valid_sales` | Rows that meet the finalized valid-sales rule (see `dataset_description.md`, Section 6) |

### Analytics layer: `analytics_online_retail`

`fct_sales`, `dim_products`, `dim_customers`, `mart_monthly_sales`, `mart_country_sales`, `mart_product_performance`, as in the Master Prompt, adapted after the ingested schema is verified.

## 5. Steps for when real credentials become available

Only follow these if the team later decides on a route that allows them. Nothing here has been done.

1. In the Google Cloud Console, create a project (Sandbox, no billing) and note its project ID.
2. Open BigQuery in the Console, which enables the BigQuery API for the project.
3. Create three datasets with location `asia-south1`. For Sandbox projects, keep the default 60-day table expiration.
4. Create the two service accounts, grant the roles in Section 3, and save the key files outside the repository.
5. Copy `.env.example` to `.env` and replace the placeholders with real values.
6. Run the connection test (Section 6).
7. Copy `dbt_project/profiles.yml.example` to `dbt_project/profiles.yml` in Phase 5.
8. Airbyte settings (Phase 4): destination BigQuery, the project ID, dataset location `asia-south1`, default dataset `raw_online_retail`, and the pipeline key pasted into Airbyte's own settings screen, not into chat or files.

## 6. Connection test

[`ingestion/test_bigquery_connection.py`](../ingestion/test_bigquery_connection.py) checks the settings, loads credentials, runs `SELECT 1`, and confirms each dataset exists in the expected location. It is read-only and prints no credentials.

```powershell
# Pipeline account
.\.venv\Scripts\python.exe ingestion\test_bigquery_connection.py

# Dashboard (read-only) account
.\.venv\Scripts\python.exe ingestion\test_bigquery_connection.py --readonly
```

**Verified so far:** with no `.env` present, it exits with code 1 and the message `set these in .env first: GCP_PROJECT_ID, BQ_LOCATION, BQ_RAW_DATASET, BQ_ANALYTICS_DATASET`.

**Not verified:** every real check (credentials, query, datasets), because no real project exists. The script's success path has not been exercised.

## 7. Screenshot

`04_bigquery_setup.png` is **deferred**. A real screenshot needs a real project and datasets. It is recorded as pending in the [screenshot checklist](screenshot_checklist.md).

## 8. Open issues

- No Google Cloud project exists; the connection cannot be tested.
- Sandbox compatibility with Airbyte and dbt is unverified.
- The Google Cloud CLI is not installed; it is optional because the plan uses key files.
- Phases 4 to 8 depend on a working BigQuery project. The team needs a plan for reaching one before Phase 4 can ingest anything.
