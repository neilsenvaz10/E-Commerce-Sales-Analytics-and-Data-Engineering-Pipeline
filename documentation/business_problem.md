# Phase 1: Business Problem Definition

**Project:** E-Commerce Sales Analytics – Modern Automated Data Pipeline
**Phase status:** Phase 1 documentation. The dataset has **not** been downloaded or inspected yet. Every statement about the data below is an expectation, to be verified in Phase 2.

---

## 1. Introduction

E-commerce businesses generate transaction data with every customer purchase. This data holds useful information about product sales, customer activity, revenue, and geographical purchasing patterns. Analysing it helps a business understand its sales performance and make better decisions.

This project builds an automated data engineering pipeline using Airbyte, Google BigQuery, dbt, Apache Airflow, and Streamlit.

## 2. Business Scenario

An e-commerce business wants to analyse its historical transactions to understand revenue performance, product demand, customer activity, and sales by country. The planned data source is the **UCI Online Retail Dataset**, which contains historical transactions of a retailer.

## 3. Business Problem

E-commerce transaction data commonly contains missing values, cancelled orders, returns, duplicate records, and inconsistent entries. Analysing raw data directly can give inaccurate results. Manual processing is repetitive, slow, and hard to maintain.

A reliable pipeline is needed to ingest, clean, transform, and organise transactional data for business analysis.

## 4. Problem Statement

To design and implement an automated data engineering pipeline that processes real e-commerce transaction data, stores it in Google BigQuery, transforms it using dbt, and provides business insights through an interactive Streamlit dashboard.

The system will help users analyse revenue, product performance, customer activity, and monthly sales trends.

## 5. Project Objectives

1. Collect genuine e-commerce transaction data from the UCI Online Retail Dataset.
2. Ingest the records using Airbyte.
3. Store raw data in Google BigQuery.
4. Clean and transform the data using dbt and SQL.
5. Automate pipeline execution using Apache Airflow.
6. Build an interactive Streamlit dashboard.
7. Provide a conversational interface for the approved business questions.
8. Provide accurate and consistent business analytics.

## 6. Expected Outcomes

- Raw transaction data preserved separately from cleaned data.
- Documented, tested transformation rules producing reusable analytical tables.
- An orchestrated workflow that runs ingestion, transformation, tests, and verification in order.
- A dashboard that answers the eight business questions from warehouse data.

## 7. Intended Users and Stakeholders

| User | Interest |
|---|---|
| Business Owners | Monitor revenue and overall sales performance |
| Sales Managers | Identify best-selling products and monthly patterns |
| Business Analysts | Analyse customer activity and country-wise revenue |
| Data Engineers | Monitor ingestion, transformation, and pipeline runs |

## 8. Business Questions

| # | Question | Metric used | Fields needed (expected) |
|---|---|---|---|
| 1 | What is the total revenue? | Total Revenue | Quantity, UnitPrice |
| 2 | Which product has the highest sales revenue? | Top-Selling Product | StockCode, Description, Quantity, UnitPrice |
| 3 | Which month has the highest revenue? | Highest Revenue Month | InvoiceDate, Quantity, UnitPrice |
| 4 | Which country generates the highest revenue? | Top Revenue Country | Country, Quantity, UnitPrice |
| 5 | What is the average order value? | AOV | InvoiceNo, Quantity, UnitPrice |
| 6 | How many unique customers are there? | Unique Customers | CustomerID |
| 7 | What is the total number of transactions? | Total Transactions | InvoiceNo |
| 8 | What are the monthly sales trends? | Monthly Sales Trends | InvoiceDate, Quantity, UnitPrice |

**Feasibility check:** each question maps to fields the dataset is *expected* to contain (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country). This is based on the dataset's published description. Whether the actual workbook has these fields in usable form is confirmed only in Phase 2.

## 9. Business Metric Definitions

