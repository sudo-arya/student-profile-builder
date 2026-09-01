from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
import json
import re

from ..utils import BuilderError

MANIFEST_NAME = ".profile-builder-manifest.json"
MANIFEST_VERSION = "1.0"
DRIVE_PATH = re.compile(r"^[A-Za-z]:")


def validate_managed_path(value: Any) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise BuilderError("Remote manifest contains an empty or invalid managed path.")
    if "\\" in value or value.startswith(("/", "~")) or DRIVE_PATH.match(value):
        raise BuilderError(f"Unsafe path in remote manifest: {value}")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts) or path.is_absolute():
        raise BuilderError(f"Unsafe path in remote manifest: {value}")
    normalized = path.as_posix()
    if normalized == MANIFEST_NAME: raise BuilderError("The ownership manifest cannot manage itself.")
    return normalized


def collect_files(output: Path) -> tuple[list[str], int]:
    root = output.resolve(); files: list[str] = []; total = 0
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            resolved = path.resolve()
            if resolved != root and root not in resolved.parents:
                raise BuilderError(f"Generated output contains a symbolic link outside the build directory: {path}")
            raise BuilderError(f"Generated output contains an unsupported symbolic link: {path}")
        if path.is_file():
            relative = validate_managed_path(path.relative_to(output).as_posix())
            files.append(relative); total += path.stat().st_size
    return sorted(files), total


def create_manifest(output: Path, target: IITDTarget) -> dict[str, Any]:
    files, _ = collect_files(output)
    return {"manifest_version": MANIFEST_VERSION, "generator": "Student Profile Builder",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "deployment_target": target.value, "files": files}


def parse_manifest(text: str) -> dict[str, Any] | None:
    if not text.strip(): return None
    try: raw = json.loads(text)
    except json.JSONDecodeError as exc: raise BuilderError("The remote ownership manifest is not valid JSON; no cleanup will be attempted.") from exc
    if not isinstance(raw, dict) or raw.get("manifest_version") != MANIFEST_VERSION or not isinstance(raw.get("files"), list):
        raise BuilderError("The remote ownership manifest has an unsupported format; no cleanup will be attempted.")
    raw["files"] = sorted(validate_managed_path(value) for value in raw["files"])
    return raw


def stale_files(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if previous is None: return []
    old = {validate_managed_path(value) for value in previous["files"]}
    new = {validate_managed_path(value) for value in current["files"]}
    return sorted(old - new)
