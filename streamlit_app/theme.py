"""Shared look: dark navy panels with a purple accent. Colours also live in .streamlit/config.toml."""

from __future__ import annotations

import streamlit as st

PURPLE = "#8b5cf6"
PURPLE_LIGHT = "#c4b5fd"
AMBER = "#f59e0b"
PALETTE = ["#8b5cf6", "#3b82f6", "#22d3ee", "#f59e0b", "#f472b6", "#94a3b8"]

# KPI accents: (border, tint, icon background, icon colour, Material icon name)
KPI_STYLES = {
    1: ("#1f9d6b", "#0f2a2b", "#12503f", "#34d399", "payments"),
    2: ("#2f6fd0", "#0f2036", "#173d73", "#60a5fa", "shopping_cart"),
    3: ("#6d4fd6", "#1a1840", "#2c2566", "#a78bfa", "deployed_code"),
    4: ("#d98a1f", "#2a1f12", "#5c3a0f", "#fbbf24", "calendar_month"),
}


def _kpi_css() -> str:
    rules = []
    for n, (border, tint, icon_bg, icon_fg, icon) in KPI_STYLES.items():
        col = f'[data-testid="stColumn"]:has(.kpi{n}) [data-testid="stMetric"]'
        rules.append(
            f"{col}{{border-color:{border}; background:linear-gradient(135deg,{tint},#141831); "
            f"padding-left:78px; position:relative;}}"
            f"{col}::before{{content:'{icon}'; font-family:'Material Symbols Rounded'; font-size:27px; "
            f"position:absolute; left:16px; top:50%; transform:translateY(-50%); width:44px; height:44px; "
            f"border-radius:50%; background:{icon_bg}; color:{icon_fg}; display:flex; align-items:center; "
            f"justify-content:center; font-feature-settings:'liga';}}")
    return "\n".join(rules)


_CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1360px;}
[data-testid="stMetric"] {background:#171c33; border:1px solid #2b3150; border-radius:14px; padding:16px 20px;}
[data-testid="stMetricLabel"] p {color:#c9cee6; font-size:0.9rem; font-weight:600;}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {white-space:normal !important; overflow:visible !important; text-overflow:clip !important;}
[data-testid="stMetricValue"] {font-size:1.55rem; font-weight:700;}
[data-testid="stMetricValue"] div {overflow:visible !important; text-overflow:clip !important;}
[data-testid="stElementContainer"]:has(.kmark) {display:none;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px; border-color:#2b3150;}
[data-testid="stSidebar"] {border-right:1px solid #2b3150;}
[data-testid="stSidebarHeader"] img {max-height:56px;}
h1, h2, h3 {letter-spacing:-0.01em;}
.badge {display:inline-block; padding:2px 10px; border-radius:999px; background:#2a2250; color:#c4b5fd;
        font-size:.78rem; border:1px solid #4c3b8f;}
%KPI%
</style>
""".replace("%KPI%", _kpi_css())


def apply() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def kpi_marker(number: int) -> None:
    """Invisible marker inside a column so the CSS above can colour that column's metric card."""
    st.markdown(f"<span class='kmark kpi{number}'></span>", unsafe_allow_html=True)


def header(title: str, subtitle: str = "") -> None:
    st.title(title)
    st.markdown(
        "<span class='badge'>744-row sample</span> of the 541,909-row UCI Online Retail dataset", unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)
