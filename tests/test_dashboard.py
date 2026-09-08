from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb
import pandas as pd
import plotly.graph_objects as go


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.config import LicensedS3Config
from app.data import available_years, build_metric_frames, filter_tables, load_dashboard_tables
from app.ui import prepare_chart, ranked_share_chart
from scripts.check_repository_boundary import run_checks
from scripts.fetch_licensed_data import list_required_objects


def write_test_fixture(root: Path) -> None:
    """Create a minimal relational Parquet fixture without shipping dataset rows."""
    partition = root / "dt=2026-01-01"
    partition.mkdir(parents=True)
    frames = {
        "regions": pd.DataFrame(
            [("r-vic", "VIC"), ("r-nsw", "NSW")],
            columns=["region_id", "name"],
        ),
        "districts": pd.DataFrame(
            [("d-vic", "r-vic", "Melbourne"), ("d-nsw", "r-nsw", "Sydney")],
            columns=["district_id", "region_id", "name"],
        ),
        "stores": pd.DataFrame(
            [
                ("s-vic", "d-vic", "Melbourne Central", "Melbourne", "physical", "Australia"),
                ("s-nsw", "d-nsw", "Sydney Central", "Sydney", "online", "Australia"),
            ],
            columns=["store_id", "district_id", "name", "city", "store_type", "country"],
        ),
        "categories": pd.DataFrame(
            [("c-camera", "Cameras"), ("c-pantry", "Pantry")],
            columns=["category_id", "name"],
        ),
        "products": pd.DataFrame(
            [("p-camera", "Demo Camera", "c-camera"), ("p-pantry", "Demo Pantry Item", "c-pantry")],
            columns=["product_id", "name", "category_id"],
        ),
        "customers": pd.DataFrame(
            [("customer-gold", "Gold"), ("customer-guest", "")],
            columns=["customer_id", "loyalty_tier"],
        ),
        "transactions": pd.DataFrame(
            [
                ("t-2017", "customer-guest", "s-nsw", "2017-01-10", "cash", 100.0),
                ("t-2018", "customer-gold", "s-vic", "2018-02-10", "credit_card", 200.0),
                ("t-2019-vic", "customer-gold", "s-vic", "2019-03-10", "digital_wallet", 300.0),
                ("t-2019-nsw", "customer-guest", "s-nsw", "2019-04-10", "cash", 150.0),
            ],
            columns=[
                "transaction_id",
                "customer_id",
                "store_id",
                "transaction_date",
                "payment_method",
                "total_amount",
            ],
        ),
        "items": pd.DataFrame(
            [
                ("i-2017", "t-2017", "p-pantry", 1, 100.0, 40.0, 0.0),
                ("i-2018", "t-2018", "p-camera", 1, 200.0, 100.0, 10.0),
                ("i-2019-vic", "t-2019-vic", "p-camera", 1, 300.0, 150.0, 0.0),
                ("i-2019-nsw", "t-2019-nsw", "p-pantry", 2, 150.0, 50.0, 5.0),
            ],
            columns=[
                "item_id",
                "transaction_id",
                "product_id",
                "quantity",
                "line_total",
                "gross_profit",
                "discount_amount",
            ],
        ),
        "returns": pd.DataFrame(
            [("return-1", "t-2019-vic", "i-2019-vic", "2019-03-15", 30.0, 1, "defective")],
            columns=[
                "return_id",
                "transaction_id",
                "item_id",
                "return_date",
                "refund_amount",
                "quantity_returned",
                "reason_code",
            ],
        ),
    }
    frames["transactions"]["transaction_date"] = pd.to_datetime(
        frames["transactions"]["transaction_date"]
    )
    frames["returns"]["return_date"] = pd.to_datetime(frames["returns"]["return_date"])

    con = duckdb.connect(database=":memory:")
    try:
        for table, frame in frames.items():
            con.register("fixture_frame", frame)
            output = str(partition / f"{table}.parquet").replace("'", "''")
            con.execute(f"copy fixture_frame to '{output}' (format parquet)")
            con.unregister("fixture_frame")
    finally:
        con.close()


class FakePaginator:
    def __init__(self, objects: list[dict]):
        self.objects = objects

    def paginate(self, **kwargs):
        return [{"Contents": self.objects}]


