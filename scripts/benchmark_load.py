from __future__ import annotations

import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.data import available_years, date_range_label, load_dashboard_tables


def main() -> int:
    started = time.perf_counter()
    tables = load_dashboard_tables()
    elapsed = time.perf_counter() - started

    print(f"duckdb_load_seconds={elapsed:.3f}")
    print(f"coverage={date_range_label(tables)}")
    print(f"years={available_years(tables)}")
    for table in ("transactions", "items", "returns"):
        print(f"{table}={len(tables[table])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
