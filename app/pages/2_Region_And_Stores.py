from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import available_years, build_metric_frames, date_range_label, enriched_transactions, filter_options, filter_tables
from runtime import load_cached_dashboard_tables
from ui import PALETTE, base_layout, business_filters, filter_caption, prepare_chart, ranked_share_chart, year_selection_label


tables = load_cached_dashboard_tables()
selected_years = base_layout(
    "Region And Stores",
    "Regional contribution, store footprint, and monthly sales movement across the licensed dataset.",
    available_years(tables),
    date_range_label(tables),
)
filters = business_filters(filter_options(tables))

filtered_tables = filter_tables(tables, years=selected_years, **filters)
metrics = build_metric_frames(filtered_tables)
txns = enriched_transactions(filtered_tables)
if txns.empty:
    st.warning("No licensed rows match the selected filters.")
    st.stop()

st.info(
    f"Showing {year_selection_label(selected_years)}. "
    f"Available coverage: {date_range_label(tables)}. {filter_caption(filters)}"
)

left, right = st.columns(2)
with left:
    region = metrics["region_sales"].sort_values("revenue")
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
    st.plotly_chart(prepare_chart(fig), use_container_width=True)

with right:
    store_type = (
        txns.groupby("store_type", as_index=False)
        .agg(revenue=("total_amount", "sum"), transactions=("transaction_id", "count"))
        .sort_values("revenue", ascending=False)
    )
    fig = ranked_share_chart(
        store_type["store_type"],
        store_type["revenue"],
        "Store Type Mix",
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly Revenue By Region")
heat = (
    txns.groupby(["region", "year_month"], as_index=False)["total_amount"].sum()
    .pivot(index="region", columns="year_month", values="total_amount")
    .fillna(0)
)
fig = px.imshow(
    heat,
    text_auto=".3s",
    color_continuous_scale="Blues",
    labels={"color": "Revenue ($)", "x": "Month", "y": "Region"},
    aspect="auto",
)
fig.update_layout(xaxis_tickangle=-45)
st.plotly_chart(prepare_chart(fig, 420), use_container_width=True)

st.subheader("Store Leaderboard")
stores = (
    txns.groupby(["store_name", "city", "region", "store_type"], as_index=False)
    .agg(
        revenue=("total_amount", "sum"),
        transactions=("transaction_id", "count"),
        avg_basket=("total_amount", "mean"),
    )
    .sort_values("revenue", ascending=False)
)
stores["revenue"] = stores["revenue"].round(2)
stores["avg_basket"] = stores["avg_basket"].round(2)
store_display = stores.rename(
    columns={
        "store_name": "Store",
        "city": "City",
        "region": "Region",
        "store_type": "Store Type",
        "revenue": "Revenue ($)",
        "transactions": "Transactions",
        "avg_basket": "Average Order Value ($)",
    }
)
st.dataframe(store_display, use_container_width=True, hide_index=True)
