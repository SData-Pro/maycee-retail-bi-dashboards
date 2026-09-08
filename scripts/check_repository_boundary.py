from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "data",
    "reports",
}
TEXT_SUFFIXES = {".csv", ".env", ".example", ".gitignore", ".md", ".py", ".txt", ".toml", ""}
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(
        r"(?im)^(?:MAYCEE_)?AWS_SECRET_ACCESS_KEY\s*=\s*"
        r"(?!<issued-secret-access-key>)[A-Za-z0-9/+=]{20,}\s*$"
    ),
    re.compile(r"(?im)^(?:PASSWORD|TOKEN)\s*=\s*[^\s#<]{16,}\s*$"),
]
BLOCKED_TRACKED_PATHS = {
    ".env",
    ".streamlit/secrets.toml",
}
BLOCKED_TRACKED_PREFIXES = (
    "data/licensed_v1_0/",
    "data/downloaded/",
)


def iter_text_files(root: Path = REPO_ROOT) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        normalised = relative.as_posix()
        if normalised in BLOCKED_TRACKED_PATHS:
            continue
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            paths.append(path)
    return paths


def check_for_secrets(root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(root)}: possible credential matched {pattern.pattern}")
    return errors


def tracked_paths(root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def check_tracked_boundaries(root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for path in tracked_paths(root):
        if path in BLOCKED_TRACKED_PATHS or path.startswith(BLOCKED_TRACKED_PREFIXES):
            errors.append(f"{path}: credentials or licensed data must not be tracked")
    return errors


def run_checks(root: Path = REPO_ROOT) -> list[str]:
    return check_for_secrets(root) + check_tracked_boundaries(root)


if __name__ == "__main__":
    failures = run_checks()
    if failures:
        print("Repository boundary check failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("Repository boundary check passed.")
