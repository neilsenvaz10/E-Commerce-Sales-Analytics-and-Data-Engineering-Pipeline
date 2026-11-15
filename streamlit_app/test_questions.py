"""Offline checks for the question matcher and the fixed SQL (no Snowflake needed).

Run:  .\\.venv\\Scripts\\python.exe streamlit_app\\test_questions.py
"""

import re

from questions import QUESTIONS, match_question

CASES = {
    "What is the total revenue?": "total_revenue",
    "how much revenue did we make": "total_revenue",
    "Show total sales": "total_revenue",
    "Show the top 10 products by sales": "top_products",
    "which product is the best selling": "top_products",
    "top products by revenue": "top_products",
    "Show monthly sales trends": "monthly_revenue",
    "revenue per month": "monthly_revenue",
    "what is the monthly revenue trend": "monthly_revenue",
}
UNSUPPORTED = ["hello", "delete everything", "weather today", "drop table fct_sales"]

failures = 0
for text, expected in CASES.items():
    got = match_question(text)
    ok = got is not None and got.key == expected
    failures += not ok
    print(("PASS" if ok else "FAIL"), f"{text!r} -> {got.key if got else None} (expected {expected})")
for text in UNSUPPORTED:
    got = match_question(text)
    ok = got is None
    failures += not ok
    print(("PASS" if ok else "FAIL"), f"unsupported {text!r} -> {got.key if got else None}")

for q in QUESTIONS:
    sql = q.sql.lower()
    ok = sql.strip().startswith("select") and not re.search(r"\b(insert|update|delete|drop|alter|create|merge|truncate|grant)\b", sql)
    ok = ok and "{" not in q.sql and "%s" not in q.sql   # fixed text, no placeholders for user input
    failures += not ok
    print(("PASS" if ok else "FAIL"), f"{q.key}: read-only fixed SELECT")

print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures})")
raise SystemExit(1 if failures else 0)
