from pathlib import Path
import shutil
import pytest

from conftest import ROOT, make_project
from profile_builder.builder import build_site
from profile_builder.config import Config
from profile_builder.deployment.github_cli import CLIResult, GitHubCLI
from profile_builder.deployment.github_models import GitHubDeploymentRequest, GitHubSiteType
from profile_builder.deployment.github_pages import GitHubPagesDeploymentProvider, deployment_identity, validate_repository
from profile_builder.deployment.git_client import GitClient
from profile_builder.utils import BuilderError


def built(tmp_path):
    root = make_project(tmp_path); shutil.copy(ROOT / "examples/profiles/full.md", root / "profile.md")
    return root, build_site(root, Config())


def test_requirements(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    assert GitHubCLI().check_tools() == ("/bin/git", "/bin/gh")


@pytest.mark.parametrize("missing", ["git", "gh"])
def test_missing_requirements(monkeypatch, missing):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == missing else f"/bin/{name}")
    with pytest.raises(BuilderError, match=f"command not found: {missing}"): GitHubCLI().check_tools()


@pytest.mark.parametrize("name", ["academic-profile", "profile_2026", "student.page"])
def test_safe_repository_names(name): assert validate_repository(name) == name


@pytest.mark.parametrize("name", ["../repo", "owner/repo", "repo;command", "repo name", "https://github.com/test", "C:\\repo", "x.git"])
def test_unsafe_repository_names(name):
    with pytest.raises(BuilderError, match="Invalid GitHub repository"): validate_repository(name)


def test_personal_and_project_identity():
    assert deployment_identity("deepanshu", GitHubSiteType.PERSONAL, None) == (
        "deepanshu.github.io", "https://deepanshu.github.io/")
    assert deployment_identity("deepanshu", GitHubSiteType.PROJECT, "academic-profile") == (
        "academic-profile", "https://deepanshu.github.io/academic-profile/")
    with pytest.raises(BuilderError, match="personal site mode"):
        deployment_identity("deepanshu", GitHubSiteType.PROJECT, "deepanshu.github.io")


class FakeCLI:
    def __init__(self, username="deepanshu", exists=True, branch=(False, False), pages=None):
        self.account = username; self.exists = exists; self.branch = branch; self.pages = pages; self.calls = []
    def check_tools(self): self.calls.append(("tools",)); return "git", "gh"
    def username(self, gh): self.calls.append(("username", gh)); return self.account
    def login(self, gh): self.calls.append(("login", gh))
    def repository_exists(self, gh, repo): self.calls.append(("exists", repo)); return self.exists
    def create_repository(self, gh, repo): self.calls.append(("create", repo))
    def branch_marker(self, gh, repo): self.calls.append(("marker", repo)); return self.branch
    def pages_source(self, gh, repo): self.calls.append(("pages", repo)); return self.pages
    def configure_pages(self, gh, repo, existing): self.calls.append(("configure", repo, existing))


class FakeGit:
    def __init__(self, changed=True, fail=False): self.calls = []; self.changed = changed; self.fail = fail
    def publish(self, git, source, workspace, remote, branch):
        self.calls.append((git, source, workspace, remote, branch,
                           sorted(path.name for path in source.iterdir())))
        assert workspace != source and not (source / ".git").exists()
        assert ".nojekyll" not in [p.name for p in source.iterdir()]  # GitClient adds it in its repo.
        assert ".profile-builder-pages.json" in [p.name for p in source.iterdir()]
        if self.fail: raise BuilderError("Git push failed")
        return self.changed


def provider(cli, git=None, answers=None):
    choices = iter(answers or [])
    return GitHubPagesDeploymentProvider(cli, git or FakeGit(), lambda _m, _d: next(choices), lambda _m: None)


def request(output, **kwargs):
    values = {"site_type": GitHubSiteType.PROJECT, "repository": "academic-profile"}
    values.update(kwargs); return GitHubDeploymentRequest(output, **values)


