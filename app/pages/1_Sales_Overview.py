from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import available_years, build_metric_frames, date_range_label, filter_options, filter_tables
from runtime import load_cached_dashboard_tables
from ui import PALETTE, base_layout, business_filters, delta_pct, filter_caption, money, pct, prepare_chart, ranked_share_chart, year_selection_label


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


tables = load_cached_dashboard_tables()
selected_years = base_layout(
    "Sales Overview",
    "Revenue, basket size, payment mix, and customer segment movement across the licensed Maycee dataset.",
    available_years(tables),
    date_range_label(tables),
)
filters = business_filters(filter_options(tables))

metrics = build_metric_frames(filter_tables(tables, years=selected_years, **filters))
if metrics["monthly_sales"].empty:
    st.warning("No licensed rows match the selected filters.")
    st.stop()

kpis = metrics["kpis"].iloc[0]
st.info(
    f"Showing {year_selection_label(selected_years)}. "
    f"Available coverage: {date_range_label(tables)}. {filter_caption(filters)}"
)

monthly = metrics["monthly_sales"].copy()
latest = monthly.iloc[-1]
previous = monthly.iloc[-2] if len(monthly) > 1 else None
prior_year_month = monthly[
    (monthly["year"] == latest["year"] - 1) & (monthly["month_number"] == latest["month_number"])
]
prior_year = prior_year_month.iloc[0] if not prior_year_month.empty else None

primary_cols = st.columns(3)
primary_cols[0].metric("Revenue", money(kpis["revenue"]))
primary_cols[1].metric("Transactions", f"{int(kpis['transactions']):,}")
primary_cols[2].metric("Average Order Value", f"${kpis['avg_basket']:,.2f}")
ratio_cols = st.columns(2)
ratio_cols[0].metric("Gross Margin", pct(kpis["gross_margin_pct"]))
ratio_cols[1].metric("Return Value Rate", pct(kpis["return_value_pct"], 2))

trend_cols = st.columns(3)
trend_cols[0].metric("Latest Month Revenue", money(latest["revenue"]))
trend_cols[1].metric(
    "MoM Revenue",
    money(latest["revenue"]),
    delta=delta_pct(float(latest["revenue"]), float(previous["revenue"])) if previous is not None else None,
)
trend_cols[2].metric(
    "YoY Revenue",
    money(latest["revenue"]),
    delta=delta_pct(float(latest["revenue"]), float(prior_year["revenue"])) if prior_year is not None else None,
)

st.divider()

left, right = st.columns([1.45, 1])

with left:
    monthly["month_name"] = monthly["month_number"].apply(lambda month: MONTH_LABELS[int(month) - 1])
    monthly["year"] = monthly["year"].astype(str)
    fig = px.line(
        monthly,
        x="month_name",
        y="revenue",
        color="year",
        markers=True,
        color_discrete_sequence=[PALETTE["blue"], PALETTE["emerald"], PALETTE["amber"]],
        labels={"month_name": "Month", "revenue": "Revenue ($)", "year": "Year"},
        title="Monthly Revenue YoY",
    )
    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MONTH_LABELS),
        yaxis=dict(title="Revenue ($)"),
    )
    st.plotly_chart(prepare_chart(fig, 430), use_container_width=True)

with right:
    payment = metrics["payment_mix"].copy()
    payment["payment_method"] = payment["payment_method"].str.title()
    fig = ranked_share_chart(
        payment["payment_method"],
        payment["revenue"],
        "Payment Mix",
        height=430,
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Customer Segments")
segments = metrics["customer_segments"].copy()
segments["customer_segment"] = segments["customer_segment"].str.title()
fig = px.bar(
    segments,
    x="customer_segment",
    y="revenue",
    color="avg_basket",
    color_continuous_scale="Tealgrn",
    labels={"customer_segment": "Segment", "revenue": "Revenue ($)", "avg_basket": "Average Basket"},
    text="transactions",
)
fig.update_traces(texttemplate="%{text} txns", textposition="outside")
st.plotly_chart(prepare_chart(fig, 380), use_container_width=True)
segment_display = segments.rename(
    columns={
        "customer_segment": "Customer Segment",
        "revenue": "Revenue ($)",
        "transactions": "Transactions",
        "avg_basket": "Average Order Value ($)",
    }
)
st.dataframe(segment_display, use_container_width=True, hide_index=True)
