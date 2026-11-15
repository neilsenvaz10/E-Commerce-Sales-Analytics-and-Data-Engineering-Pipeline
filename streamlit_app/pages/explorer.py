"""Data Explorer: a bounded, read-only preview of valid sales lines with CSV download (filtered)."""

import streamlit as st

import data
import filters_ui
import queries as q
import theme

f, known, (first_day, last_day, _) = filters_ui.context()
theme.header("Data Explorer", "Read-only preview of ANALYTICS.FCT_SALES. Nothing here can change the data.")
filters_ui.banner(f, first_day, last_day)

labels = {"all": "All valid sales lines", "products": "Merchandise only", "non_products": "Non-product lines only"}
scope = st.selectbox("Line type", list(labels), format_func=labels.get)

frame = data.explorer(f, known, scope)
if frame.empty:
    st.warning("No rows match the current filters.")
    st.stop()

with st.container(border=True):
    st.dataframe(frame, hide_index=True, width="stretch", height=480)
    st.caption(f"Showing {len(frame):,} rows (preview limit {q.EXPLORER_LIMIT}), ordered by invoice time. "
               "Customer IDs are the anonymised IDs published with the UCI dataset.")
    st.download_button("Download these rows as CSV", frame.to_csv(index=False).encode("utf-8"),
                       file_name="fct_sales_preview.csv", mime="text/csv")
