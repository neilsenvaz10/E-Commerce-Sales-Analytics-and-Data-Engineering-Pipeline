"""Read-only Snowflake access for the dashboard (READER_USER key-pair login, READER_ROLE).

Settings come from environment variables / .env (see .env.example). The private key is read from
a file kept OUTSIDE the repository; its contents are never printed, logged or cached anywhere
except inside the live connection object.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

REQUIRED = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_READER_USER", "SNOWFLAKE_READER_PRIVATE_KEY_PATH"]


def missing_settings() -> list[str]:
    return [name for name in REQUIRED if not os.getenv(name)]


@st.cache_resource(show_spinner="Connecting to Snowflake...")
def get_connection():
    import snowflake.connector
    from cryptography.hazmat.primitives import serialization

    snowflake.connector.paramstyle = "qmark"   # server-side binding for the `?` parameters

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


def run_query(sql: str, params=None) -> pd.DataFrame:
    """Run one read-only SELECT with bound parameters and return a DataFrame (lower-case columns)."""
    cursor = get_connection().cursor()
    try:
        cursor.execute(sql, list(params) if params else None)
        frame = cursor.fetch_pandas_all()
    finally:
        cursor.close()
    frame.columns = [c.lower() for c in frame.columns]
    return frame
