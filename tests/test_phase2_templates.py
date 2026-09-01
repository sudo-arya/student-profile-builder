from pathlib import Path
import json
import shutil
import sys
import pytest
import yaml

from conftest import make_project, ROOT
from profile_builder.builder import build_site, validate_output
from profile_builder.config import Config
from profile_builder.template_manifest import load_manifest
from profile_builder.template_tools import check_template, create_template
from profile_builder.templates import discover_templates
from profile_builder.utils import BuilderError


def manifest(folder: Path, raw: dict, files: dict[str, str] | None = None):
    folder.mkdir(parents=True)
    for name, value in (files or {}).items():
        path = folder / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value, encoding="utf-8")
    (folder / "template.yml").write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def base(template_id="sample", engine="jinja"):
    return {"id": template_id, "name": "Sample", "version": "1.0", "description": "Test", "engine": engine}


@pytest.mark.parametrize(("engine", "extra", "files"), [
    ("jinja", {"entry": "index.html.j2"}, {"index.html.j2": "<h1>{{ profile.name }}</h1>"}),
    ("static", {"source_directory": "site"}, {"site/index.html": "ok"}),
    ("external-build", {"build": {"command": ["tool"], "output_directory": "out"}}, {}),
])
def test_valid_engine_manifests(tmp_path, engine, extra, files):
    raw = base(engine=engine); raw.update(extra); manifest(tmp_path / "sample", raw, files)
    assert load_manifest(tmp_path / "sample" / "template.yml").engine == engine


@pytest.mark.parametrize(("change", "message"), [
    ({"id": None}, "missing id"), ({"id": "other"}, "must match folder"),
    ({"engine": "magic"}, "Unknown template engine"), ({"entry": None}, "requires \"entry\""),
])
def test_invalid_manifest_fields(tmp_path, change, message):
    raw = base(); raw.update(change); manifest(tmp_path / "sample", raw)
    with pytest.raises(BuilderError, match=message): load_manifest(tmp_path / "sample" / "template.yml")


def test_registry_multiple_and_ignores_other_directories(tmp_path):
    manifest(tmp_path / "one", {**base("one"), "entry": "index.j2"}, {"index.j2": "ok"})
    manifest(tmp_path / "two", {**base("two", "static"), "source_directory": "site"}, {"site/index.html": "ok"})
    (tmp_path / "notes").mkdir()
    assert set(discover_templates(tmp_path)) == {"one", "two"}


def project_with_template(tmp_path: Path, example: str) -> Path:
    root = make_project(tmp_path)
    shutil.copy(ROOT / "examples/profiles/full.md", root / "profile.md")
    shutil.copytree(ROOT / "examples" / "templates" / example, root / "templates" / example)
    return root


def test_static_renderer_contract(tmp_path):
    root = project_with_template(tmp_path, "static-example")
    output = build_site(root, Config(), template_id="static-example")
    data = json.loads((output / "profile-data.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.1" and data["profile"]["name"]
    assert not data["profile"]["photo"] or data["profile"]["photo"].startswith("assets/user/")


def test_external_renderer_contract(tmp_path):
    root = project_with_template(tmp_path, "external-build-example")
    output = build_site(root, Config(), template_id="external-build-example")
    assert "<h1>" in (output / "index.html").read_text(encoding="utf-8")
    assert not (root / "templates" / "external-build-example" / "generated").exists()


def external(root: Path, command: list[str], script: str = "", output="out"):
    folder = root / "templates" / "external"
    raw = {**base("external", "external-build"), "build": {"command": command, "output_directory": output}}
    manifest(folder, raw, {"script.py": script})
    return folder


@pytest.mark.parametrize(("command", "script", "match"), [
    (["definitely-missing-executable-xyz"], "", "Required executable not found"),
    (["{python}", "script.py"], "raise SystemExit(3)", "Exit code: 3"),
    (["{python}", "script.py"], "print('nothing')", "build output was not found"),
    (["{python}", "script.py"], "from pathlib import Path; Path('out').mkdir()", "index.html"),
])
def test_external_failures(tmp_path, command, script, match):
    root = make_project(tmp_path); shutil.copy(ROOT / "examples/profiles/full.md", root / "profile.md")
    external(root, command, script)
    with pytest.raises(BuilderError, match=match): build_site(root, Config(), template_id="external")


@pytest.mark.parametrize(("contents", "message"), [
    ('<img src="/assets/a.png">', "root-relative"),
    ('<p>C:\\Users\\name\\photo.jpg</p>', "absolute filesystem"),
    ('<p>/home/person/photo.jpg</p>', "absolute filesystem"),
])
def test_output_validation_rejects_bad_paths(tmp_path, contents, message):
    (tmp_path / "index.html").write_text(contents, encoding="utf-8")
    assert message in validate_output(tmp_path)[0].message


def test_output_validation_accepts_relative(tmp_path):
    (tmp_path / "index.html").write_text('<img src="./assets/user/a.png">', encoding="utf-8")
    assert validate_output(tmp_path) == []


def test_template_checker_and_schema_incompatibility(tmp_path):
    root = make_project(tmp_path); shutil.copy(ROOT / "examples/profiles/full.md", root / "profile.md")
    assert "[OK] build succeeded" in check_template(root, "basic")
    path = root / "templates" / "basic" / "template.yml"
    raw = yaml.safe_load(path.read_text()); raw["compatibility"] = {"profile_schema": ["9.0"]}
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(BuilderError, match="incompatible"): check_template(root, "basic")


@pytest.mark.parametrize("engine", ["jinja", "static", "external-build"])
def test_scaffolding(engine, tmp_path):
    folder = create_template(tmp_path, f"new-{engine}", "New", "TA", engine)
    assert (folder / "template.yml").is_file()
    assert load_manifest(folder / "template.yml").engine == engine
