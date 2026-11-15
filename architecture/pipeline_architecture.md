# Pipeline Architecture

Planned architecture. Components are **not yet implemented**; this diagram shows the design only.

```mermaid
flowchart LR
    SRC["UCI Online Retail Dataset<br/>(source file)"]
    AB["Airbyte<br/>ingestion"]

    subgraph BQ["Google BigQuery"]
        RAW[("Raw layer<br/>untouched records")]
        STG[("Staging layer<br/>cleaned, typed")]
        MART[("Analytics layer<br/>marts for reporting")]
    end

    DBT["dbt Core<br/>SQL transformations + tests"]
    ST["Streamlit<br/>dashboard + conversational BI"]
    AF["Apache Airflow<br/>orchestration only"]

    SRC --> AB --> RAW
    RAW --> DBT
    DBT --> STG --> MART
    MART --> ST

    AF -. triggers and monitors .-> AB
    AF -. triggers .-> DBT
    AF -. verifies tables .-> MART
```

## Roles

- **Airbyte** moves source records into the BigQuery raw layer.
- **BigQuery** stores all three layers and executes the SQL.
- **dbt** builds staging and analytics tables and runs data tests.
- **Airflow** only schedules and sequences tasks (ingest, wait, verify, dbt run, dbt test, verify). It does not store or transform data.
- **Streamlit** reads the analytics layer with read-only access.
