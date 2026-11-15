"""Altair charts. All values come from the DataFrames passed in (real query results)."""

from __future__ import annotations

import altair as alt
import pandas as pd

import theme


def monthly_chart(frame: pd.DataFrame, partial_month: pd.Timestamp | None = None) -> alt.Chart:
    """Chronological monthly revenue; a partial last month is drawn in amber."""
    frame = frame.sort_values("invoice_month")
    tips = [alt.Tooltip("invoice_month:T", title="Month", format="%B %Y"),
            alt.Tooltip("revenue:Q", title="Revenue", format=",.2f")]
    if "orders" in frame.columns:
        tips.append(alt.Tooltip("orders:Q", title="Orders", format=","))
    base = alt.Chart(frame).encode(
        x=alt.X("invoice_month:T", title="Month", axis=alt.Axis(format="%b %Y", labelAngle=-40, tickCount="month", labelOverlap=False),
                scale=alt.Scale(padding=14)),
        y=alt.Y("revenue:Q", title="Revenue", axis=alt.Axis(format=",.0f")),
        tooltip=tips,
    )
    layers = [base.mark_area(color=theme.PURPLE, opacity=0.18, interpolate="monotone"),
              base.mark_line(color=theme.PURPLE, strokeWidth=2.5, interpolate="monotone"),
              base.mark_point(color=theme.PURPLE, filled=True, size=70)]
    if len(frame) == 1:   # a single month has no line or area, so draw a bar as well
        layers.insert(0, base.mark_bar(color=theme.PURPLE, opacity=0.55, size=48))
    if partial_month is not None:
        partial = frame[frame["invoice_month"] == partial_month]
        if not partial.empty:
            layers.append(alt.Chart(partial).mark_point(color=theme.AMBER, filled=True, size=130).encode(
                x=alt.X("invoice_month:T", scale=alt.Scale(padding=14)), y="revenue:Q"))
    return alt.layer(*layers).properties(height=320).interactive(bind_y=False)


def top_products_chart(frame: pd.DataFrame) -> alt.Chart:
    """Horizontal bars, largest revenue at the top."""
    frame = frame.sort_values("revenue", ascending=False).copy()
    frame["label"] = frame["stock_code"] + "  " + frame["description"].fillna("").str.slice(0, 30)
    return (
        alt.Chart(frame).mark_bar(color=theme.PURPLE, cornerRadiusEnd=4)
        .encode(
            y=alt.Y("label:N", sort=list(frame["label"]), title=None, axis=alt.Axis(labelLimit=300)),
            x=alt.X("revenue:Q", title="Revenue", axis=alt.Axis(format=",.0f")),
            tooltip=[alt.Tooltip("stock_code:N", title="Stock code"),
                     alt.Tooltip("description:N", title="Description"),
                     alt.Tooltip("revenue:Q", title="Revenue", format=",.2f"),
                     alt.Tooltip("units:Q", title="Units sold", format=",")],
        )
        .properties(height=max(120, 32 * len(frame)))
    )


def country_donut(frame: pd.DataFrame) -> alt.Chart:
    """Donut of revenue by country (frame from queries.group_other: country, revenue, share).

    The legend shows each share and the centre shows the total; both are computed from the data.
    """
    frame = frame.copy()
    frame["label"] = frame["country"] + "   " + (frame["share"] * 100).map("{:.1f}%".format)
    order = list(frame["label"])
    arcs = (
        alt.Chart(frame).mark_arc(innerRadius=46, outerRadius=74, stroke="#0e1224", strokeWidth=2)
        .encode(
            theta=alt.Theta("revenue:Q", stack=True),
            color=alt.Color("label:N", sort=order, scale=alt.Scale(domain=order, range=theme.PALETTE[: len(order)]),
                            legend=alt.Legend(title=None, orient="bottom", columns=2, offset=22, labelFontSize=13, symbolType="square")),
            order=alt.Order("revenue:Q", sort="descending"),
            tooltip=[alt.Tooltip("country:N", title="Country"),
                     alt.Tooltip("revenue:Q", title="Revenue", format=",.2f"),
                     alt.Tooltip("share:Q", title="Share", format=".1%")],
        )
    )
    total = float(frame["revenue"].sum())
    centre = pd.DataFrame({"value": [f"{total:,.2f}"], "caption": ["Total Revenue"]})
    value = alt.Chart(centre).mark_text(fontSize=20, fontWeight="bold", color="#e8eaf6", dy=-8).encode(text="value:N")
    caption = alt.Chart(centre).mark_text(fontSize=12, color="#aab0d0", dy=14).encode(text="caption:N")
    return (arcs + value + caption).properties(height=230, padding={"left": 8, "right": 8, "top": 8, "bottom": 8})
