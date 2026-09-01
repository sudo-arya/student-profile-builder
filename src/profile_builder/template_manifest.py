"""Stable template manifest model and validation."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re
import yaml

from .utils import BuilderError

TEMPLATE_MANIFEST_VERSION = "1.0"
PROFILE_SCHEMA_VERSION = "1.1"
ENGINES = {"jinja", "static", "external-build"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class BuildSpec:
    command: tuple[str, ...] = ()
    output_directory: str = "dist"
    data_file: str = "profile-data.json"


@dataclass(frozen=True)
class TemplateManifest:
    id: str
    name: str
    version: str
    author: str
    description: str
    engine: str
    directory: Path
    manifest_version: str = TEMPLATE_MANIFEST_VERSION
    entry: str | None = None
    static_directory: str | None = None
    source_directory: str | None = None
    build: BuildSpec = field(default_factory=BuildSpec)
    executables: tuple[str, ...] = ()
    profile_schemas: tuple[str, ...] = (PROFILE_SCHEMA_VERSION,)
    capabilities: dict[str, bool] = field(default_factory=dict)
    license: str = ""
    third_party: tuple[dict[str, Any], ...] = ()
    preview: str | None = None
    layout_mode: str = "unspecified"


def load_manifest(path: Path) -> TemplateManifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BuilderError(f"Invalid template metadata at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise BuilderError(f"Invalid template metadata at {path}: expected a mapping.")
    missing = [key for key in ("id", "name", "version", "description", "engine") if not raw.get(key)]
    if missing:
        raise BuilderError(f"Invalid template metadata at {path}: missing {', '.join(missing)}.")
    template_id, engine = str(raw["id"]), str(raw["engine"]).lower()
    if not ID_PATTERN.fullmatch(template_id):
        raise BuilderError(f'Invalid template id "{template_id}"; use lowercase letters, numbers, and hyphens.')
    if template_id != path.parent.name:
        raise BuilderError(f'Template id "{template_id}" must match folder "{path.parent.name}".')
    if engine not in ENGINES:
        raise BuilderError(f'Unknown template engine "{engine}". Supported: {", ".join(sorted(ENGINES))}.')
    manifest_version = str(raw.get("manifest_version", TEMPLATE_MANIFEST_VERSION))
    if manifest_version != TEMPLATE_MANIFEST_VERSION:
        raise BuilderError(f'Unsupported manifest version "{manifest_version}".')
    compat = raw.get("compatibility", {}) or {}
    schemas = tuple(str(v) for v in compat.get("profile_schema", [PROFILE_SCHEMA_VERSION]))
    requirements = raw.get("requirements", {}) or {}
    executables = requirements.get("executables", []) or []
    if not isinstance(executables, list) or not all(isinstance(v, str) and v for v in executables):
        raise BuilderError('Manifest "requirements.executables" must be a list of executable names.')
    build_raw = raw.get("build", {}) or {}
    command = build_raw.get("command", []) or []
    if command and (not isinstance(command, list) or not all(isinstance(v, str) and v for v in command)):
        raise BuilderError('External build command must be a non-empty YAML list of strings.')
    if engine == "jinja" and not raw.get("entry"):
        raise BuilderError('Jinja template requires "entry".')
    if engine == "static" and not raw.get("source_directory"):
        raise BuilderError('Static template requires "source_directory".')
    if engine == "external-build" and not command:
        raise BuilderError('External-build template requires "build.command" as a YAML list.')
    manifest = TemplateManifest(template_id, str(raw["name"]), str(raw["version"]),
        str(raw.get("author", "")), str(raw["description"]).strip(), engine, path.parent,
        manifest_version, raw.get("entry"), raw.get("static_directory"), raw.get("source_directory"),
        BuildSpec(tuple(command), str(build_raw.get("output_directory", "dist")),
                  str(build_raw.get("data_file", "profile-data.json"))),
        tuple(executables), schemas, dict(raw.get("capabilities", {}) or {}),
        str(raw.get("license", "")), tuple(raw.get("third_party", []) or []), raw.get("preview"),
        str((raw.get("layout", {}) or {}).get("mode", "unspecified")))
    validate_manifest_paths(manifest)
    return manifest


def _inside(directory: Path, value: str, label: str, must_exist: bool = True) -> Path:
    candidate = (directory / value).resolve()
    root = directory.resolve()
    if candidate == root or root not in candidate.parents:
        raise BuilderError(f"{label} must stay inside the template directory: {value}")
    if must_exist and not candidate.exists():
        raise BuilderError(f"{label} not found: {candidate}")
    return candidate


def validate_manifest_paths(item: TemplateManifest) -> None:
    if item.entry:
        path = _inside(item.directory, item.entry, "Template entry")
        if not path.is_file(): raise BuilderError(f"Template entry is not a file: {path}")
    if item.static_directory:
        path = _inside(item.directory, item.static_directory, "Static directory")
        if not path.is_dir(): raise BuilderError(f"Static directory is not a directory: {path}")
    if item.source_directory:
        path = _inside(item.directory, item.source_directory, "Source directory")
        if not path.is_dir(): raise BuilderError(f"Source directory is not a directory: {path}")
    if item.preview:
        path = _inside(item.directory, item.preview, "Template preview")
        if not path.is_file(): raise BuilderError(f"Template preview is not a file: {path}")
    if item.engine == "external-build":
        _inside(item.directory, item.build.data_file, "Build data file", must_exist=False)
        _inside(item.directory, item.build.output_directory, "Build output directory", must_exist=False)


def check_compatibility(item: TemplateManifest) -> None:
    if PROFILE_SCHEMA_VERSION not in item.profile_schemas and "1.0" not in item.profile_schemas:
        raise BuilderError(f'Template "{item.name}" is incompatible with profile schema {PROFILE_SCHEMA_VERSION}. '
                           f'Supported by template: {", ".join(item.profile_schemas) or "none"}.')
