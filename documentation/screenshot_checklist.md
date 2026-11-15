# Screenshot Checklist

Screenshots must be genuine captures saved in `screenshots/`. Only files that exist and were verified are marked captured. No placeholder or mock images are used.

| # | File | Phase | Status |
|---|---|---|---|
| 1 | `01_business_problem.png` | 1 | **Pending — deferred to Phase 8** (approved by the team; capture the VS Code Markdown preview of `documentation/business_problem.md`) |
| 2 | `02_dataset_preview.png` | 2 | **Pending — deferred to Phase 8** (approved by the team) |
| 3 | `03_dataset_inspection.png` | 2 | **Pending — deferred to Phase 8** (approved by the team) |
| 4 | `04_postgres_setup.png` | 3 | **Pending** (renamed from `04_bigquery_setup.png` after the 2026-11-15 stack revision; show the running container and the schemas) |
| 5 | `05_airbyte_configuration.png` | 4 | **Pending** (Airbyte is not running yet; see the teammate handover) |
| 6 | `06_airbyte_sync.png` | 4 | Not captured |
| 7 | `07_dbt_models.png` | 5 | Not captured |
| 8 | `08_dbt_tests.png` | 5 | Not captured |
| 9 | `09_airflow_dag.png` | 6 | Not captured |
| 10 | `10_airflow_execution.png` | 6 | Not captured |
| 11 | `11_streamlit_dashboard.png` | 7 | Not captured |
| 12 | `12_business_analytics.png` | 7 | Not captured |

## How to capture the Phase 2 screenshots

- `02_dataset_preview.png`: open `dataset/original/Online Retail.xlsx` in Excel and show the header row and first rows. Do not save or edit the workbook (close without saving).
- `03_dataset_inspection.png`: in a VS Code PowerShell terminal run `.\.venv\Scripts\python.exe dataset\inspect_dataset.py` and capture the shape, missing-value, duplicate and cancellation sections (scroll up as needed, or open `documentation/dataset_inspection_results.txt`).
- Save each into `screenshots\` with the exact filename and verify with `Test-Path`.

## How to capture `01_business_problem.png`

1. In VS Code, open `documentation/business_problem.md` and press `Ctrl+Shift+V`.
2. Show the title, problem statement and the eight-question table. No credentials or unrelated windows.
3. Press `Win+Shift+S`, select the preview, then Save As the full project path `screenshots\01_business_problem.png`.
4. Verify with `Test-Path screenshots\01_business_problem.png`.
