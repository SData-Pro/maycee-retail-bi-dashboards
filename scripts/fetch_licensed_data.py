from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import boto3
from botocore.config import Config


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.config import LicensedS3Config, licensed_data_dir


FACT_TABLES = {"transactions", "items", "returns"}
DIMENSION_TABLES = {"customers", "stores", "districts", "regions", "products", "categories"}
OBJECT_RE = re.compile(r"^dt=(\d{4}-\d{2}-\d{2})/([a-z_]+)\.parquet$")


@dataclass(frozen=True)
class LicensedObject:
    key: str
    relative_path: Path
    table: str
    partition_date: date
    size: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the licensed Maycee tables required by the SData BI dashboard."
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List and validate entitled objects without downloading them.",
    )
    return parser.parse_args()


def make_client(config: LicensedS3Config):
    return boto3.client(
        "s3",
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name=config.region,
        config=Config(retries={"max_attempts": 8, "mode": "standard"}),
    )


def list_required_objects(client, config: LicensedS3Config) -> list[LicensedObject]:
    snapshot_end = date.fromisoformat(config.snapshot_through + "-01")
    selected: list[LicensedObject] = []
    latest_dimensions: dict[str, LicensedObject] = {}

    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=config.bucket, Prefix=config.prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            relative = key.removeprefix(config.prefix)
            match = OBJECT_RE.fullmatch(relative)
            if not match:
                continue
            partition_date = date.fromisoformat(match.group(1))
            if (partition_date.year, partition_date.month) > (snapshot_end.year, snapshot_end.month):
                continue
            table = match.group(2)
            obj = LicensedObject(
                key=key,
                relative_path=Path(relative),
                table=table,
                partition_date=partition_date,
                size=int(item["Size"]),
            )
            if table in FACT_TABLES:
                selected.append(obj)
            elif table in DIMENSION_TABLES:
                current = latest_dimensions.get(table)
                if current is None or obj.partition_date > current.partition_date:
                    latest_dimensions[table] = obj

    missing = sorted((FACT_TABLES | DIMENSION_TABLES) - ({obj.table for obj in selected} | set(latest_dimensions)))
    if missing:
        raise RuntimeError("Licensed S3 source is missing required tables: " + ", ".join(missing))

    return sorted(selected + list(latest_dimensions.values()), key=lambda obj: obj.key)


def download_object(client, config: LicensedS3Config, output_dir: Path, obj: LicensedObject, force: bool) -> str:
    destination = output_dir / obj.relative_path
    if not force and destination.is_file() and destination.stat().st_size == obj.size:
        return "cached"

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    client.download_file(config.bucket, obj.key, str(partial))
    partial.replace(destination)
    return "downloaded"


def write_metadata(output_dir: Path, config: LicensedS3Config, objects: list[LicensedObject]) -> None:
    dates = [obj.partition_date for obj in objects]
    metadata = {
        "source": "licensed-s3",
        "snapshot_through": config.snapshot_through,
        "partition_range": {
            "first": min(dates).isoformat(),
            "last": max(dates).isoformat(),
        },
        "object_count": len(objects),
        "tables": sorted({obj.table for obj in objects}),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    started = time.perf_counter()
    args = parse_args()
    if args.workers < 1 or args.workers > 32:
        raise SystemExit("--workers must be between 1 and 32")

    config = LicensedS3Config.from_environment()
    output_dir = (args.output_dir or licensed_data_dir()).resolve()
    client = make_client(config)
    listing_started = time.perf_counter()
    objects = list_required_objects(client, config)
    listing_seconds = time.perf_counter() - listing_started

    fact_count = sum(1 for obj in objects if obj.table in FACT_TABLES)
    print(f"Licensed snapshot: {config.snapshot_through}")
    print(f"Required objects: {len(objects):,} ({fact_count:,} fact partitions, 6 latest dimensions)")
    print(f"Local cache: {output_dir}")
    print(f"S3 listing time: {listing_seconds:.1f} seconds")
    if args.dry_run:
        return 0

    counts = {"downloaded": 0, "cached": 0}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_object, client, config, output_dir, obj, args.force): obj
            for obj in objects
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            counts[future.result()] += 1
            if completed % 500 == 0:
                print(f"Processed {completed:,}/{len(objects):,} objects")

    write_metadata(output_dir, config, objects)
    elapsed = time.perf_counter() - started
    print(f"Downloaded: {counts['downloaded']:,}; already cached: {counts['cached']:,}")
    print(f"Total fetch time: {elapsed:.1f} seconds")
    print("Licensed dashboard cache is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
