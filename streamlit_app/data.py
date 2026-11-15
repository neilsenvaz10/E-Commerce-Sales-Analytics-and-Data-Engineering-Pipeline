"""Cached data loaders for the pages. Cache keys are only the SQL text and the bound values."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import db
import queries as q

CACHE_SECONDS = 600


class DashboardError(Exception):
    """A readable error that is safe to show (never contains account names, hosts or key paths)."""


@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Querying Snowflake...")
def _query(sql: str, params: tuple) -> pd.DataFrame:
    try:
        return db.run_query(sql, params)
    except Exception as exc:  # noqa: BLE001 - turn any driver error into a safe message
        raise DashboardError(
            f"Could not run the Snowflake query ({type(exc).__name__}). Check your .env settings, that the "
            "key file exists, and that the pipeline has loaded FCT_SALES. Technical details are hidden on purpose."
        ) from None


def fetch(sql: str, params=()) -> pd.DataFrame:
    """Run a query; on failure show the safe message and stop the page."""
    try:
        return _query(sql, tuple(params))
    except DashboardError as exc:
        st.error(str(exc))
        st.stop()


def _numeric(frame: pd.DataFrame, *columns: str) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def bounds() -> tuple[date, date, pd.Timestamp]:
    row = fetch(q.BOUNDS_SQL).iloc[0]
    if pd.isna(row["first_day"]):
        st.warning("FCT_SALES is empty. Has the pipeline run?")
        st.stop()
    return pd.Timestamp(row["first_day"]).date(), pd.Timestamp(row["last_day"]).date(), pd.Timestamp(row["last_ts"])


def countries() -> list[str]:
    return fetch(q.COUNTRIES_SQL)["country"].tolist()


def kpis(f: q.Filters, known) -> dict:
    row = fetch(*q.kpi_query(f, known)).iloc[0]
    return {
        "revenue": float(row["revenue"]), "lines": int(row["lines"]), "orders": int(row["orders"]),
        "months": int(row["months"]), "non_product_revenue": float(row["non_product_revenue"]),
    }


def monthly(f, known) -> pd.DataFrame:
    frame = _numeric(fetch(*q.monthly_query(f, known)), "revenue", "orders")
    frame["invoice_month"] = pd.to_datetime(frame["invoice_month"])
    return frame.sort_values("invoice_month").reset_index(drop=True)


def top_products(f, known) -> pd.DataFrame:
    return _numeric(fetch(*q.top_products_query(f, known)), "revenue", "units")


def product_table(f, known) -> pd.DataFrame:
    return _numeric(fetch(*q.product_table_query(f, known)), "revenue", "units", "orders")


def country_revenue(f, known) -> pd.DataFrame:
    return _numeric(fetch(*q.country_query(f, known)), "revenue", "orders")


def explorer(f, known, scope: str) -> pd.DataFrame:
    frame = fetch(*q.explorer_query(f, known, scope))
    return _numeric(frame, "quantity", "unit_price", "line_revenue")
