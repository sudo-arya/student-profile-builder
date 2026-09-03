"""Git-safe working-profile and starter-profile services."""
from __future__ import annotations

from pathlib import Path
import os
import re
import shutil
import tempfile
import yaml

from .profile import parse_profile
from .utils import BuilderError, confined_path

DEFAULT_PROFILE = Path("defaults/profile.default.md")
WORKING_PROFILE = Path("profile.md")


def normalize_raw_profile(root: Path, text: str, *, theme_switching: bool = True) -> tuple[str, tuple[str, ...]]:
    """Normalize recoverable incompatibilities in a user-supplied raw profile.

    Unsafe/out-of-project paths are deliberately left unchanged for normal validation to reject.
    """
    match=re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|\Z)(.*)\Z",text,re.S)
    if not match: return text,()
    try: data=yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError: return text,()
    if not isinstance(data,dict): return text,()
    warnings=[]; changed=False; assets=(root/"assets").resolve()
    for field,label in (("photo","Profile image"),("cv","CV"),("icon","Website icon")):
        value=data.get(field)
        if not isinstance(value,str) or not value: continue
        try: candidate=confined_path(root,value,label)
        except BuilderError: continue
        if assets not in candidate.parents or candidate.is_file(): continue
        if field=="photo" and (root/"assets/profile-placeholder.svg").is_file():
            data[field]="assets/profile-placeholder.svg"
            warnings.append(f'{label} "{value}" was not found; the standard placeholder is being used.')
        else:
            data[field]=""
            warnings.append(f'{label} "{value}" was not found; that optional field was cleared.')
        changed=True
    theme=data.get("theme")
    if not theme_switching and isinstance(theme,dict) and theme.get("enabled"):
        theme["enabled"]=False
        warnings.append("Visitor theme switching was disabled because the selected template does not support it; the default appearance was preserved.")
        changed=True
    if not changed: return text,()
    newline="\r\n" if "\r\n" in text else "\n"
    header=yaml.safe_dump(data,sort_keys=False,allow_unicode=True,width=1000).replace("\n",newline)
    normalized=f"---{newline}{header}---{match.group(2)}{match.group(3)}"
    return normalized,tuple(warnings)


def default_profile_path(root: Path) -> Path:
    return root / DEFAULT_PROFILE


def working_profile_path(root: Path) -> Path:
    return root / WORKING_PROFILE


def ensure_working_profile(root: Path) -> Path:
    """Create the ignored working copy once; existing user data always wins."""
    working = working_profile_path(root)
    if working.exists():
        return working
    source = default_profile_path(root)
    if not source.is_file():
        raise BuilderError(f"Canonical default profile not found: {source}")
    parse_profile(source, root)
    shutil.copyfile(source, working)
    return working


def _atomic_replace_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try: Path(temporary).unlink()
        except FileNotFoundError: pass


def validate_profile_text(root: Path, text: str, *, directory: Path | None = None) -> Path:
    """Write a runtime candidate and validate it with the normal parser."""
    candidate_dir = directory or root / ".runtime" / "profile-candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate = candidate_dir / "profile.md"
    _atomic_replace_text(candidate, text)
    parse_profile(candidate, root)
    return candidate


def save_profile_text(root: Path, text: str) -> Path:
    """Validate, back up once, and atomically commit raw Markdown."""
    candidate = validate_profile_text(root, text)
    working = ensure_working_profile(root)
    backup = root / "profile.md.bak"
    if working.exists() and not backup.exists():
        shutil.copyfile(working, backup)
    _atomic_replace_text(working, candidate.read_text(encoding="utf-8"))
    return working


def restore_default_profile(root: Path) -> Path:
    """Restore the tracked starter while keeping one bounded current backup."""
    source = default_profile_path(root)
    parse_profile(source, root)
    working = ensure_working_profile(root)
    backup = root / "profile.md.bak"
    if working.exists():
        shutil.copyfile(working, backup)
    _atomic_replace_text(working, source.read_text(encoding="utf-8"))
    parse_profile(working, root)
    return working


def git_safety_status(root: Path) -> dict[str, bool]:
    """Report the required safety policy without requiring a Git executable."""
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    lines = {line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    return {
        "working_profile": "/profile.md" in lines or "profile.md" in lines,
        "user_assets": "/assets/managed/" in lines,
        "runtime": ".runtime/" in lines or "/.runtime/" in lines,
        "local_templates": "/local-templates/" in lines,
        "templates_contributable": "/templates/" not in lines and "templates/" not in lines,
        "default_tracked": "/defaults/" not in lines and "defaults/" not in lines,
    }
