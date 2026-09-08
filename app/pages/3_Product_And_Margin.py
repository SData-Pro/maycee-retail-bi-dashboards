from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import available_years, build_metric_frames, date_range_label, filter_options, filter_tables
from runtime import load_cached_dashboard_tables
from ui import PALETTE, base_layout, business_filters, filter_caption, prepare_chart, year_selection_label


tables = load_cached_dashboard_tables()
selected_years = base_layout(
    "Product And Margin",
    "Category contribution, product leaders, and promotion impact across the licensed dataset.",
    available_years(tables),
    date_range_label(tables),
)
filters = business_filters(filter_options(tables))

metrics = build_metric_frames(filter_tables(tables, years=selected_years, **filters))
if metrics["category_sales"].empty:
    st.warning("No licensed rows match the selected filters.")
    st.stop()

st.info(
    f"Showing {year_selection_label(selected_years)}. "
    f"Available coverage: {date_range_label(tables)}. {filter_caption(filters)}"
)

left, right = st.columns(2)
with left:
    category = metrics["category_sales"].head(12).sort_values("revenue").copy()
    fig = px.bar(
        category,
        x="revenue",
        y="category_name",
        orientation="h",
        color_discrete_sequence=[PALETTE["blue"]],
        labels={"category_name": "Category", "revenue": "Revenue ($)"},
        title="Revenue By Category",
    )
    fig.update_layout(yaxis_title=None)
    st.plotly_chart(prepare_chart(fig, 440), use_container_width=True)

with right:
    fig = px.bar(
        category,
        x="gross_margin_pct",
        y="category_name",
        orientation="h",
        color="gross_margin_pct",
        color_continuous_scale="Tealgrn",
        labels={"category_name": "Category", "gross_margin_pct": "Gross Margin %"},
        title="Gross Margin By Category",
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(yaxis_title=None)
    st.plotly_chart(prepare_chart(fig, 440), use_container_width=True)

st.subheader("Product Leaders")
products = metrics["product_leaders"].copy()
top_products = products.head(20)
fig = px.bar(
    top_products.sort_values("revenue"),
    x="revenue",
    y="product_name",
    orientation="h",
    color="gross_margin_pct",
    color_continuous_scale="Tealgrn",
    labels={
        "revenue": "Revenue ($)",
        "product_name": "Product",
        "gross_margin_pct": "Margin %",
        "category_name": "Category",
        "units": "Units",
        "gross_profit": "Gross Profit ($)",
    },
    hover_data=["category_name", "units", "gross_profit"],
)
st.plotly_chart(prepare_chart(fig, 430), use_container_width=True)

st.subheader("Promotion Impact")
promo = metrics["promotion_impact"].copy()
promo_long = promo.melt(
    id_vars="pricing_mode",
    value_vars=["revenue", "gross_profit"],
    var_name="metric",
    value_name="amount",
)
promo_long["metric"] = promo_long["metric"].map(
    {"revenue": "Revenue", "gross_profit": "Gross Profit"}
)
fig = px.bar(
    promo_long,
    x="pricing_mode",
    y="amount",
    color="metric",
    barmode="group",
    color_discrete_map={"Revenue": PALETTE["blue"], "Gross Profit": PALETTE["emerald"]},
    category_orders={"metric": ["Revenue", "Gross Profit"]},
    labels={"pricing_mode": "Pricing Mode", "amount": "Amount ($)", "metric": "Metric"},
)
fig = prepare_chart(fig, 360)
fig.update_layout(legend_title_text="")
st.plotly_chart(fig, use_container_width=True)
product_display = products.head(50).rename(
    columns={
        "product_name": "Product",
        "category_name": "Category",
        "units": "Units",
        "revenue": "Revenue ($)",
        "gross_profit": "Gross Profit ($)",
        "gross_margin_pct": "Gross Margin (%)",
    }
)
st.dataframe(product_display, use_container_width=True, hide_index=True)
