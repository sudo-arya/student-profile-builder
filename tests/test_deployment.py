from pathlib import Path
import json
import shutil
import pytest

from conftest import make_project, ROOT
from profile_builder.builder import build_site
from profile_builder.config import Config
from profile_builder.deployment.iitd import IITDDeploymentProvider, _remote_script, validate_userid
from profile_builder.deployment.manifest import collect_files, create_manifest, parse_manifest, stale_files
from profile_builder.deployment.models import DeploymentRequest, IITDTarget
from profile_builder.deployment.ssh import CommandResult, OpenSSHRunner
from profile_builder.utils import BuilderError


@pytest.mark.parametrize(("value", "directory", "url"), [
    ("public", "public_html", "https://web.iitd.ac.in/~ird123/"),
    ("private", "private_html", "http://privateweb.iitd.ac.in/~ird123/"),
])
def test_targets(value, directory, url):
    target = IITDTarget.parse(value)
    assert target.directory == directory and target.url("ird123") == url


def test_invalid_target():
    with pytest.raises(BuilderError, match="public.*private"): IITDTarget.parse("other")


@pytest.mark.parametrize("userid", ["ird123456", "student.name", "abc_123", "abc-123"])
def test_valid_userids(userid): assert validate_userid(userid) == userid


@pytest.mark.parametrize("userid", ["abc@host", "../../test", "abc;rm", "abc name", '"abc"', ""])
def test_invalid_userids(userid):
    with pytest.raises(BuilderError, match="Invalid IIT Delhi user ID"): validate_userid(userid)


def test_dependency_checks(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda value: f"/bin/{value}")
    assert OpenSSHRunner().check_tools() == ("/bin/ssh", "/bin/scp")


@pytest.mark.parametrize("missing", ["ssh", "scp"])
def test_missing_dependency(monkeypatch, missing):
    monkeypatch.setattr(shutil, "which", lambda value: None if value == missing else f"/bin/{value}")
    with pytest.raises(BuilderError, match=f"command not found: {missing}"): OpenSSHRunner().check_tools()


def output(tmp_path):
    root = make_project(tmp_path); shutil.copy(ROOT / "examples/profiles/full.md", root / "profile.md")
    return build_site(root, Config())


def test_manifest_is_deterministic_and_posix(tmp_path):
    built = output(tmp_path); files, total = collect_files(built)
    manifest = create_manifest(built, IITDTarget.PUBLIC)
    assert files == sorted(files) == manifest["files"] and total > 0
    assert "index.html" in files and all("\\" not in value and not Path(value).is_absolute() for value in files)


@pytest.mark.parametrize("value", ["../file", "/home/file", "~/file", "C:\\file", "", "a\\b"])
def test_unsafe_previous_manifest_paths(value):
    raw = json.dumps({"manifest_version": "1.0", "files": [value]})
    with pytest.raises(BuilderError, match="manifest|Unsafe"): parse_manifest(raw)


def test_manifest_diff_only_stale():
    old = {"files": ["a", "b", "c"]}; new = {"files": ["a", "c", "d"]}
    assert stale_files(old, new) == ["b"] and stale_files(None, new) == []


class FakeRunner:
    def __init__(self, responses=None): self.calls = []; self.responses = list(responses or [])
    def check_tools(self): return ("ssh", "scp")
    def run(self, arguments, *, capture=False):
        self.calls.append((list(arguments), capture))
        return self.responses.pop(0) if self.responses else CommandResult(0, "")


def request(tmp_path, dry=False):
    return DeploymentRequest(output(tmp_path), "ird123", IITDTarget.PUBLIC, dry)


def test_dry_run_makes_no_runner_calls(tmp_path):
    runner = FakeRunner(); result = IITDDeploymentProvider(runner, status=lambda _: None).deploy(request(tmp_path, True))
    assert result.dry_run and runner.calls == []


