from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LICENSED_DATA_DIR = REPO_ROOT / "data" / "licensed_v1_0"
DEFAULT_REGION = "ap-southeast-2"
SNAPSHOT_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def load_local_environment() -> Path | None:
    """Load the repository-local .env without overriding process values."""
    candidate = REPO_ROOT / ".env"
    if candidate.is_file():
        load_dotenv(candidate, override=False)
        return candidate
    return None


def licensed_data_dir() -> Path:
    configured = os.getenv("MAYCEE_LICENSED_DATA_DIR")
    return Path(configured).expanduser() if configured else DEFAULT_LICENSED_DATA_DIR


@dataclass(frozen=True)
class LicensedS3Config:
    access_key_id: str
    secret_access_key: str
    region: str
    bucket: str
    prefix: str
    snapshot_through: str

    @classmethod
    def from_environment(cls) -> "LicensedS3Config":
        load_local_environment()
        required = {
            "access_key_id": "MAYCEE_AWS_ACCESS_KEY_ID",
            "secret_access_key": "MAYCEE_AWS_SECRET_ACCESS_KEY",
            "bucket": "MAYCEE_S3_BUCKET",
            "prefix": "MAYCEE_S3_PREFIX",
            "snapshot_through": "MAYCEE_SNAPSHOT_THROUGH",
        }
        values: dict[str, str] = {}
        missing: list[str] = []
        for field, variable in required.items():
            value = os.getenv(variable, "").strip()
            if value:
                values[field] = value
            else:
                missing.append(variable)
        if missing:
            raise RuntimeError(
                "Licensed Maycee configuration is incomplete. Missing: "
                + ", ".join(sorted(missing))
            )

        snapshot = values["snapshot_through"]
        if not SNAPSHOT_RE.fullmatch(snapshot):
            raise RuntimeError("MAYCEE_SNAPSHOT_THROUGH must use YYYY-MM format.")

        return cls(
            access_key_id=values["access_key_id"],
            secret_access_key=values["secret_access_key"],
            region=os.getenv("MAYCEE_AWS_DEFAULT_REGION", DEFAULT_REGION).strip() or DEFAULT_REGION,
            bucket=values["bucket"],
            prefix=values["prefix"].strip("/") + "/",
            snapshot_through=snapshot,
        )
