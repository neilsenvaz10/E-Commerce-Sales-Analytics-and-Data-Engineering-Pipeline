"""Read-only SQL for the dashboard, built with bound parameters (no Streamlit, no database here).

Every query reads only ANALYTICS.FCT_SALES (valid sales lines). User input (dates, countries, a
product search) is NEVER placed into the SQL text: it is passed as `?` parameters. The only
dynamic SQL is the number of `?` placeholders for the selected countries, and the selected values
are first checked against the list of countries that really exist in the table. Each query starts
with a /* name */ comment (visible in Snowflake query history; also used by the offline tests).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

MAX_SEARCH_LENGTH = 60
MAX_COUNTRIES = 50
EXPLORER_LIMIT = 500
PRODUCT_TABLE_LIMIT = 1000
TOP_N = 10

# Fixed fragments only; the key comes from a select box, never from free text.
SCOPES = {
    "all": "",
    "products": " and not is_non_product",
    "non_products": " and is_non_product",
}


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    countries: tuple[str, ...] = ()   # empty means all countries
    search: str = ""                  # matches description or stock code


def clean_search(text: str | None) -> str:
    """Trim, drop control characters, collapse spaces and cap the length."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text or "")
    return " ".join(text.split())[:MAX_SEARCH_LENGTH]


def escape_like(text: str) -> str:
    """Make %, _ and the escape character literal inside a LIKE pattern (ESCAPE '\\')."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def valid_countries(selected, known) -> tuple[str, ...]:
    """Keep only selected countries that exist in the table; unknown values are dropped."""
    known_set = set(known)
    return tuple(sorted({c for c in selected if c in known_set}))[:MAX_COUNTRIES]


def build_where(f: Filters, known_countries, scope: str = "all") -> tuple[str, list]:
    """Return (' where ...', params). Placeholders and params always line up one to one."""
    if scope not in SCOPES:
        raise ValueError(f"unknown scope: {scope!r}")
    conditions = ["invoice_ts::date between to_date(?) and to_date(?)"]
    params: list = [f.start.isoformat(), f.end.isoformat()]

    countries = valid_countries(f.countries, known_countries)
    if countries:
        conditions.append("country in (" + ", ".join("?" for _ in countries) + ")")
        params += list(countries)

    term = clean_search(f.search)
    if term:
        pattern = f"%{escape_like(term)}%"
        conditions.append("(description ilike ? escape '\\\\' or stock_code ilike ? escape '\\\\')")
        params += [pattern, pattern]

    return " where " + " and ".join(conditions) + SCOPES[scope], params


# ---- unfiltered helper queries (no parameters) ------------------------------------------------

BOUNDS_SQL = """/* bounds */
select min(invoice_ts)::date as first_day,
       max(invoice_ts)::date as last_day,
       max(invoice_ts)       as last_ts
from fct_sales"""

COUNTRIES_SQL = f"""/* countries */
select distinct country from fct_sales where country is not null order by country limit {MAX_COUNTRIES * 2}"""


# ---- filtered queries ---------------------------------------------------------------------------

def kpi_query(f, known):
    where, params = build_where(f, known)
    return f"""/* kpi */
select coalesce(sum(line_revenue), 0)                         as revenue,
       count(*)                                               as lines,
       count(distinct invoice_no)                             as orders,
       count(distinct invoice_month)                          as months,
       coalesce(sum(iff(is_non_product, line_revenue, 0)), 0) as non_product_revenue
from fct_sales{where}""", params


def monthly_query(f, known):
    where, params = build_where(f, known)
    return f"""/* monthly */
select invoice_month,
       sum(line_revenue)          as revenue,
       count(distinct invoice_no) as orders
from fct_sales{where}
group by invoice_month
order by invoice_month
limit 120""", params


def top_products_query(f, known, limit: int = TOP_N):
    where, params = build_where(f, known, scope="products")
    limit = max(1, min(int(limit), 50))
    return f"""/* top_products */
select stock_code,
       min(description)  as description,
       sum(line_revenue) as revenue,
       sum(quantity)     as units
from fct_sales{where}
group by stock_code
order by revenue desc, stock_code
limit {limit}""", params


def product_table_query(f, known):
    where, params = build_where(f, known, scope="products")
    return f"""/* product_table */
select stock_code,
       min(description)           as description,
       sum(line_revenue)          as revenue,
       sum(quantity)              as units,
       count(distinct invoice_no) as orders
from fct_sales{where}
group by stock_code
order by revenue desc, stock_code
limit {PRODUCT_TABLE_LIMIT}""", params


def country_query(f, known):
    where, params = build_where(f, known)
    return f"""/* country_revenue */
select country,
       sum(line_revenue)          as revenue,
       count(distinct invoice_no) as orders
from fct_sales{where}
group by country
order by revenue desc, country
limit {MAX_COUNTRIES * 2}""", params


def explorer_query(f, known, scope: str = "all"):
    where, params = build_where(f, known, scope=scope)
    return f"""/* explorer */
select invoice_no, stock_code, description, quantity, unit_price, line_revenue,
       invoice_ts, country, customer_id, is_non_product
from fct_sales{where}
order by invoice_ts, invoice_no, stock_code
limit {EXPLORER_LIMIT}""", params


# ---- small pure helpers used by the pages --------------------------------------------------------

def group_other(frame: pd.DataFrame, label: str = "country", value: str = "revenue", keep: int = 5) -> pd.DataFrame:
    """Keep the `keep` largest rows, sum the rest into 'Other', add a percentage from the data."""
    frame = frame.sort_values(value, ascending=False, kind="stable").reset_index(drop=True)
    if len(frame) > keep:
        other = frame.iloc[keep:][value].sum()
        frame = pd.concat([frame.iloc[:keep][[label, value]],
                           pd.DataFrame({label: ["Other"], value: [other]})], ignore_index=True)
    else:
        frame = frame[[label, value]].copy()
    total = frame[value].sum()
    frame["share"] = frame[value] / total if total else 0.0
    return frame


def is_filtered(f: Filters, first_day: date, last_day: date) -> bool:
    return bool(f.countries) or bool(clean_search(f.search)) or f.start != first_day or f.end != last_day


def describe_filters(f: Filters, first_day: date, last_day: date) -> str:
    parts = []
    if f.start != first_day or f.end != last_day:
        parts.append(f"dates {f.start:%d %b %Y} to {f.end:%d %b %Y}")
    if f.countries:
        parts.append("countries: " + ", ".join(f.countries))
    if clean_search(f.search):
        parts.append(f"product search: \"{clean_search(f.search)}\"")
    return "; ".join(parts)
