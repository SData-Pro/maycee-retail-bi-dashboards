from __future__ import annotations

import html
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.data import build_metric_frames, load_dashboard_tables

REPORT_PATH = REPO_ROOT / "reports" / "maycee-retail-dashboard.html"


def render_table(rows: list[dict]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    headers = list(rows[0].keys())
    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(row[header]))}</td>" for header in headers)
            + "</tr>"
        )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def build_report(output_path: Path = REPORT_PATH) -> Path:
    metrics = build_metric_frames(load_dashboard_tables())
    overview = metrics["kpis"].iloc[0].to_dict()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maycee Retail BI Dashboard - Static Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #172033; background: #f7fafc; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1 {{ margin-bottom: 4px; color: #1e3a5f; }}
    h2 {{ margin-top: 34px; color: #047857; }}
    .lede, .small {{ color: #4b5563; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 24px 0; }}
    .metric {{ background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; }}
    .metric strong {{ display: block; font-size: 1.45rem; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9e2ec; font-size: 0.92rem; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e5edf5; text-align: left; }}
    th {{ background: #edf7f3; }}
    .note {{ border-left: 4px solid #047857; padding: 12px 16px; background: #fff; }}
  </style>
</head>
<body>
<main>
  <h1>Maycee Retail BI Dashboard</h1>
  <p class="lede">Static aggregate review report generated from the licensed Maycee Parquet cache.</p>
  <section class="metrics">
    <div class="metric">Transactions<strong>{int(overview["transactions"]):,}</strong></div>
    <div class="metric">Revenue<strong>${overview["revenue"]:,.2f}</strong></div>
    <div class="metric">Average Order Value<strong>${overview["avg_basket"]:,.2f}</strong></div>
    <div class="metric">Gross Margin<strong>{overview["gross_margin_pct"]:.1f}%</strong></div>
    <div class="metric">Return Value Rate<strong>{overview["return_value_pct"]:.2f}%</strong></div>
    <div class="metric">Discount Rate<strong>{overview["discount_rate_pct"]:.2f}%</strong></div>
  </section>
  <p class="note">Licensed aggregate output. Credentials, licence records, and source Parquet files are not embedded in this report.</p>
  <h2>Yearly KPI Comparison</h2>
  {render_table(metrics["yearly_kpis"].to_dict("records"))}
  <h2>Monthly Sales</h2>
  {render_table(metrics["monthly_sales"].to_dict("records"))}
  <h2>Region Performance</h2>
  {render_table(metrics["region_sales"].to_dict("records"))}
  <h2>Top Category Return Rates</h2>
  <p class="small">Sorted by return value percentage, then return amount.</p>
  {render_table(metrics["category_returns"].head(20).to_dict("records"))}
  <h2>Return Reasons</h2>
  {render_table(metrics["returns_summary"].to_dict("records"))}
</main>
</body>
</html>
"""
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    path = build_report()
    print(f"Wrote {path}")
