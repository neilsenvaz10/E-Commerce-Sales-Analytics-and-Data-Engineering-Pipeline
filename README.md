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
| 2–8 | Not started |

- Folder structure, `.gitignore`, `.env.example`, and a placeholder `requirements.txt` are in place.
- No Python packages, containers, Airbyte, Airflow, or cloud services have been installed or configured.
- The dataset has not been downloaded or inspected. Data-cleaning rules are provisional until Phase 2.
- Phase 2 (Dataset Collection and Inspection) is next, pending approval.
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
- [Architecture diagram](architecture/pipeline_architecture.md)