class FakeS3Client:
    def __init__(self, objects: list[dict]):
        self.objects = objects

    def get_paginator(self, name: str):
        if name != "list_objects_v2":
            raise AssertionError(name)
        return FakePaginator(self.objects)


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_temp_dir = tempfile.TemporaryDirectory()
        cls.fixture_dir = Path(cls.fixture_temp_dir.name)
        write_test_fixture(cls.fixture_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_temp_dir.cleanup()

    def test_repository_boundary_checks_pass(self) -> None:
        self.assertEqual(run_checks(REPO_ROOT), [])

    def test_generic_loader_uses_explicit_local_parquet_fixture(self) -> None:
        tables = load_dashboard_tables(self.fixture_dir)
        self.assertEqual(available_years(tables), [2017, 2018, 2019])
        self.assertEqual(len(tables["transactions"]), 4)
        self.assertEqual(len(tables["items"]), 4)
        self.assertEqual(len(tables["returns"]), 1)
        self.assertEqual(tables["source"].iloc[0]["kind"], "licensed")

    def test_dashboard_metrics_include_decision_ratios(self) -> None:
        metrics = build_metric_frames(load_dashboard_tables(self.fixture_dir))
        for column in [
            "gross_margin_pct",
            "return_value_pct",
            "return_count_rate_pct",
            "discount_rate_pct",
        ]:
            self.assertIn(column, metrics["kpis"].columns)
        self.assertIn("yearly_kpis", metrics)
        self.assertIn("category_returns", metrics)
        self.assertGreater(float(metrics["kpis"].iloc[0]["gross_margin_pct"]), 0)

    def test_ranked_share_chart_uses_direct_labels_without_a_legend(self) -> None:
        fig = ranked_share_chart(["Small", "Large"], [20, 80], "Test Mix")

        self.assertFalse(fig.layout.showlegend)
        self.assertEqual(fig.data[0].orientation, "h")
        self.assertEqual(list(fig.data[0].text), ["20.0%", "80.0%"])

    def test_chart_legends_are_anchored_above_the_plot(self) -> None:
        fig = go.Figure()
        fig.add_bar(name="Revenue", x=["Standard"], y=[100])
        fig.add_bar(name="Gross Profit", x=["Standard"], y=[60])

        prepared = prepare_chart(fig)

        self.assertEqual(prepared.layout.legend.yanchor, "bottom")
        self.assertGreater(float(prepared.layout.legend.y), 1.0)

    def test_business_filters_narrow_data(self) -> None:
        tables = load_dashboard_tables(self.fixture_dir)
        filtered = filter_tables(
            tables,
            years=[2019],
            regions=["VIC"],
            categories=["Cameras"],
            store_types=[],
            payment_methods=[],
        )
        self.assertEqual(available_years(filtered), [2019])
        self.assertLess(len(filtered["transactions"]), len(tables["transactions"]))
        self.assertLess(len(filtered["items"]), len(tables["items"]))
        metrics = build_metric_frames(filtered)
        self.assertGreater(int(metrics["kpis"].iloc[0]["transactions"]), 0)

    def test_licensed_fetch_respects_snapshot_and_uses_latest_dimensions(self) -> None:
        prefix = "maycee-retail-dataset/v1.0/premium/data/"
        objects = []
        for day in ["2026-08-31", "2026-09-01", "2026-10-01"]:
            for table in {"transactions", "items", "returns", "customers", "stores", "districts", "regions", "products", "categories"}:
                objects.append({"Key": f"{prefix}dt={day}/{table}.parquet", "Size": 100})
        config = LicensedS3Config(
            access_key_id="test-access",
            secret_access_key="test-secret",
            region="ap-southeast-2",
            bucket="test-bucket",
            prefix=prefix,
            snapshot_through="2026-09",
        )

        selected = list_required_objects(FakeS3Client(objects), config)
        self.assertEqual(sum(obj.table in {"transactions", "items", "returns"} for obj in selected), 6)
        dimensions = [obj for obj in selected if obj.table not in {"transactions", "items", "returns"}]
        self.assertEqual(len(dimensions), 6)
        self.assertTrue(all(obj.partition_date.isoformat() == "2026-09-01" for obj in dimensions))
        self.assertFalse(any(obj.partition_date.isoformat() == "2026-10-01" for obj in selected))

    def test_fetch_dry_run_requires_no_secret_output(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/fetch_licensed_data.py", "--help"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", result.stdout)

    def test_streamlit_pages_run_with_explicit_local_fixture(self) -> None:
        from streamlit.testing.v1 import AppTest

        with patch.dict(os.environ, {"MAYCEE_LICENSED_DATA_DIR": str(self.fixture_dir)}):
            paths = [REPO_ROOT / "app" / "Overview.py", *(sorted((REPO_ROOT / "app" / "pages").glob("*.py")))]
            for page_path in paths:
                with self.subTest(page=page_path.name):
                    app = AppTest.from_file(str(page_path))
                    app.run(timeout=30)
                    self.assertEqual(app.exception, [])


if __name__ == "__main__":
    unittest.main()
