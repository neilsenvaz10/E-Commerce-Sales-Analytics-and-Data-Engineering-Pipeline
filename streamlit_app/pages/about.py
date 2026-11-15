"""About the Project: problem, data, pipeline and the Airbyte Cloud billing restriction."""

import streamlit as st

import filters_ui
import theme

filters_ui.context()
theme.header("About the Project", "E-Commerce Sales Analytics: an automated data pipeline (fifth-semester Data Engineering mini-project).")

with st.container(border=True):
    st.subheader("Business problem")
    st.write("Raw e-commerce transactions contain cancelled orders, returns, missing values and duplicates, so analysing "
             "them directly gives inaccurate answers and manual processing is slow. The project builds a repeatable pipeline "
             "that loads, cleans, tests and publishes the data so questions such as total revenue, best-selling products and "
             "monthly trends can be answered reliably. Revenue here means gross valid sales (quantity x unit price) before returns.")

with st.container(border=True):
    st.subheader("Pipeline")
    st.code("UCI Online Retail (541,909 rows)\n"
            "   -> deterministic 744-row sample (CSV)\n"
            "   -> Python loader  ->  Snowflake RAW\n"
            "   -> dbt            ->  STAGING (view) / ANALYTICS (fct_sales)\n"
            "   -> Streamlit (this dashboard, read-only)\n"
            "Apache Airflow orchestrates: load -> dbt run -> dbt test -> validate", language="text")
    st.markdown(
        "- **Python ingestion:** loads the sample CSV into `RAW.ONLINE_RETAIL_SAMPLE` in one transaction (safe to repeat, rolls back on error).\n"
        "- **Snowflake:** stores the RAW, STAGING and ANALYTICS layers; this dashboard connects with a read-only role and a key pair.\n"
        "- **dbt:** converts types, flags cancelled, adjustment and non-product lines, builds `fct_sales`, runs 5 tests and validates the results.\n"
        "- **Apache Airflow:** one DAG runs the four steps in order (a verified run completed 4 of 4 tasks).\n"
        "- **Streamlit:** this dashboard, plus three predefined business questions answered by fixed queries (no free-form SQL).")

with st.container(border=True):
    st.subheader("Dataset and sample")
    st.write("Source: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository, "
             "https://doi.org/10.24432/C5BW33, licensed CC BY 4.0. The full dataset has **541,909** rows; it was inspected "
             "in full, but the implemented pipeline and every figure in this dashboard use only a deterministic "
             "**744-row sample** (597 valid sales lines, 72 orders, revenue 10,210.21, 13 months). Sample results are not full-dataset results.")

with st.container(border=True):
    st.subheader("Why Python ingestion and not Airbyte Cloud")
    st.write("Airbyte Cloud ingestion was blocked by a billing restriction. An insufficient-credits message was observed during setup, "
             "and the connection was subsequently disabled by Airbyte Cloud due to a billing issue. The project therefore uses "
             "Python-based ingestion into Snowflake instead.")
