from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import os
import shutil
import tempfile
from urllib.parse import urlparse

import bleach
import markdown
import yaml

from .utils import BuilderError, confined_path

REQUIRED_FIELDS = ("name", "designation", "institute")
SECTION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
THEME_DEFAULTS = {"light", "dark", "system"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {"p", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "hr", "br", "table", "thead", "tbody", "tr", "th", "td", "ul", "ol", "li"}
ALLOWED_ATTRIBUTES = {"a": ["href", "title"], "code": ["class"]}


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    type: str
    visible: bool
    order: int
    markdown: str
    html: str


@dataclass(frozen=True)
class Theme:
    enabled: bool = False
    default: str = "system"


@dataclass(frozen=True)
class Profile:
    data: dict[str, Any]
    markdown: str
    html: str
    sections: tuple[Section, ...] = ()
    theme: Theme = Theme()


def _render(value: str) -> str:
    rendered = markdown.markdown(value, extensions=["extra", "sane_lists"])
    return bleach.clean(rendered, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                        protocols={"http", "https", "mailto"}, strip=True)


def _slug(title: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"
    candidate, number = base, 2
    while candidate in used:
        candidate = f"{base}-{number}"; number += 1
    used.add(candidate); return candidate


def _legacy_sections(body: str) -> list[dict[str, Any]]:
    matches = list(re.finditer(r"(?m)^# (.+?)\s*$", body))
    if not matches:
        return [{"id": "content", "title": "Content", "type": "custom", "visible": True,
                 "order": 10, "content": body.strip()}] if body.strip() else []
    result, used = [], set()
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        content = body[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(body)].strip()
        section_id = _slug(title, used)
        result.append({"id": section_id, "title": title, "type": section_id if section_id in {
            "about", "education", "publications", "projects", "awards", "experience", "research", "teaching", "news"} else "custom",
            "visible": True, "order": (index + 1) * 10, "content": content})
    return result


def parse_profile(path: Path, project_root: Path | None = None) -> Profile:
    root = (project_root or path.parent).resolve()
    try: text = path.read_text(encoding="utf-8")
    except OSError as exc: raise BuilderError(f"Unable to read profile: {exc}") from exc
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", text, re.S)
    if not match: raise BuilderError("Profile must begin with YAML front matter enclosed by --- lines.")
    try: raw = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None); where = f" near line {mark.line + 2}" if mark else ""
        raise BuilderError(f"Malformed YAML front matter{where}: {getattr(exc, 'problem', exc)}") from exc
    if not isinstance(raw, dict): raise BuilderError("Profile front matter must be a YAML mapping.")
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if not isinstance(raw.get(field), str) or not raw[field].strip(): errors.append(f'Required field "{field}" is missing or empty.')
    if "research_interests" in raw and not isinstance(raw["research_interests"], list): errors.append('Field "research_interests" must be a list.')
    if "links" in raw and not isinstance(raw["links"], dict): errors.append('Field "links" must be a mapping.')
    elif isinstance(raw.get("links"), dict):
        for label, url in raw["links"].items():
            if url and (not isinstance(url, str) or urlparse(url).scheme not in {"http", "https", "mailto"}): errors.append(f'Link "{label}" must use http, https, or mailto.')
    if raw.get("email") and (not isinstance(raw["email"],str) or not EMAIL.fullmatch(raw["email"].strip())):
        errors.append('Field "email" must be a valid email address or empty.')
    for asset_field,label in (("photo","Profile image"),("cv","CV"),("icon","Website icon")):
      asset_value=raw.get(asset_field)
      if asset_value:
        try:
            asset_path = confined_path(root, str(asset_value), label); assets_root = (root / "assets").resolve()
            if assets_root not in asset_path.parents: errors.append(f"{label} must be inside assets/: {asset_value}")
            elif not asset_path.is_file(): errors.append(f"{label} not found: {asset_value}")
        except BuilderError as exc: errors.append(str(exc))
    theme_raw = raw.pop("theme", {}) or {}
    if not isinstance(theme_raw, dict): errors.append('Field "theme" must be a mapping.'); theme_raw = {}
    default = str(theme_raw.get("default", "system"))
    if default not in THEME_DEFAULTS: errors.append('Theme default must be "light", "dark", or "system".')
    theme = Theme(bool(theme_raw.get("enabled", False)), default)
    section_raw = raw.pop("sections", None)
    if section_raw is None: section_raw = _legacy_sections(match.group(2))
    if not isinstance(section_raw, list): errors.append('Field "sections" must be a list.'); section_raw = []
    sections: list[Section] = []; ids: set[str] = set()
    for index, item in enumerate(section_raw):
        if not isinstance(item, dict): errors.append(f"Section {index + 1} must be a mapping."); continue
        sid, title = str(item.get("id", "")), str(item.get("title", "")).strip()
        if not SECTION_ID.fullmatch(sid): errors.append(f'Invalid section ID: "{sid}".')
        elif sid in ids: errors.append(f'Duplicate section ID: "{sid}".')
        ids.add(sid)
        if not title: errors.append(f'Section "{sid or index + 1}" requires a title.')
        content = str(item.get("content", "")); visible = item.get("visible", True)
        if not isinstance(visible, bool): errors.append(f'Section "{sid}" visible must be true or false.')
        try: order = int(item.get("order", (index + 1) * 10))
        except (TypeError, ValueError): errors.append(f'Section "{sid}" order must be a number.'); order = (index + 1) * 10
        sections.append(Section(sid, title, str(item.get("type", "custom")), bool(visible), order, content, _render(content)))
    if errors: raise BuilderError("Profile validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    for field, value in (("department", ""), ("email", ""), ("photo", ""), ("cv", ""), ("icon", ""), ("links", {}), ("research_interests", [])): raw.setdefault(field, value)
    sections.sort(key=lambda section: section.order)
    visible = tuple(section for section in sections if section.visible)
    combined_md = "\n\n".join(f"# {s.title}\n\n{s.markdown}" for s in visible)
    combined_html = "\n".join(f'<section id="{s.id}"><h1>{bleach.clean(s.title)}</h1>{s.html}</section>' for s in visible)
    return Profile(raw, combined_md, combined_html, tuple(sections), theme)


def serialize_profile(profile: Profile, path: Path, *, backup: bool = True,
                      project_root: Path | None = None) -> None:
    data = dict(profile.data)
    data["theme"] = {"enabled": profile.theme.enabled, "default": profile.theme.default}
    data["sections"] = [{"id": s.id, "title": s.title, "type": s.type, "visible": s.visible,
                         "order": (i + 1) * 10, "content": s.markdown} for i, s in enumerate(profile.sections)]
    text = "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000) + "---\n"
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,prefix=f".{path.name}.",suffix=".tmp",delete=False,newline="\n") as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno()); temporary=Path(handle.name)
        # Validate the exact serialized representation before touching the source of truth.
        parse_profile(temporary,project_root or path.parent)
        if backup and path.exists() and not path.with_suffix(path.suffix+".bak").exists(): shutil.copy2(path,path.with_suffix(path.suffix+".bak"))
        os.replace(temporary,path); temporary=None
    finally:
        if temporary and temporary.exists(): temporary.unlink()
