"""Streamlit dashboard: three predefined business questions answered from Snowflake.

Run (project root, PowerShell):   .\\.venv\\Scripts\\streamlit.exe run streamlit_app\\app.py
Connects with the read-only READER_USER (key-pair login). Settings come from environment
variables / .env (see .env.example). No credentials are stored in this file.
"""

from __future__ import annotations

import os
import sys
from calendar import monthrange
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from questions import QUESTIONS, match_question  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

REQUIRED = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_READER_USER", "SNOWFLAKE_READER_PRIVATE_KEY_PATH"]


@st.cache_resource(show_spinner="Connecting to Snowflake...")
def get_connection():
    """Read-only Snowflake connection using the READER_USER private key (file kept outside the repo)."""
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    key_bytes = Path(os.environ["SNOWFLAKE_READER_PRIVATE_KEY_PATH"]).read_bytes()
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_READER_USER"],
        private_key=private_key.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
        role="READER_ROLE",
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ECOMMERCE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ECOMMERCE_ANALYTICS"),
        schema="ANALYTICS",
    )


def run_query(sql: str) -> pd.DataFrame:
    cursor = get_connection().cursor()
    try:
        cursor.execute(sql)
        frame = cursor.fetch_pandas_all()
    finally:
        cursor.close()
    frame.columns = [c.lower() for c in frame.columns]
    return frame


def show_answer(question) -> None:
    data = run_query(question.sql)
    st.subheader(question.title)
    if data.empty:
        st.warning("The query returned no rows. Has the pipeline run?")
        return
    if question.key == "total_revenue":
        row = data.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total revenue", f"{float(row['total_revenue']):,.2f}")
        c2.metric("Orders", f"{int(row['orders']):,}")
        c3.metric("Order lines", f"{int(row['lines']):,}")
        st.caption("Gross valid-sales revenue (quantity x unit price) before any returns; includes valid postage and fee lines.")
    elif question.key == "top_products":
        st.dataframe(data, hide_index=True, use_container_width=True)
        st.caption("Merchandise only: postage, fees, vouchers and manual entries are excluded.")
    else:
        data["revenue"] = data["revenue"].astype(float)
        st.bar_chart(data, x="invoice_month", y="revenue")
        st.dataframe(data, hide_index=True, use_container_width=True)
        last = pd.to_datetime(data["invoice_month"]).max()
        last_day = run_query("select max(invoice_ts) as last_ts from fct_sales").iloc[0, 0]
        if last_day is not None and pd.Timestamp(last_day).day < monthrange(last.year, last.month)[1]:
            st.caption(f"{last:%B %Y} is a partial month (data ends {pd.Timestamp(last_day):%d %b %Y}).")


st.set_page_config(page_title="E-Commerce Sales Analytics", layout="wide")
st.title("E-Commerce Sales Analytics")
st.caption("Pipeline: UCI Online Retail sample (CSV) -> Airbyte Cloud -> Snowflake -> dbt -> Streamlit. "
           "Data: 744-row sample of the UCI Online Retail dataset (CC BY 4.0), not the full dataset.")

missing = [name for name in REQUIRED if not os.getenv(name)]
if missing:
    st.error("Snowflake is not configured yet. Set these in .env: " + ", ".join(missing))
    st.stop()

st.write("Ask one of the three supported questions, or click an example.")
cols = st.columns(len(QUESTIONS))
clicked = next((q for q, col in zip(QUESTIONS, cols) if col.button(q.example, use_container_width=True)), None)
typed = st.text_input("Your question", placeholder="e.g. What is the total revenue?")

question = clicked or (match_question(typed) if typed.strip() else None)
if typed.strip() and question is None and clicked is None:
    st.info("I can only answer: " + " | ".join(q.title for q in QUESTIONS))
elif question is not None:
    try:
        show_answer(question)
    except Exception as exc:  # show a readable message instead of a stack trace
        st.error(f"Could not run the query: {type(exc).__name__}: {str(exc)[:300]}")
