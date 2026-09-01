from pathlib import Path
import pytest

from profile_builder.templates import discover_templates, selected_template
from profile_builder.utils import BuilderError
from conftest import make_project


def test_discovers_valid_template(tmp_path):
    root = make_project(tmp_path)
    assert discover_templates(root / "templates")["basic"].engine == "jinja"


def test_malformed_metadata_is_clear(tmp_path):
    folder = tmp_path / "templates" / "bad"; folder.mkdir(parents=True)
    (folder / "template.yml").write_text("id: [", encoding="utf-8")
    with pytest.raises(BuilderError, match="Invalid template metadata"):
        discover_templates(tmp_path / "templates")


def test_unknown_configured_template_is_clear(tmp_path):
    templates = discover_templates(make_project(tmp_path) / "templates")
    with pytest.raises(BuilderError, match="was not found"):
        selected_template(templates, "missing")
