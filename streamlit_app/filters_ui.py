"""Sidebar filters shared by every page (date range, countries, product search)."""

from __future__ import annotations

import streamlit as st

import data
import queries as q


def _version() -> int:
    return st.session_state.get("flt_version", 0)


def _reset() -> None:
    """Button callback: new widget keys mean brand-new widgets at their defaults. (Assigning or popping the old
    widgets' state can lose a race with a late 'blur' update from a date box that still has focus.)"""
    st.session_state["flt_version"] = _version() + 1


def render() -> tuple[q.Filters, list[str], tuple]:
    """Draw the filters and return (filters, known_countries, (first_day, last_day, last_ts))."""
    first_day, last_day, last_ts = data.bounds()
    known = data.countries()

    v = _version()
    st.sidebar.markdown("### Filters")
    picked = st.sidebar.date_input("Invoice date range", value=(first_day, last_day),
                                   min_value=first_day, max_value=last_day, key=f"flt_dates_{v}")
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start, end = picked
    else:   # the user is still choosing the second date
        start, end = first_day, last_day
    countries = st.sidebar.multiselect("Country (empty = all)", known, key=f"flt_countries_{v}")
    search = st.sidebar.text_input("Product search", key=f"flt_search_{v}", max_chars=q.MAX_SEARCH_LENGTH,
                                   placeholder="description or stock code")
    st.sidebar.button("Clear filters", on_click=_reset, width="stretch", icon=":material/filter_alt_off:")
    st.sidebar.caption("Filters apply to Overview, Product Analytics and Data Explorer. "
                       "Business Questions always uses the whole sample.")
    st.sidebar.info("**Dataset:** UCI Online Retail  \n**Sample:** 744 of 541,909 rows  \n**Source:** CC BY 4.0",
                    icon=":material/info:")

    filters = q.Filters(start=start, end=end, countries=tuple(countries), search=search)
    return filters, known, (first_day, last_day, last_ts)


def store(ctx: tuple) -> None:
    st.session_state["ctx"] = ctx


def context() -> tuple[q.Filters, list[str], tuple]:
    return st.session_state["ctx"]


def banner(f: q.Filters, first_day, last_day) -> bool:
    """Say clearly when numbers are a filtered subset. Returns True if filters are active."""
    if q.is_filtered(f, first_day, last_day):
        st.info("**Filtered subset.** The figures below cover only: " + q.describe_filters(f, first_day, last_day)
                + ". Clear the filters in the sidebar to see the whole 744-row sample.", icon=":material/filter_alt:")
        return True
    return False
