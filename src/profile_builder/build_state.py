"""Non-sensitive local build freshness metadata."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

STATE_FILE = ".profile-builder-state.json"


def input_fingerprint(root: Path, template_id: str) -> str:
    digest = sha256()
    paths = [root / "profile.md", root / "config.yml"]
    for directory in (root / "templates" / template_id, root / "assets"):
        if directory.is_dir(): paths.extend(path for path in directory.rglob("*") if path.is_file() and not path.is_symlink())
    for path in sorted(paths, key=lambda p: p.as_posix()):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def record_build(root: Path, template_id: str) -> None:
    data = {"version": "1.0", "fingerprint": input_fingerprint(root, template_id),
            "template": template_id, "built_at": datetime.now(timezone.utc).isoformat()}
    (root / STATE_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_status(root: Path, template_id: str, output: Path) -> tuple[bool, str | None]:
    try: data = json.loads((root / STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return False, None
    current = output.joinpath("index.html").is_file() and data.get("template") == template_id and data.get("fingerprint") == input_fingerprint(root, template_id)
    return current, data.get("built_at")
