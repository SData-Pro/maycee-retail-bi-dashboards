from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import available_years, build_metric_frames, date_range_label, enriched_items, enriched_returns, filter_options, filter_tables
from runtime import load_cached_dashboard_tables
from ui import PALETTE, base_layout, business_filters, filter_caption, money, pct, prepare_chart, year_selection_label


tables = load_cached_dashboard_tables()
selected_years = base_layout(
    "Returns",
    "Return value, reason codes, and category-level signals across the licensed dataset.",
    available_years(tables),
    date_range_label(tables),
)
filters = business_filters(filter_options(tables))

filtered_tables = filter_tables(tables, years=selected_years, **filters)
metrics = build_metric_frames(filtered_tables)
returns = enriched_returns(filtered_tables)
items = enriched_items(filtered_tables)
if items.empty:
    st.warning("No licensed rows match the selected filters.")
    st.stop()

st.info(
    f"Showing {year_selection_label(selected_years)}. "
    f"Available coverage: {date_range_label(tables)}. {filter_caption(filters)}"
)

kpis = metrics["kpis"].iloc[0]
volume_cols = st.columns(2)
volume_cols[0].metric("Returns", f"{int(kpis['returns_count']):,}")
volume_cols[1].metric("Return Value", money(kpis["returns_value"]))
ratio_cols = st.columns(2)
ratio_cols[0].metric("Return Value Rate", pct(kpis["return_value_pct"], 2))
ratio_cols[1].metric("Categories Affected", f"{returns['category_name'].nunique():,}")

st.divider()

if returns.empty:
    st.info("No returns match the selected filters.")
    st.stop()

left, right = st.columns(2)
with left:
    reason = (
        returns.groupby("reason", as_index=False)
        .agg(returns=("return_id", "count"), return_amount=("return_amount", "sum"))
        .sort_values("return_amount", ascending=True)
    )
    fig = px.bar(
        reason,
        x="return_amount",
        y="reason",
        orientation="h",
        color="return_amount",
        color_continuous_scale="Reds",
        labels={"return_amount": "Return Value ($)", "reason": "Reason"},
        title="Return Value By Reason",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(prepare_chart(fig), use_container_width=True)

with right:
    category = metrics["category_returns"].head(12).copy()
    fig = px.bar(
        category.sort_values("return_value_pct"),
        x="return_value_pct",
        y="category_name",
        orientation="h",
        color="unit_return_rate_pct",
        color_continuous_scale="Reds",
        labels={
            "category_name": "Category",
            "return_value_pct": "Return Value %",
            "unit_return_rate_pct": "Unit Return Rate %",
        },
        title="Return Rate And Value By Category",
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(yaxis_title=None)
    st.plotly_chart(prepare_chart(fig, 440), use_container_width=True)

st.subheader("Monthly Return Value")
monthly = returns.groupby("year_month", as_index=False).agg(return_amount=("return_amount", "sum"), returns=("return_id", "count"))
fig = go.Figure()
fig.add_bar(x=monthly["year_month"], y=monthly["return_amount"], name="Return Value", marker_color=PALETTE["red"])
fig.add_scatter(x=monthly["year_month"], y=monthly["returns"], name="Return Count", yaxis="y2", mode="lines+markers", line=dict(color=PALETTE["navy"], width=3))
fig.update_layout(yaxis=dict(title="Return Value ($)"), yaxis2=dict(title="Count", overlaying="y", side="right"))
st.plotly_chart(prepare_chart(fig, 380), use_container_width=True)
