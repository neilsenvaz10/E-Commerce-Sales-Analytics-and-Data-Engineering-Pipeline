"""The three predefined business questions and a simple keyword matcher.

There is no free-form SQL and no language model: a typed question is matched to one of three
fixed templates by keywords, and each template has one fixed, read-only query. User text is
never placed into SQL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    key: str
    title: str
    example: str
    keywords: tuple[str, ...]   # each keyword found in the text adds one point
    sql: str


QUESTIONS: tuple[Question, ...] = (
    Question(
        key="total_revenue",
        title="What is the total revenue?",
        example="What is the total revenue?",
        keywords=("total revenue", "total sales", "how much revenue", "how much did we sell", "revenue"),
        sql="""
            select sum(line_revenue)            as total_revenue,
                   count(distinct invoice_no)   as orders,
                   count(*)                     as lines
            from fct_sales
        """,
    ),
    Question(
        key="top_products",
        title="Which products generate the most revenue?",
        example="Show the top 10 products by sales.",
        keywords=("top product", "best selling", "best-selling", "top selling", "product", "item"),
        sql="""
            select stock_code,
                   min(description)  as description,
                   sum(line_revenue) as revenue,
                   sum(quantity)     as units
            from fct_sales
            where not is_non_product
            group by stock_code
            order by revenue desc
            limit 10
        """,
    ),
    Question(
        key="monthly_revenue",
        title="What are the monthly revenue trends?",
        example="Show monthly sales trends.",
        keywords=("monthly", "per month", "each month", "month", "trend", "over time"),
        sql="""
            select invoice_month,
                   sum(line_revenue) as revenue
            from fct_sales
            group by invoice_month
            order by invoice_month
        """,
    ),
)


def match_question(text: str) -> Question | None:
    """Return the best-matching question, or None if no keyword matches.

    Longer keywords count more, so "monthly revenue" goes to the monthly trend (it contains
    "month" and "revenue") and "top products by revenue" goes to the products question.
    """
    lowered = " ".join(text.lower().split())
    best, best_score = None, 0
    for question in QUESTIONS:
        score = sum(len(k.split()) + 1 for k in question.keywords if k in lowered)
        # a specific topic word beats the generic word "revenue"
        if question.key != "total_revenue" and score > 0:
            score += 1
        if score > best_score:
            best, best_score = question, score
    return best
