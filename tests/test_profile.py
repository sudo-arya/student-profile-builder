from pathlib import Path
import pytest

from profile_builder.profile import parse_profile
from profile_builder.utils import BuilderError


def write_profile(root: Path, front: str, body: str = "# About\n\nHello **world**.") -> Path:
    path = root / "profile.md"
    path.write_text(f"---\n{front}\n---\n{body}\n", encoding="utf-8")
    return path


def test_valid_front_matter_markdown_and_optional_fields(tmp_path):
    profile = parse_profile(write_profile(tmp_path, "name: Ada\ndesignation: Student\ninstitute: IIT Delhi"))
    assert profile.data["name"] == "Ada"
    assert profile.data["links"] == {}
    assert "<h1>About</h1>" in profile.html and "<strong>world</strong>" in profile.html


def test_missing_required_field(tmp_path):
    with pytest.raises(BuilderError, match='field "name"'):
        parse_profile(write_profile(tmp_path, "designation: Student\ninstitute: IIT Delhi"))


def test_malformed_yaml(tmp_path):
    with pytest.raises(BuilderError, match="Malformed YAML"):
        parse_profile(write_profile(tmp_path, "name: [broken\ndesignation: Student\ninstitute: IIT"))


def test_invalid_collections_and_path_traversal(tmp_path):
    with pytest.raises(BuilderError) as error:
        parse_profile(write_profile(tmp_path, "name: A\ndesignation: B\ninstitute: C\nlinks: no\nresearch_interests: no\nphoto: ../secret.jpg"))
    assert "must be a mapping" in str(error.value)
    assert "inside the project" in str(error.value)


def test_raw_script_is_removed(tmp_path):
    profile = parse_profile(write_profile(tmp_path, "name: A\ndesignation: B\ninstitute: C", "# Hi\n<script>alert(1)</script>"))
    assert "<script>" not in profile.html


def test_unsafe_link_scheme_is_rejected(tmp_path):
    with pytest.raises(BuilderError, match="must use http"):
        parse_profile(write_profile(tmp_path, "name: A\ndesignation: B\ninstitute: C\nlinks:\n  website: 'javascript:alert(1)'"))