| Metric | Definition |
|---|---|
| **Total Revenue** | Sum of `Quantity × UnitPrice` over valid positive sales |
| **Top-Selling Product** | Product with the highest total valid sales revenue, identified by `StockCode` (not description) |
| **Highest Revenue Month** | Calendar month with the highest valid sales revenue |
| **Top Revenue Country** | Country with the highest valid sales revenue |
| **Average Order Value (AOV)** | Total valid sales revenue ÷ number of distinct valid sales invoices |
| **Unique Customers** | Count of distinct non-null `CustomerID` values on valid sales |
| **Total Transactions** | Count of distinct valid sales `InvoiceNo` values (not line-item rows) |
| **Monthly Sales Trends** | Valid sales revenue aggregated by invoice month |

**Revenue meaning:** the main revenue metric is **gross valid positive sales revenue before return deductions**. It is *not* net revenue after refunds. Returns are excluded from it, and no excluded-return amount will be labelled as net revenue.

## 10. Preliminary Data Quality Rules

These rules are **provisional**. They will be confirmed or revised after the dataset is inspected in Phase 2.

| Situation | Proposed treatment |
|---|---|
| Cancelled invoices | Exclude from main sales analytics |
| Returns / negative quantities | Exclude from main sales analytics; keep in raw layer |
| Zero or negative unit price | Exclude from main sales analytics |
| Missing invoice or product identifier | Exclude from main sales analytics |
| Missing CustomerID | Keep for revenue; exclude from unique customer count |
| Duplicate records | Investigate before deciding whether to remove |
| Transaction counts | Use distinct invoice numbers |
| Invoice dates | Preserve original dates; parse and verify in Phase 2 |
| Missing product descriptions | Decide in Phase 2 after seeing how common they are |

Raw records are always preserved unchanged in the raw layer. Cleaning happens only in downstream dbt models.

## 11. Why an Automated Pipeline Is Required

1. It reduces repetitive manual processing.
2. It applies cleaning rules the same way every time.
3. It makes ingestion and transformation repeatable.
4. It lowers the risk of manual calculation errors.
5. It supports automated data quality tests.
6. It makes results reproducible.
7. It lets dashboards read prepared warehouse tables.

## 12. Component Roles

| Component | Role | What it is *not* |
|---|---|---|
| Airbyte | Ingests source data into BigQuery raw tables | Not a transformation tool here |
| Google BigQuery | Stores raw, staging, and analytics data and runs SQL | |
| dbt Core | Transforms data with SQL, tests it, documents it | Not an ingestion tool |
| Apache Airflow | Orchestrates and monitors the run order | Not a storage or transformation engine |
| Streamlit | Presents the dashboard and conversational interface | Reads analytics tables only |

See the diagram: [`architecture/pipeline_architecture.md`](../architecture/pipeline_architecture.md).

## 13. Technology Stack

| Component | Technology |
|---|---|
| Data source | UCI Online Retail Dataset |
| Language | Python |
| Ingestion | Airbyte |
| Warehouse | Google BigQuery |
| Transformation | dbt Core (BigQuery adapter) |
| Orchestration | Apache Airflow |
| Dashboard | Streamlit |
| Environment | VS Code, Windows 11, Docker Desktop, WSL2, Git |

## 14. Scope

**In scope:** historical transaction analysis, revenue reporting, product performance, customer counts, geographical sales insights, and a dashboard answering the eight questions from transformed BigQuery data.

**Out of scope:** live or streaming data, customer segmentation, forecasting, return/refund analysis (unless added later), and unrestricted natural-language-to-SQL.

## 15. Limitations

- The dataset holds historical transactions, not live sales.
- Product categories are not provided in the original dataset.
- Customer demographic information is limited.
- Missing customer identifiers may affect customer-level analysis.
- Main revenue analytics exclude returns unless a separate return analysis is built.
- Conversational BI will support controlled, predefined business questions, not free-form SQL.

## 16. Assumptions

- The UCI dataset is available from its official page: https://archive.ics.uci.edu/dataset/352/online+retail
- The dataset has the expected columns listed above (**unverified until Phase 2**).
- Free-tier or low-cost Google Cloud usage will be sufficient (to be explained and approved in Phase 3).

## 17. Phase 1 Conclusion

Phase 1 sets out the business problem, objectives, users, questions, metrics, preliminary quality rules, and architecture roles. Dataset-specific assumptions are verified in Phase 2 before any transformation is built.
