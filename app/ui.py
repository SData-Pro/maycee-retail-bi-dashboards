from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

PALETTE = {
    "blue": "#2a6cb5",
    "navy": "#1e3a5f",
    "emerald": "#047857",
    "teal": "#0f766e",
    "amber": "#d97706",
    "red": "#b91c1c",
    "grey": "#64748b",
}


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def compact_number(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"


def delta_pct(current: float, previous: float | None, digits: int = 1) -> str | None:
    if previous in (None, 0):
        return None
    return f"{((current - previous) / previous * 100):+.{digits}f}%"


def delta_points(current: float, previous: float | None, digits: int = 1) -> str | None:
    if previous is None:
        return None
    return f"{(current - previous):+.{digits}f} pp"


def bounded_progress(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def ranked_share_chart(
    labels,
    values,
    title: str,
    height: int = 360,
) -> go.Figure:
    """Build a readable categorical-share chart without a separate legend."""
    ranked = sorted(
        ((str(label), float(value)) for label, value in zip(labels, values)),
        key=lambda item: item[1],
    )
    total = sum(value for _, value in ranked)
    shares = [(value / total * 100) if total else 0.0 for _, value in ranked]
    amounts = [value for _, value in ranked]

    fig = go.Figure(
        go.Bar(
            x=shares,
            y=[label for label, _ in ranked],
            orientation="h",
            customdata=amounts,
            marker=dict(
                color=shares,
                colorscale=[[0, "#9dd8cf"], [1, PALETTE["blue"]]],
                showscale=False,
            ),
            text=[f"{share:.1f}%" for share in shares],
            textposition="outside",
            hovertemplate=(
                "%{y}<br>Revenue share: %{x:.1f}%"
                "<br>Revenue: $%{customdata:,.0f}<extra></extra>"
            ),
        )
    )
    upper_bound = max(shares, default=0.0) * 1.2
    fig.update_layout(
        showlegend=False,
        title=title,
        xaxis=dict(title="Revenue share", ticksuffix="%", range=[0, upper_bound]),
        yaxis=dict(title=None),
    )
    return prepare_chart(fig, height)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1240px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 8px 18px rgba(30, 58, 95, 0.06);
        }
        div[data-testid="stMetricLabel"] {
            color: #475569;
        }
        div[data-testid="stMetricValue"] {
            color: #172033;
        }
        section[data-testid="stSidebar"] {
            background: #f8fafc;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
            gap: 0.2rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            border-left: 3px solid transparent;
            border-radius: 4px;
            padding: 0.55rem 0.75rem;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: #e7f4ef;
            border-left-color: #047857;
            color: #172033;
            font-weight: 650;
        }
        section[data-testid="stSidebar"] hr {
            margin: 1rem 0;
        }
        .sdata-source {
            border-top: 1px solid #d9e2ec;
            margin-top: 0.75rem;
            padding-top: 0.9rem;
            color: #475569;
            font-size: 0.82rem;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def source_note(coverage: str) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sdata-source">
        <strong>Licensed Maycee Retail</strong><br>
        Entitled coverage loaded: {coverage}<br>
        Credentials remain server-side.
        </div>
        """,
        unsafe_allow_html=True,
    )


def base_layout(title: str, caption: str, years: list[int], coverage: str) -> list[int]:
    st.set_page_config(page_title=title, page_icon="", layout="wide")
    apply_theme()
    page_header(title, caption)
    st.sidebar.markdown("### Analysis scope")
    start_year, end_year = st.sidebar.select_slider(
        "Year range",
        options=years,
        value=(years[0], years[-1]),
    )
    selected = [year for year in years if start_year <= year <= end_year]
    source_note(coverage)
    return selected


def business_filters(options: dict[str, list[str]]) -> dict[str, list[str]]:
    with st.sidebar.expander("Business filters", expanded=True):
        return {
            "regions": st.multiselect("Regions", options["regions"], default=[]),
            "categories": st.multiselect("Categories", options["categories"], default=[]),
            "store_types": st.multiselect("Store types", options["store_types"], default=[]),
            "payment_methods": st.multiselect("Payment methods", options["payment_methods"], default=[]),
        }


def benchmark_controls() -> dict[str, float]:
    with st.sidebar.expander("Benchmarks", expanded=False):
        return {
            "annual_revenue_target": float(
                st.number_input(
                "Annual revenue target",
                min_value=1_000_000,
                max_value=200_000_000,
                value=40_000_000,
                step=1_000_000,
                )
            ),
            "gross_margin_floor_pct": float(
                st.slider("Gross margin floor", min_value=1, max_value=80, value=55, step=1)
            ),
            "return_value_ceiling_pct": float(
                st.slider("Return value ceiling", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
            ),
        }


def filter_caption(filters: dict[str, list[str]]) -> str:
    active = sum(1 for values in filters.values() if values)
    if not active:
        return "Business filters: all regions, categories, store types, and payment methods."
    parts = []
    for label, key in [
        ("regions", "regions"),
        ("categories", "categories"),
        ("store types", "store_types"),
        ("payment methods", "payment_methods"),
    ]:
        values = filters[key]
        if values:
            parts.append(f"{label}: {', '.join(values[:4])}{'...' if len(values) > 4 else ''}")
    return "Business filters: " + "; ".join(parts) + "."


def year_selection_label(years: list[int]) -> str:
    if len(years) > 1 and years == list(range(years[0], years[-1] + 1)):
        return f"{years[0]} to {years[-1]}"
    return ", ".join(str(year) for year in years)


def prepare_chart(fig: go.Figure, height: int = 360) -> go.Figure:
    title_text = fig.layout.title.text if fig.layout.title else None
    top_margin = 116 if title_text else 64
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_layout(
        height=height,
        margin=dict(t=top_margin, r=20, b=48, l=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(color="#172033"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title_text or "", y=0.98, x=0, xanchor="left", font=dict(size=16)),
    )
    return fig
