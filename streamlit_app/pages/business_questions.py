"""Business Questions: the three predefined questions, matched by keywords to fixed read-only queries.

There is no free-form SQL and no language model. Typed text is only compared with keywords and is
never placed into SQL. These answers always use the whole sample (dashboard filters do not apply).
"""

import calendar

import pandas as pd
import streamlit as st

import charts
import data
import filters_ui
import theme
from questions import QUESTIONS, match_question

filters_ui.context()   # keeps the sidebar filters alive; they do not affect this page
theme.header("Business Questions", "Ask one of the three supported questions, or click an example.")
st.info("**These results are for the full 744-row sample and are not affected by the dashboard filters.** "
        "The sample is a small subset of the 541,909-row UCI dataset.", icon=":material/info:")


def show_answer(question) -> None:
    frame = data.fetch(question.sql)
    st.subheader(question.title)
    if frame.empty:
        st.warning("The query returned no rows. Has the pipeline run?")
        return
    if question.key == "total_revenue":
        row = frame.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total revenue", f"{float(row['total_revenue']):,.2f}")
        c2.metric("Orders", f"{int(row['orders']):,}")
        c3.metric("Order lines", f"{int(row['lines']):,}")
        st.caption("Gross valid-sales revenue (quantity x unit price) before any returns; includes valid postage "
                   "and fee lines.")
    elif question.key == "top_products":
        frame["revenue"] = pd.to_numeric(frame["revenue"])
        frame["units"] = pd.to_numeric(frame["units"])
        st.altair_chart(charts.top_products_chart(frame), width="stretch")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Merchandise only: postage, fees, vouchers and manual entries are excluded from product rankings "
                   "(they still count toward total revenue).")
    else:
        frame["revenue"] = pd.to_numeric(frame["revenue"])
        frame["invoice_month"] = pd.to_datetime(frame["invoice_month"])
        _, _, last_ts = filters_ui.context()[2]
        last_month = pd.Timestamp(last_ts).to_period("M").to_timestamp()
        partial = last_month if last_ts.day < calendar.monthrange(last_ts.year, last_ts.month)[1] else None
        st.altair_chart(charts.monthly_chart(frame, partial), width="stretch")
        shown = frame[["invoice_month", "revenue"]].assign(invoice_month=frame["invoice_month"].dt.strftime("%Y-%m"))
        st.dataframe(shown, hide_index=True, width="stretch",
                     column_config={"revenue": st.column_config.NumberColumn(format="%.2f")})
        if partial is not None:
            st.caption(f"{last_month:%B %Y} is a partial month (data ends {last_ts:%d %b %Y}).")


cols = st.columns(len(QUESTIONS))
pressed = [col.button(item.example, width="stretch") for item, col in zip(QUESTIONS, cols)]   # draw all three first
clicked = next((item for item, was_pressed in zip(QUESTIONS, pressed) if was_pressed), None)
typed = st.text_input("Your question", placeholder="e.g. What is the total revenue?", max_chars=200)

question = clicked or (match_question(typed) if typed.strip() else None)
if typed.strip() and question is None and clicked is None:
    st.info("I can only answer: " + " | ".join(item.title for item in QUESTIONS)
            + ". Other questions are not supported, and no SQL is generated from typed text.")
elif question is not None:
    show_answer(question)
