# Screenshot Checklist

Screenshots must be genuine captures saved in `screenshots/`. Only files that exist and were verified are marked captured. No placeholder or mock images are used.

| # | File | Phase | Status |
|---|---|---|---|
| 1 | `01_business_problem.png` | 1 | **Captured and verified.** A rendered preview of the updated `documentation/business_problem.md` (title, status box, problem statement and the eight business questions). It is a **locally rendered HTML preview of the Markdown, not a VS Code screenshot** |
| 2 | `02_dataset_preview.png` | 2 | **Captured and verified.** A **read-only pandas preview** (`read_excel(nrows=15)`) of the original `Online Retail.xlsx`: the eight genuine column headers and the first 15 rows. It is **not an Excel screenshot**; the workbook's SHA-256 was identical before and after (`43465a06...6d`) |
| 3 | `03_dataset_inspection.png` | 2 | **Captured and verified.** Lines 1 to 61 of the existing `documentation/dataset_inspection_results.txt` (file hash, shape and schema, first and last rows, missing values, duplicates, cancelled invoices), rendered for the screenshot. The inspection was **not rerun** |
| 4 | `04_postgres_setup.png` | 3 (PostgreSQL fallback) | **Optional; skipped for now.** Would show only the local PostgreSQL fallback warehouse (container and schemas), which is not part of the implemented pipeline. Capture it only if the report discusses the fallback |
| 5 | `05_airbyte_configuration.png` | 4 | **Captured and verified.** Airbyte Cloud connection Timeline for *Ecommerce Retail CSV -> Snowflake*: event "Connection disabled", message "Airbyte disabled the connection due to a billing issue." (Nov 15, 2026, 9:14 PM). This is evidence of a **billing-related disablement**; it does not display the original insufficient-credits message itself. The two later "Connection settings changed" entries (schedule set to Manual) were made by the account owner. No keys or credentials are visible. The account owner's name and the organisation name were covered with plain boxes (redaction only); the Timeline events, message and dates are unaltered |
| 6 | `06_python_ingestion.png` | 4 | **Captured and verified (Snowsight part).** `SELECT COUNT(*) AS RAW_ROWS FROM ECOMMERCE_ANALYTICS.RAW.ONLINE_RETAIL_SAMPLE;` returns 744, as `ACCOUNTADMIN`. The loader terminal output (`LOADED ... 744 rows`) is not included: the earlier terminal run is no longer available, and the same line is in the Airflow `ingest_sample` log |
| 7 | `07_dbt_models.png` | 5 | **Captured and verified (Snowsight part).** `SELECT COUNT(*) AS VALID_SALES_ROWS FROM ECOMMERCE_ANALYTICS.ANALYTICS.FCT_SALES;` returns 597. The `dbt run` terminal output is not included; the same 597 appears in the Airflow `dbt_run` log |
| 8 | `08_dbt_tests.png` | 5 | **Captured and verified** (Airflow log of task `dbt_test`: `PASS=5 ... TOTAL=5`; the `Validation OK` line is in screenshot 10) |
| 9 | `09_airflow_dag.png` | 6 | **Captured and verified** (Graph view: four tasks, all `success`; the earlier failed run is visible in the grid) |
| 10 | `10_airflow_execution.png` | 6 | **Captured and verified** (run of 2026-11-15 18:01 UTC, all tasks green; `validate_results` log: `Validation OK: raw 744 rows, fct_sales 597 rows, 72 orders, revenue 10210.21, 13 months`) |
| 11 | `11_streamlit_dashboard.png` | 7 | **Captured and verified** (landing page with the three example questions) |
| 12 | `12_business_analytics.png` | 7 | **Captured and verified** (monthly revenue chart and table from Snowflake; values match the runbook) |

## How to capture the Phase 2 screenshots

- `02_dataset_preview.png`: open `dataset/original/Online Retail.xlsx` in Excel and show the header row and first rows. Do not save or edit the workbook (close without saving).
- `03_dataset_inspection.png`: in a VS Code PowerShell terminal run `.\.venv\Scripts\python.exe dataset\inspect_dataset.py` and capture the shape, missing-value, duplicate and cancellation sections (scroll up as needed, or open `documentation/dataset_inspection_results.txt`).
- Save each into `screenshots\` with the exact filename and verify with `Test-Path`.

## How to capture `01_business_problem.png`

1. In VS Code, open `documentation/business_problem.md` and press `Ctrl+Shift+V`.
2. Show the title, problem statement and the eight-question table. No credentials or unrelated windows.
3. Press `Win+Shift+S`, select the preview, then Save As the full project path `screenshots\01_business_problem.png`.
4. Verify with `Test-Path screenshots\01_business_problem.png`.

**As of 2026-11-15, screenshots 01 to 03 and 05 to 12 exist and were checked; 04 is optional and skipped.** Mark one captured only after `Test-Path` confirms the file.

## Capture guide for the working pipeline (05 to 12)

Capture only what is on screen; hide keys, account URLs you want private, and `.env` contents. Nothing here needs a rerun of ingestion, dbt or the DAG (the Airflow run and its logs already exist; run `dbt` commands only if you want fresh terminal output).

| # | What to open | Needs your manual sign-in? |
|---|---|---|
| 05 | Airbyte Cloud: the connection (File source to Snowflake) and its Timeline entry "Connection disabled ... billing issue" (captured) | **Yes**, your Airbyte Cloud account |
| 06 | Snowsight: `ECOMMERCE_ANALYTICS.RAW.ONLINE_RETAIL_SAMPLE` data preview or `SELECT COUNT(*)` = 744, plus terminal output of the loader `LOADED ... 744 rows` | **Yes**, Snowsight. Terminal part: no |
| 07 | Terminal, `cd dbt_project` then `..\.venv-dbt\Scripts\dbt.exe run` (or Snowsight: `ANALYTICS.FCT_SALES` with 597 rows) | Snowsight only |
| 08 | Terminal, `dbt test` and `dbt run-operation validate_sample_results` | No |
| 09 | `http://localhost:8081`, DAG `ecommerce_pipeline`, Graph tab | Airflow login: the standalone password is in the container (`docker exec ecommerce_airflow cat /opt/airflow/standalone_admin_password.txt`); do not show it in the capture |
| 10 | Same page, Grid view of the successful run and one task log (`validate_results`: "Validation OK ...") | Same Airflow login |
| 11 | Streamlit started with `--server.address 127.0.0.1`, open `http://127.0.0.1:8501` | No (it uses the reader key from `.env`) |
| 12 | Click an example question and capture the answer and chart | No |
