"""Dashboard Overview: KPI cards, monthly trend, revenue by country and top products (all filtered)."""

import calendar

import pandas as pd
import streamlit as st

import charts
import data
import filters_ui
import queries as q
import theme

f, known, (first_day, last_day, last_ts) = filters_ui.context()
theme.header("E-Commerce Sales Analytics",
             "Insights from an end-to-end data engineering pipeline: Python → Snowflake → dbt → Streamlit "
             "(orchestrated by Apache Airflow). Gross valid-sales revenue before returns.")
filtered = filters_ui.banner(f, first_day, last_day)

kpi = data.kpis(f, known)
if kpi["lines"] == 0:
    st.warning("No valid sales lines match the current filters. Widen the date range or clear the search.")
    st.stop()

suffix = " (filtered)" if filtered else ""
cards = [("Total Revenue", f"{kpi['revenue']:,.2f}"), ("Valid Sales Records", f"{kpi['lines']:,}"),
         ("Distinct Orders", f"{kpi['orders']:,}"), ("Monthly Periods", f"{kpi['months']:,}")]
for number, (column, (label, value)) in enumerate(zip(st.columns(4), cards), start=1):
    with column:
        theme.kpi_marker(number)
        st.metric(label + suffix, value)

monthly = data.monthly(f, known)
partial = None
last_month = pd.Timestamp(last_ts).to_period("M").to_timestamp()
if last_ts.day < calendar.monthrange(last_ts.year, last_ts.month)[1] and last_month in set(monthly["invoice_month"]):
    partial = last_month

trend, countries_panel = st.columns([3, 2])
with trend, st.container(border=True):
    st.markdown("#### :material/show_chart: Monthly Revenue Trend")
    st.altair_chart(charts.monthly_chart(monthly, partial), width="stretch")
    if partial is not None:
        st.warning(f"{partial:%B %Y} is an incomplete month: the data ends on {last_ts:%d %b %Y}, so its revenue "
                   "is not comparable with full months (amber point).", icon=":material/warning:")
    st.caption("Months are in chronological order. The sample holds only a few blocks of invoices per month, so "
               "monthly values are small and uneven.")
with countries_panel, st.container(border=True):
    st.markdown("#### :material/donut_large: Revenue by Country (Top 5)")
    by_country = data.country_revenue(f, known)
    grouped = q.group_other(by_country, keep=5)
    st.altair_chart(charts.country_donut(grouped), width="stretch")
    top_row = grouped.iloc[0]
    st.caption(f"{top_row['country']} accounts for {top_row['share']:.1%} of the revenue shown. The selection has "
               f"{len(by_country)} country(ies); the sample is UK-heavy and not representative of the full dataset.")

st.markdown("#### :material/emoji_events: Top 10 Products by Revenue")
top = data.top_products(f, known)
table_panel, bars_panel = st.columns(2)
if top.empty:
    st.info("No merchandise products match the filters.")
else:
    ranked = top.reset_index(drop=True)
    ranked.index = ranked.index + 1
    with table_panel, st.container(border=True):
        st.dataframe(
            ranked.rename(columns={"stock_code": "Stock code", "description": "Description", "revenue": "Revenue",
                                   "units": "Units"}),
            width="stretch", height=min(390, 38 + 35 * len(ranked)),
            column_config={"Stock code": st.column_config.TextColumn(width=62),
                           "Description": st.column_config.TextColumn(width=125),
                           "Revenue": st.column_config.NumberColumn(format="%.2f", width=66),
                           "Units": st.column_config.NumberColumn(format="localized", width=48)},
        )
    with bars_panel, st.container(border=True):
        st.altair_chart(charts.top_products_chart(top), width="stretch")
st.caption(f"Merchandise only. Non-product lines (postage, fees, vouchers, manual entries) add "
           f"{kpi['non_product_revenue']:,.2f} to the total revenue above but are excluded from product rankings.")
