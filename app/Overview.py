from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import available_years, build_metric_frames, date_range_label, filter_options, filter_tables
from runtime import load_cached_dashboard_tables
from ui import (
    PALETTE,
    base_layout,
    benchmark_controls,
    bounded_progress,
    business_filters,
    delta_pct,
    delta_points,
    filter_caption,
    money,
    pct,
    prepare_chart,
    ranked_share_chart,
    year_selection_label,
)


MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def latest_year_delta(yearly, column: str) -> str | None:
    if len(yearly) < 2:
        return None
    latest = yearly.iloc[-1]
    previous = yearly.iloc[-2]
    return delta_pct(float(latest[column]), float(previous[column]))


def latest_year_point_delta(yearly, column: str, digits: int = 1) -> str | None:
    if len(yearly) < 2:
        return None
    latest = yearly.iloc[-1]
    previous = yearly.iloc[-2]
    return delta_points(float(latest[column]), float(previous[column]), digits)


tables = load_cached_dashboard_tables()
selected_years = base_layout(
    "Maycee Retail BI Dashboard",
    "Licensed Maycee analytics across sales, margin, stores, products, and returns.",
    available_years(tables),
    date_range_label(tables),
)
filters = business_filters(filter_options(tables))
benchmarks = benchmark_controls()

filtered_tables = filter_tables(tables, years=selected_years, **filters)
metrics = build_metric_frames(filtered_tables)
if metrics["monthly_sales"].empty:
    st.warning("No licensed rows match the selected filters.")
    st.stop()

kpis = metrics["kpis"].iloc[0]
st.info(
    f"Showing {year_selection_label(selected_years)} from the licensed dataset. "
    f"Available coverage: {date_range_label(tables)}. {filter_caption(filters)}"
)
yearly = metrics["yearly_kpis"]

top_cols = st.columns(3)
top_cols[0].metric("Revenue", money(kpis["revenue"]), delta=latest_year_delta(yearly, "revenue"))
top_cols[1].metric("Transactions", f"{int(kpis['transactions']):,}", delta=latest_year_delta(yearly, "transactions"))
top_cols[2].metric("Average Order Value", f"${kpis['avg_basket']:,.2f}", delta=latest_year_delta(yearly, "avg_basket"))
bottom_cols = st.columns(3)
bottom_cols[0].metric(
    "Gross Margin",
    pct(kpis["gross_margin_pct"]),
    delta=latest_year_point_delta(yearly, "gross_margin_pct"),
)
bottom_cols[1].metric(
    "Return Value Rate",
    pct(kpis["return_value_pct"], 2),
    delta=latest_year_point_delta(yearly, "return_value_pct", 2),
)
bottom_cols[2].metric(
    "Discount Rate",
    pct(kpis["discount_rate_pct"], 2),
    delta=latest_year_point_delta(yearly, "discount_rate_pct", 2),
)

latest_year = int(yearly["year"].max())
latest_year_revenue = float(yearly.loc[yearly["year"] == latest_year, "revenue"].iloc[0])
target_cols = st.columns(3)
target_cols[0].progress(
    bounded_progress(latest_year_revenue, benchmarks["annual_revenue_target"]),
    text=f"{latest_year} revenue pacing: {money(latest_year_revenue)} / {money(benchmarks['annual_revenue_target'])}",
)
target_cols[1].progress(
    bounded_progress(float(kpis["gross_margin_pct"]), benchmarks["gross_margin_floor_pct"]),
    text=f"Gross margin floor: {pct(kpis['gross_margin_pct'])} / {pct(benchmarks['gross_margin_floor_pct'])}",
)
target_cols[2].progress(
    bounded_progress(float(kpis["return_value_pct"]), benchmarks["return_value_ceiling_pct"]),
    text=f"Return value ceiling: {pct(kpis['return_value_pct'], 2)} / {pct(benchmarks['return_value_ceiling_pct'], 1)}",
)

st.divider()

left, right = st.columns([1.35, 1])

with left:
    monthly = metrics["monthly_sales"].copy()
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
    st.plotly_chart(prepare_chart(fig, 420), use_container_width=True)

with right:
    region = metrics["region_sales"].sort_values("revenue", ascending=True)
    fig = px.bar(
        region,
        x="revenue",
        y="region",
        orientation="h",
        color="revenue",
        color_continuous_scale="Blues",
        labels={"revenue": "Revenue ($)", "region": "Region"},
        title="Revenue By Region",
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(prepare_chart(fig, 420), use_container_width=True)

left2, right2 = st.columns(2)

with left2:
    category = metrics["category_sales"].sort_values("revenue", ascending=False).copy()
    category_plot = category.head(8).copy()
    if len(category) > len(category_plot):
        other_category_count = len(category) - len(category_plot)
        other_revenue = category["revenue"].iloc[len(category_plot) :].sum()
        other_gross_profit = category["gross_profit"].iloc[len(category_plot) :].sum()
        other_discount = category["discount_value"].iloc[len(category_plot) :].sum()
        category_plot.loc[len(category_plot)] = {
            "category_name": f"Other ({other_category_count} categories)",
            "revenue": other_revenue,
            "gross_profit": other_gross_profit,
            "discount_value": other_discount,
            "units_sold": category["units_sold"].iloc[len(category_plot) :].sum(),
            "gross_margin_pct": other_gross_profit / other_revenue * 100 if other_revenue else 0,
            "discount_rate_pct": other_discount / other_revenue * 100 if other_revenue else 0,
        }
    fig = ranked_share_chart(
        category_plot["category_name"],
        category_plot["revenue"],
        "Category Mix",
        height=390,
    )
    st.plotly_chart(fig, use_container_width=True)

with right2:
    product = metrics["product_leaders"].head(6).sort_values("revenue")
    fig = px.bar(
        product,
        x="revenue",
        y="product_name",
        orientation="h",
        color="gross_margin_pct",
        color_continuous_scale="Tealgrn",
        labels={"revenue": "Revenue ($)", "product_name": "Product", "gross_margin_pct": "Margin %"},
        title="Product Leaders",
    )
    st.plotly_chart(prepare_chart(fig, 390), use_container_width=True)
