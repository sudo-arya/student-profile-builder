from pathlib import Path


class BuilderError(Exception):
    """An expected error suitable for display to an end user."""


def confined_path(root: Path, value: str | Path, label: str) -> Path:
    """Resolve a user-controlled relative path and ensure it stays below root."""
    candidate = (root / value).resolve()
    root = root.resolve()
    if candidate == root or root not in candidate.parents:
        raise BuilderError(f"{label} must be a path inside the project: {value}")
    return candidate