def test_zero_network_dry_run(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(); git = FakeGit()
    result = provider(cli, git).deploy(request(output, expected_username="deepanshu", dry_run=True))
    assert result.dry_run and cli.calls == [("tools",)] and git.calls == []


def test_dry_run_account_mismatch(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI("active")
    with pytest.raises(BuilderError, match="does not match"):
        provider(cli).deploy(request(output, expected_username="expected", dry_run=False))


def test_unauthenticated_login_only_when_allowed(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(None)
    with pytest.raises(BuilderError, match="not authenticated"): provider(cli).deploy(request(output))
    assert not any(call[0] == "login" for call in cli.calls)
    cli = FakeCLI(None)
    def login(gh): cli.calls.append(("login", gh)); cli.account = "deepanshu"
    cli.login = login
    provider(cli, answers=[True]).deploy(request(output, allow_login=True, assume_yes=True))
    assert ("login", "gh") in cli.calls


def test_authentication_failure(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(None)
    with pytest.raises(BuilderError, match="no active account"):
        provider(cli, answers=[True]).deploy(request(output, allow_login=True))


def test_authentication_declined(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(None)
    with pytest.raises(BuilderError, match="cancelled before authentication"):
        provider(cli, answers=[False]).deploy(request(output, allow_login=True))
    assert not any(call[0] == "login" for call in cli.calls)


def test_repository_lookup_error_is_not_absent(monkeypatch):
    cli = GitHubCLI()
    monkeypatch.setattr(cli, "run", lambda *args, **kwargs: CLIResult(2, "", "network failure"))
    with pytest.raises(BuilderError, match="Unable to check"):
        cli.repository_exists("gh", "owner/repo")


def test_repository_creation_and_pages_configuration(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(exists=False); git = FakeGit()
    result = provider(cli, git).deploy(request(output, assume_yes=True))
    assert result.success
    assert ("create", "deepanshu/academic-profile") in cli.calls
    assert ("configure", "deepanshu/academic-profile", False) in cli.calls
    assert git.calls[0][3] == "https://github.com/deepanshu/academic-profile.git"


def test_repository_creation_declined(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(exists=False); git = FakeGit()
    with pytest.raises(BuilderError, match="cancelled"):
        provider(cli, git, [False]).deploy(request(output))
    assert git.calls == [] and not any(c[0] == "create" for c in cli.calls)


@pytest.mark.parametrize(("branch", "answers", "allowed"), [
    ((False, False), [], True), ((True, True), [], True), ((True, False), [False], False), ((True, False), [True], True)
])
def test_branch_ownership(tmp_path, branch, answers, allowed):
    _, output = built(tmp_path); cli = FakeCLI(branch=branch, pages="gh-pages:/"); git = FakeGit()
    if allowed: provider(cli, git, answers).deploy(request(output)); assert git.calls
    else:
        with pytest.raises(BuilderError, match="unmanaged"): provider(cli, git, answers).deploy(request(output))
        assert git.calls == []


def test_pages_source_confirmation(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(branch=(True, True), pages="main:/docs"); git = FakeGit()
    with pytest.raises(BuilderError, match="configuration was not changed"):
        provider(cli, git, [False]).deploy(request(output))
    assert git.calls == []


def test_noop_skips_pages_mutation(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(branch=(True, True), pages="gh-pages:/"); git = FakeGit(False)
    result = provider(cli, git).deploy(request(output))
    assert not result.changed and not any(c[0] == "configure" for c in cli.calls)


def test_push_failure_never_claims_success(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI(branch=(True, True), pages="gh-pages:/")
    with pytest.raises(BuilderError, match="Git push failed"): provider(cli, FakeGit(fail=True)).deploy(request(output))


def test_pages_configuration_failure_propagates(tmp_path):
    _, output = built(tmp_path); cli = FakeCLI()
    def fail(*args): raise BuilderError("files were pushed successfully, but GitHub Pages configuration failed")
    cli.configure_pages = fail
    with pytest.raises(BuilderError, match="pushed successfully"):
        provider(cli).deploy(request(output))


def test_cli_wrapper_never_requests_token(monkeypatch):
    calls = []
    def fake_run(args, **kwargs): calls.append(args); return type("R", (), {"returncode": 0, "stdout": "deepanshu\n", "stderr": ""})()
    monkeypatch.setattr("subprocess.run", fake_run)
    cli = GitHubCLI(); assert cli.username("gh") == "deepanshu"
    joined = " ".join(calls[0])
    assert "auth token" not in joined and "--token" not in joined and "--password" not in joined


def test_real_git_publisher_uses_only_gh_pages_and_generated_files(tmp_path):
    git = shutil.which("git")
    if not git: pytest.skip("Git is not installed")
    source = tmp_path / "source"; source.mkdir()
    (source / "index.html").write_text("profile", encoding="utf-8")
    (source / ".profile-builder-pages.json").write_text("{}", encoding="utf-8")
    bare = tmp_path / "remote.git"
    import subprocess
    subprocess.run([git, "init", "--bare", str(bare)], check=True, capture_output=True)
    workspace = tmp_path / "workspace"; workspace.mkdir()
    assert GitClient().publish(git, source, workspace, str(bare), False)
    branches = subprocess.run([git, "--git-dir", str(bare), "branch", "--format=%(refname:short)"],
                              check=True, text=True, capture_output=True).stdout.splitlines()
    files = subprocess.run([git, "--git-dir", str(bare), "ls-tree", "-r", "--name-only", "gh-pages"],
                           check=True, text=True, capture_output=True).stdout.splitlines()
    assert branches == ["gh-pages"]
    assert sorted(files) == [".nojekyll", ".profile-builder-pages.json", "index.html"]
    assert not (source / ".git").exists()
