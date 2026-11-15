"""Product Analytics: sortable product performance table (filtered)."""

import streamlit as st

import data
import filters_ui
import theme

f, known, (first_day, last_day, _) = filters_ui.context()
theme.header("Product Analytics", "Revenue and units per stock code, merchandise only.")
filters_ui.banner(f, first_day, last_day)

table = data.product_table(f, known)
if table.empty:
    st.warning("No merchandise products match the current filters.")
    st.stop()

kpi = data.kpis(f, known)
c1, c2, c3 = st.columns(3)
c1.metric("Products listed", f"{len(table):,}")
c2.metric("Product revenue", f"{table['revenue'].sum():,.2f}")
c3.metric("Units sold", f"{int(table['units'].sum()):,}")

with st.container(border=True):
    st.subheader("Product Performance")
    st.dataframe(
        table.rename(columns={"stock_code": "Stock code", "description": "Description", "revenue": "Revenue",
                              "units": "Units sold", "orders": "Orders"}),
        hide_index=True, width="stretch", height=480,
        column_config={"Revenue": st.column_config.NumberColumn(format="%.2f"),
                       "Units sold": st.column_config.NumberColumn(format="localized"),
                       "Orders": st.column_config.NumberColumn(format="localized")},
    )
    st.caption(f"Click a column header to sort. One description is shown per stock code. Non-product lines "
               f"(postage, fees, vouchers, manual entries) contribute {kpi['non_product_revenue']:,.2f} to overall "
               "revenue but are excluded from this table. The list is capped at 1,000 products.")
