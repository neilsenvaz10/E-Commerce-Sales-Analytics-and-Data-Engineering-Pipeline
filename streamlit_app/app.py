"""E-Commerce Sales Analytics dashboard (Streamlit, multi-page).

Run (project root, PowerShell):
    .\\.venv\\Scripts\\streamlit.exe run streamlit_app\\app.py --server.address 127.0.0.1

Data: ANALYTICS.FCT_SALES in Snowflake, read with the read-only READER_USER (key-pair login). The data
is the deterministic 744-row SAMPLE of the 541,909-row UCI Online Retail dataset, not the full dataset.
Settings come from environment variables / .env (see .env.example). No credentials are stored here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import db  # noqa: E402
import filters_ui  # noqa: E402
import theme  # noqa: E402

st.set_page_config(page_title="E-Commerce Sales Analytics", page_icon=":material/insights:", layout="wide")
theme.apply()
st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

missing = db.missing_settings()
if missing:
    st.title("E-Commerce Sales Analytics")
    st.error("Snowflake is not configured yet. Set these in .env: " + ", ".join(missing))
    st.stop()

pages = [
    st.Page("pages/overview.py", title="Dashboard Overview", icon=":material/dashboard:", default=True),
    st.Page("pages/business_questions.py", title="Business Questions", icon=":material/forum:"),
    st.Page("pages/products.py", title="Product Analytics", icon=":material/inventory_2:"),
    st.Page("pages/explorer.py", title="Data Explorer", icon=":material/table_view:"),
    st.Page("pages/about.py", title="About the Project", icon=":material/info:"),
]
navigation = st.navigation(pages)

filters_ui.store(filters_ui.render())
navigation.run()
