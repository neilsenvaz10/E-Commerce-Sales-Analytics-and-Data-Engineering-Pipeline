"""Offline tests for the dashboard: no Snowflake, no network. Run from the project root:

    .\\.venv\\Scripts\\python.exe streamlit_app\\test_dashboard.py

Part 1 checks the SQL builders (bound parameters, no user text in SQL). Part 2 renders every page with
Streamlit's AppTest against STUB data (clearly fake, used only to prove the pages run and respond to
filters; no figure from it is ever shown in the real dashboard).
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import queries as q  # noqa: E402

PASSED = FAILED = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    PASSED, FAILED = PASSED + ok, FAILED + (not ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


KNOWN = ["France", "Germany", "United Kingdom"]
BASE = q.Filters(start=date(2010, 12, 1), end=date(2011, 12, 9))
EVIL = "x'); DROP TABLE fct_sales; --"

# ---- part 1: SQL builders ---------------------------------------------------------------------
filters_list = [
    BASE,
    q.Filters(BASE.start, BASE.end, ("Germany", "France")),
    q.Filters(BASE.start, BASE.end, (), "heart"),
    q.Filters(BASE.start, BASE.end, ("Germany",), "50%_off"),
    q.Filters(BASE.start, BASE.end, (EVIL, "Germany"), EVIL),
]
builders = [q.kpi_query, q.monthly_query, q.top_products_query, q.product_table_query, q.country_query, q.explorer_query]
ok_count = ok_inj = ok_ro = True
for f in filters_list:
    for build in builders:
        sql, params = build(f, KNOWN)
        ok_count &= sql.count("?") == len(params)
        ok_inj &= EVIL not in sql and "DROP" not in sql and "50%_off" not in sql
        ok_ro &= (re.match(r"/\* \w+ \*/\s*select", sql) is not None and ";" not in sql
                  and re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant)\b", sql, re.I) is None
                  and "from fct_sales" in sql)
check("every query has exactly one bound value per ? placeholder", ok_count)
check("user text (including an injection attempt) never appears in the SQL text", ok_inj)
check("every query is a single read-only SELECT on fct_sales", ok_ro)

sql, params = q.build_where(q.Filters(BASE.start, BASE.end, (EVIL, "Germany", "Atlantis"), ""), KNOWN)
check("unknown country values are dropped, known ones bound", params[2:] == ["Germany"] and sql.count("?") == 3, str(params))
sql, params = q.build_where(q.Filters(BASE.start, BASE.end, (), "50%_off"), KNOWN)
check("LIKE wildcards in the search are escaped", params[2] == "%50\\%\\_off%", str(params))
check("search is trimmed, cleaned and capped", q.clean_search("  a\tb\n" + "z" * 200) == "a b " + "z" * (q.MAX_SEARCH_LENGTH - 4))
check("dates are bound as ISO strings", params[:2] == ["2010-12-01", "2011-12-09"])
try:
    q.build_where(BASE, KNOWN, scope="; drop table x")
    check("unknown scope is rejected", False)
except ValueError:
    check("unknown scope is rejected", True)
check("product rankings exclude non-product lines", "not is_non_product" in q.top_products_query(BASE, KNOWN)[0]
      and "not is_non_product" in q.product_table_query(BASE, KNOWN)[0])
check("all queries are bounded by LIMIT", all("limit" in b(BASE, KNOWN)[0].lower() for b in builders if b is not q.kpi_query))
check("top products are ordered by revenue descending", "order by revenue desc" in q.top_products_query(BASE, KNOWN)[0])
check("monthly query is ordered chronologically", "order by invoice_month" in q.monthly_query(BASE, KNOWN)[0])

frame = pd.DataFrame({"country": list("ABCDEFG"), "revenue": [70, 10, 8, 5, 3, 2, 2]})
grouped = q.group_other(frame, keep=3)
check("country grouping keeps the top rows and sums the rest into Other",
      list(grouped["country"]) == ["A", "B", "C", "Other"] and grouped["revenue"].iloc[-1] == 12)
check("shares are computed from the data and sum to 1", abs(grouped["share"].sum() - 1) < 1e-9 and abs(grouped["share"].iloc[0] - 0.70) < 1e-9)
check("filter detection", not q.is_filtered(BASE, BASE.start, BASE.end) and q.is_filtered(q.Filters(BASE.start, BASE.end, (), "x"), BASE.start, BASE.end))

# ---- part 2: render every page with stub data ------------------------------------------------
os.environ.update({"SNOWFLAKE_ACCOUNT": "stub", "SNOWFLAKE_READER_USER": "stub", "SNOWFLAKE_READER_PRIVATE_KEY_PATH": "stub"})
import db  # noqa: E402

SEEN: list[tuple[str, tuple]] = []
MONTHS = pd.to_datetime(["2010-12-01", "2011-01-01", "2011-12-01"])


def stub_query(sql: str, params=None) -> pd.DataFrame:
    name = re.match(r"/\* (\w+) \*/", sql).group(1)
    SEEN.append((name, tuple(params or ())))
    narrowed = bool(params) and len(params) > 2
    if name == "bounds":
        return pd.DataFrame({"first_day": [date(2010, 12, 1)], "last_day": [date(2011, 12, 8)],
                             "last_ts": [datetime(2011, 12, 8, 13, 27)]})
    if name == "countries":
        return pd.DataFrame({"country": KNOWN})
    if name == "kpi":
        return pd.DataFrame({"revenue": [5.0 if narrowed else 100.0], "lines": [2 if narrowed else 6],
                             "orders": [1 if narrowed else 3], "months": [1 if narrowed else 3], "non_product_revenue": [1.0]})
    if name == "monthly":
        return pd.DataFrame({"invoice_month": MONTHS, "revenue": [10.0, 20.0, 5.0], "orders": [1, 1, 1]})
    if name in ("top_products", "product_table"):
        return pd.DataFrame({"stock_code": ["A1", "B2"], "description": ["STUB ONE", "STUB TWO"],
                             "revenue": [9.0, 4.0], "units": [3, 2], "orders": [2, 1]})
    if name == "country_revenue":
        return pd.DataFrame({"country": ["United Kingdom", "Germany"], "revenue": [90.0, 10.0], "orders": [2, 1]})
    if name == "explorer":
        return pd.DataFrame({"invoice_no": ["1"], "stock_code": ["A1"], "description": ["STUB ONE"], "quantity": [1],
                             "unit_price": [2.0], "line_revenue": [2.0], "invoice_ts": [datetime(2011, 1, 1)],
                             "country": ["Germany"], "customer_id": [1], "is_non_product": [False]})
    # business-question queries (fixed SQL from questions.py, no comment header)
    raise AssertionError("unexpected query " + name)


def stub_question_query(sql: str, params=None) -> pd.DataFrame:
    if not sql.lstrip().startswith("/*"):
        SEEN.append(("question", ()))
        if "sum(line_revenue)            as total_revenue" in sql:
            return pd.DataFrame({"total_revenue": [100.0], "orders": [3], "lines": [6]})
        if "group by stock_code" in sql:
            return pd.DataFrame({"stock_code": ["A1"], "description": ["STUB ONE"], "revenue": [9.0], "units": [3]})
        return pd.DataFrame({"invoice_month": MONTHS, "revenue": [10.0, 20.0, 5.0]})
    return stub_query(sql, params)


db.run_query = stub_question_query

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(HERE / "app.py")


def fresh(page: str | None = None, state: dict | None = None) -> AppTest:
    """Start the app; `state` presets widget values (AppTest cannot re-run a navigation app after set_value)."""
    at = AppTest.from_file(APP, default_timeout=60)
    for key, value in (state or {}).items():
        at.session_state[key] = value
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def texts(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [w.value for w in at.warning] + [i.value for i in at.info]
    parts += [m.label for m in at.metric] + [str(m.value) for m in at.metric] + [s.value for s in at.subheader] + [t.value for t in at.title]
    return " | ".join(parts)


at = fresh()
check("overview renders without exceptions", not at.exception, str([e.value for e in at.exception]))
check("overview shows the four KPI cards", [m.label for m in at.metric] == ["Total Revenue", "Valid Sales Records", "Distinct Orders", "Monthly Periods"], str([m.label for m in at.metric]))
check("unfiltered KPI cards show no 'filtered' label or banner", not any("(filtered)" in m.label for m in at.metric) and not any("Filtered subset" in i.value for i in at.info))
check("December 2011 partial-month warning is shown", any("incomplete month" in w.value and "December 2011" in w.value for w in at.warning))
check("non-product explanation is shown", "excluded from product rankings" in texts(at))
check("sample vs full dataset is labelled", "744-row sample" in texts(at) and "541,909" in texts(at))

at = fresh(state={"flt_countries_0": ["Germany"]})
check("country filter reaches the queries as a bound value", any(n == "kpi" and "Germany" in p for n, p in SEEN))
check("filtered KPI cards are labelled and a banner explains it",
      all("(filtered)" in m.label for m in at.metric) and any("Filtered subset" in i.value for i in at.info),
      str([m.label for m in at.metric]))
at = fresh(state={"flt_search_0": EVIL})
check("injection-style search is bound, not executed",
      any(n == "kpi" and any(str(v).startswith("%x'") for v in p) for n, p in SEEN) and not at.exception)
at = fresh("pages/products.py", state={"flt_countries_0": ["France"]})
check("filters also reach the product table query", any(n == "product_table" and "France" in p for n, p in SEEN))
at = fresh("pages/explorer.py", state={"flt_search_0": "heart"})
check("filters also reach the data explorer query", any(n == "explorer" and any("heart" in str(v) for v in p) for n, p in SEEN))

for title, page in [("Business Questions", "pages/business_questions.py"), ("Product Analytics", "pages/products.py"),
                    ("Data Explorer", "pages/explorer.py"), ("About the Project", "pages/about.py")]:
    page_at = fresh(page)
    check(f"{title} renders without exceptions", not page_at.exception, str([e.value for e in page_at.exception]))
    if title == "Business Questions":
        check("Business Questions states it ignores the filters and covers the 744-row sample",
              any("not affected by the dashboard filters" in i.value and "744-row sample" in i.value for i in page_at.info))
        page_at.button[0].click().run()
        check("example question 1 answers with the total-revenue metric", any(m.label == "Total revenue" for m in page_at.metric))
        page_at.text_input[0].set_value("Delete everything; drop table fct_sales").run()
        check("unsupported question gets a safe refusal and no query",
              any("I can only answer" in i.value for i in page_at.info) and not page_at.exception)
        page_at.text_input[0].set_value("what is the total revenue").run()
        check("typed supported question is routed to the fixed total-revenue answer",
              any(m.label == "Total revenue" for m in page_at.metric) and not page_at.exception)
        page_at.text_input[0].set_value("monthly sales trend").run()
        check("typed monthly question is routed to the monthly answer",
              any("monthly revenue trends" in sh.value for sh in page_at.subheader) and not page_at.exception)
    if title == "About the Project":
        body = " ".join(m.value for m in page_at.markdown) + " ".join(c.value for c in page_at.code)
        check("About mentions the billing restriction, Python ingestion and licence",
              "billing restriction" in body and "Python-based ingestion" in body and "CC BY 4.0" in body)

print(f"\nRESULT: {'PASS' if not FAILED else 'FAIL'}  ({PASSED} passed, {FAILED} failed)")
sys.exit(1 if FAILED else 0)
