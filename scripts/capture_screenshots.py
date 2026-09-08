from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "reports" / "screenshots"
EDGE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PAGES = [
    ("", "Maycee Retail BI Dashboard", "overview"),
    ("Sales_Overview", "Sales Overview", "sales-overview"),
    ("Region_And_Stores", "Region And Stores", "region-and-stores"),
    ("Product_And_Margin", "Product And Margin", "product-and-margin"),
    ("Returns", "Returns", "returns"),
]

AUDIT_CHARTS = {
    "": "Category Mix",
    "Product_And_Margin": "Revenue By Category",
    "Returns": "Return Rate And Value By Category",
}

AUDIT_HEADINGS = {
    "Product_And_Margin": ["Promotion Impact"],
    "Returns": ["Monthly Return Value"],
}

SCREENSHOT_CSS = """
header[data-testid="stHeader"],
[data-testid="stStatusWidget"],
#MainMenu {
    display: none !important;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture local Maycee BI dashboard pages for review.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--viewport-width", type=int, default=1440)
    parser.add_argument("--viewport-height", type=int, default=1000)
    parser.add_argument(
        "--page",
        action="append",
        choices=[filename for _, _, filename in PAGES],
        help="Capture only the named page; repeat to select multiple pages.",
    )
    parser.add_argument(
        "--audit-charts",
        action="store_true",
        help="Also capture focused views of dense category charts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(EDGE_PATH),
            headless=True,
        )
        page = browser.new_page(
            viewport={"width": args.viewport_width, "height": args.viewport_height},
            device_scale_factor=1,
        )
        selected_pages = [page_info for page_info in PAGES if not args.page or page_info[2] in args.page]
        for route, heading, filename in selected_pages:
            url = args.base_url.rstrip("/") + (f"/{route}" if route else "/")
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=180_000)
            page.locator(".js-plotly-plot").first.wait_for(state="visible", timeout=60_000)
            if args.viewport_width < 900:
                collapse_button = page.locator('[data-testid="stSidebarCollapseButton"]').first
                if collapse_button.count():
                    collapse_button.evaluate(
                        "element => (element.querySelector('button') || element).click()"
                    )
                    page.wait_for_timeout(300)
            page.add_style_tag(content=SCREENSHOT_CSS)
            page.wait_for_timeout(1_500)
            output = args.output_dir / f"{filename}.png"
            page.screenshot(path=str(output), full_page=True)
            print(f"Captured {filename}.png")
            if args.audit_charts and route in AUDIT_CHARTS:
                chart_title = page.locator(".gtitle").filter(has_text=AUDIT_CHARTS[route]).first
                chart_title.wait_for(state="visible", timeout=60_000)
                chart_title.evaluate("element => element.scrollIntoView({block: 'center'})")
                page.wait_for_timeout(500)
                audit_output = args.output_dir / f"audit-{filename}.png"
                page.screenshot(path=str(audit_output))
                print(f"Captured audit-{filename}.png")
            if args.audit_charts and route in AUDIT_HEADINGS:
                for audit_heading in AUDIT_HEADINGS[route]:
                    heading_locator = page.get_by_role("heading", name=audit_heading, exact=True)
                    heading_locator.wait_for(state="visible", timeout=60_000)
                    heading_locator.evaluate("element => element.scrollIntoView({block: 'start'})")
                    page.wait_for_timeout(500)
                    audit_slug = audit_heading.lower().replace(" ", "-")
                    audit_output = args.output_dir / f"audit-{audit_slug}.png"
                    page.screenshot(path=str(audit_output))
                    print(f"Captured audit-{audit_slug}.png")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