def test_success_sequence_and_commands_are_safe(tmp_path):
    previous = json.dumps({"manifest_version": "1.0", "files": ["old.css"]})
    runner = FakeRunner([CommandResult(0, previous), CommandResult(0), CommandResult(0)])
    result = IITDDeploymentProvider(runner, status=lambda _: None).deploy(request(tmp_path))
    assert result.success and [call[0][0] for call in runner.calls] == ["ssh", "scp", "ssh"]
    joined = " ".join(arg for call, _ in runner.calls for arg in call)
    assert "ssh1.iitd.ac.in" in joined and "public_html" in joined
    assert "password" not in joined.lower() and "StrictHostKeyChecking" not in joined and "rm -rf" not in joined


def test_first_deployment_needs_confirmation(tmp_path):
    runner = FakeRunner([CommandResult(0, "")])
    with pytest.raises(BuilderError, match="cancelled"):
        IITDDeploymentProvider(runner, status=lambda _: None, confirm_first=lambda: False).deploy(request(tmp_path))
    assert len(runner.calls) == 1


def test_first_deployment_has_no_cleanup(tmp_path):
    runner = FakeRunner([CommandResult(0, ""), CommandResult(0), CommandResult(0)])
    IITDDeploymentProvider(runner, status=lambda _: None, confirm_first=lambda: True).deploy(request(tmp_path))
    script_call = runner.calls[-1][0][-1]
    # The fixed staging cleanup uses rm -r; no managed-file rm -f appears without a prior manifest.
    assert "rm -f" not in script_call


@pytest.mark.parametrize(("responses", "message", "expected_calls"), [
    ([CommandResult(1)], "ownership manifest", 1),
    ([CommandResult(0, "{}")], "unsupported format", 1),
    ([CommandResult(0, '{"manifest_version":"1.0","files":[]}'), CommandResult(1)], "uploading", 2),
    ([CommandResult(0, '{"manifest_version":"1.0","files":[]}'), CommandResult(0), CommandResult(1)], "verification failed", 3),
])
def test_deployment_failures(tmp_path, responses, message, expected_calls):
    runner = FakeRunner(responses)
    with pytest.raises(BuilderError, match=message):
        IITDDeploymentProvider(runner, status=lambda _: None).deploy(request(tmp_path))
    assert len(runner.calls) == expected_calls


def test_remote_script_permissions_and_scoped_cleanup():
    script = _remote_script("public_html", ".student-profile-builder-upload-0123456789abcdef0123456789abcdef", ["index.html", "assets/a.css"], ["old.css"])
    assert 'chmod o+x "$HOME"' in script and "chmod 755" in script and "chmod 644" in script
    assert 'rm -f -- "$target"/old.css' in script
    assert "chmod -R" not in script and 'rm -rf -- "$stage"' in script
    assert 'rm -rf -- "$target"' not in script and 'rm -rf -- "$HOME"' not in script


@pytest.mark.parametrize(("target","stage"),[("public_html","$HOME"),("private_html",".bad"),("home",".student-profile-builder-upload-0123456789abcdef0123456789abcdef")])
def test_remote_script_rejects_unsafe_cleanup_paths(target,stage):
    with pytest.raises(BuilderError,match="unsafe remote"):
        _remote_script(target,stage,["index.html"],[])


def test_cleanup_failure_is_success_warning(tmp_path):
    previous=json.dumps({"manifest_version":"1.0","files":[]})
    runner=FakeRunner([CommandResult(0,previous),CommandResult(0),CommandResult(0,"__SPB_CLEANUP_WARNING__")])
    result=IITDDeploymentProvider(runner,status=lambda _:None).deploy(request(tmp_path))
    assert result.success and result.warnings and "staging" in result.warnings[0]


def test_symlink_output_rejected(tmp_path):
    built = tmp_path / "dist"; built.mkdir(); (built / "index.html").write_text("ok")
    target = tmp_path / "outside.txt"; target.write_text("secret")
    try: (built / "link.txt").symlink_to(target)
    except OSError: pytest.skip("Symlink creation is not permitted on this platform")
    with pytest.raises(BuilderError, match="symbolic link"): collect_files(built)
