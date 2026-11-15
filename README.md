# E-Commerce-Sales-Analytics-and-Data-Engineering-Pipeline

## E-Commerce Sales Analytics – Modern Automated Data Pipeline

A Data Engineering microproject (5th semester, two-member team) that demonstrates an end-to-end automated analytics pipeline using real e-commerce transaction data.

## Project Overview

The project processes historical e-commerce transactions from the UCI Online Retail Dataset and converts them into business insights. Airbyte ingests the data, Google BigQuery stores it, dbt transforms it, Apache Airflow orchestrates the workflow, and Streamlit presents interactive analytics.

## Business Objectives

- Analyze total sales revenue.
- Identify top-performing products.
- Monitor monthly revenue trends.
- Compare country-wise sales.
- Calculate average order value.
- Analyze customer and transaction counts.

## Technology Stack

Python, Airbyte, Google BigQuery, dbt Core, Apache Airflow, Streamlit, Docker Desktop, WSL2, Git, and VS Code.

## Data Source

UCI Machine Learning Repository – Online Retail Dataset
https://archive.ics.uci.edu/dataset/352/online+retail

## Pipeline Architecture

UCI Online Retail Dataset → Airbyte → BigQuery Raw Tables → dbt → BigQuery Analytics Tables → Streamlit Dashboard

Apache Airflow orchestrates ingestion, transformation, and validation. It does not store or transform data. See [architecture/pipeline_architecture.md](architecture/pipeline_architecture.md) for the Mermaid diagram.

## Business Problem and Questions

Raw e-commerce data contains cancellations, returns, missing values, and duplicates, so analysing it directly gives unreliable results. This project builds an automated, tested pipeline that turns raw transactions into clean analytical tables.

The dashboard will answer eight questions:

1. What is the total revenue?
2. Which product has the highest sales revenue?
3. Which month has the highest revenue?
4. Which country generates the highest revenue?
5. What is the average order value?
6. How many unique customers are there?
7. What is the total number of transactions?
8. What are the monthly sales trends?

Revenue means gross valid positive sales (`Quantity × UnitPrice`) before return deductions, not net revenue. Full metric definitions, users, scope, and limitations: [documentation/business_problem.md](documentation/business_problem.md).

## Implementation Phases

1. Business Problem Definition
2. Dataset Collection and Inspection
3. Google BigQuery Setup
4. Airbyte Data Ingestion
5. dbt Data Transformation
6. Apache Airflow Orchestration
7. Streamlit Conversational BI Dashboard
8. Final Integration and Demonstration

## Current Status

| Phase | Status |
|---|---|
| Workspace preparation | Complete |
| 1. Business Problem Definition | Complete — screenshot deferred (`01_business_problem.png` to be captured in Phase 8) |
| 2. Dataset Collection and Inspection | Complete — screenshots `02` and `03` deferred to Phase 8 |
| 3–8 | Not started |

- Folder structure, `.gitignore`, `.env.example`, and a placeholder `requirements.txt` are in place.
- No Python packages, containers, Airbyte, Airflow, or cloud services have been installed or configured.
- The genuine UCI workbook is stored in `dataset/original/` (not committed to Git) and has been inspected: 541,909 rows, 8 columns. See [documentation/dataset_description.md](documentation/dataset_description.md).
- Cleaning rules remain provisional until implemented in dbt (Phase 5). Recorded team decisions: (1) keep exact duplicate rows (possible revenue overstatement up to 0.23%); (2) keep valid non-product charges in gross valid-sales revenue but exclude a verified stock-code list from merchandise product rankings; (3) keep invoice `A563185` in raw data but classify its +11,062.06 bad-debt adjustment as a financial adjustment, excluded from gross valid-sales revenue and product rankings (refined revenue 10,655,622.48 versus 10,666,684.54 provisional); (4) the highest-revenue month compares complete months only (Dec 2010 to Nov 2011); (5) the monthly trend shows all months, with December 2011 labelled as a partial month (data ends 9 Dec 2011). The inspection results file keeps the provisional figures as historical evidence. Details: [documentation/dataset_description.md](documentation/dataset_description.md).
- A Python 3.12 virtual environment (`.venv`, not committed) holds pandas and openpyxl. BigQuery, Airbyte, dbt and Airflow are not configured.
- Phase 3 (Google BigQuery Setup) is next, pending approval.
- Screenshot tracking: see [documentation/screenshot_checklist.md](documentation/screenshot_checklist.md).

## Project Structure

```text
dataset/original/        Original UCI workbook (not committed)
dataset/processed/       Derived ingestion-ready files (not committed)
ingestion/configuration/ Airbyte configuration
dbt_project/             dbt models (staging, marts) and tests
airflow/                 DAGs and logs
streamlit_app/           Dashboard (pages, components, queries)
architecture/            Architecture diagrams
screenshots/             Genuine project screenshots
documentation/           Phase notes and reports
```

## Configuration and Security

Copy `.env.example` to `.env` and fill in real values locally. `.env`, service account keys, and dbt `profiles.yml` are excluded from Git. Never commit credentials.

## Project Team

Two-member Data Engineering microproject.

## Documentation

- [Phase 1: Business Problem Definition](documentation/business_problem.md)
- [Phase 2: Dataset description and findings](documentation/dataset_description.md)
- [Raw inspection output](documentation/dataset_inspection_results.txt)
- [Architecture diagram](architecture/pipeline_architecture.md)

## Reproducing the Dataset Inspection

Download the ZIP from https://archive.ics.uci.edu/static/public/352/online+retail.zip, extract `Online Retail.xlsx` into `dataset/original/`, and confirm its SHA-256 matches the value in `documentation/dataset_description.md`. Then, from the project root in PowerShell:

```powershell
# Use a Python 3.12 interpreter for the venv (the one used here came from uv)
<path-to-python-3.12> -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas openpyxl
.\.venv\Scripts\python.exe dataset\inspect_dataset.py
```
