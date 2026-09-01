from pathlib import Path
from typing import Callable
import json
import re
import shutil
import tempfile

from ..builder import validate_output
from ..utils import BuilderError
from .git_client import GitClient
from .github_cli import GitHubCLI
from .github_models import GitHubDeploymentRequest, GitHubDeploymentResult, GitHubSiteType
from .manifest import collect_files

PAGES_MARKER = ".profile-builder-pages.json"
REPOSITORY = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def validate_repository(value: str) -> str:
    if not REPOSITORY.fullmatch(value) or value in {".", ".."} or value.endswith(".git"):
        raise BuilderError("Invalid GitHub repository name. Use only letters, numbers, dots, underscores, and hyphens.")
    return value


def deployment_identity(username: str, site: GitHubSiteType, repository: str | None) -> tuple[str, str]:
    if not REPOSITORY.fullmatch(username): raise BuilderError("GitHub CLI returned an invalid account name.")
    personal = f"{username}.github.io"
    if site is GitHubSiteType.PERSONAL:
        if repository and repository.lower() != personal.lower(): raise BuilderError(f'Personal site repository must be "{personal}".')
        return personal, f"https://{username}.github.io/"
    repo = validate_repository(repository or "")
    if repo.lower() == personal.lower(): raise BuilderError("Use personal site mode for the username.github.io repository.")
    return repo, f"https://{username}.github.io/{repo}/"


class GitHubPagesDeploymentProvider:
    def __init__(self, cli: GitHubCLI | None = None, git_client: GitClient | None = None,
                 confirm: Callable[[str, bool], bool] | None = None, status: Callable[[str], None] = print):
        self.cli = cli or GitHubCLI(); self.git_client = git_client or GitClient()
        self.confirm = confirm or (lambda _message, default: False); self.status = status

    def deploy(self, request: GitHubDeploymentRequest) -> GitHubDeploymentResult:
        output = request.output_directory.resolve()
        issues = validate_output(output)
        if issues: raise BuilderError("GitHub deployment stopped: generated output is invalid.")
        files, total = collect_files(output)
        git, gh = self.cli.check_tools()
        if request.dry_run and request.expected_username:
            username = request.expected_username
        else:
            username = self.cli.username(gh)
            if not username:
                if request.dry_run: raise BuilderError("GitHub dry run needs an authenticated gh account or --username for zero-network planning.")
                if not request.allow_login: raise BuilderError("GitHub CLI is not authenticated. Run `gh auth login`, or allow interactive login.")
                if not self.confirm("GitHub CLI is not authenticated. Run `gh auth login` now?", True):
                    raise BuilderError("GitHub deployment cancelled before authentication.")
                self.cli.login(gh); username = self.cli.username(gh)
                if not username: raise BuilderError("GitHub CLI authentication completed but no active account was found.")
        if request.expected_username and username.lower() != request.expected_username.lower():
            raise BuilderError(f'Active GitHub account "{username}" does not match expected account "{request.expected_username}".')
        repository, url = deployment_identity(username, request.site_type, request.repository)
        result = GitHubDeploymentResult(True, username, repository, url, len(files), total, request.dry_run)
        if request.dry_run:
            self.status("Dry run: no repository, branch, push, or Pages setting was modified.")
            return result
        owner_repo = f"{username}/{repository}"
        exists = self.cli.repository_exists(gh, owner_repo)
        if not exists:
            if not (request.assume_yes or self.confirm(f'Create public repository "{owner_repo}"?', True)):
                raise BuilderError("GitHub deployment cancelled before repository creation.")
            self.cli.create_repository(gh, owner_repo)
        branch_exists, managed = self.cli.branch_marker(gh, owner_repo)
        if branch_exists and not managed and not (request.assume_yes or self.confirm(
                "The existing gh-pages branch is not managed by Student Profile Builder and may be replaced.", False)):
            raise BuilderError("GitHub deployment cancelled; the unmanaged gh-pages branch was not changed.")
        pages = self.cli.pages_source(gh, owner_repo)
        if pages and pages != "gh-pages:/" and not (request.assume_yes or self.confirm(
                f"GitHub Pages currently publishes from {pages}; change it to gh-pages:/?", False)):
            raise BuilderError("GitHub deployment cancelled; Pages configuration was not changed.")
        with tempfile.TemporaryDirectory(prefix="profile-github-") as temporary:
            staged = Path(temporary) / "generated"; shutil.copytree(output, staged)
            (staged / PAGES_MARKER).write_text(json.dumps({"schema_version": "1.0", "generator": "Student Profile Builder",
                "provider": "github-pages"}, indent=2), encoding="utf-8")
            changed = self.git_client.publish(git, staged, Path(temporary),
                f"https://github.com/{owner_repo}.git", branch_exists)
        if changed and pages != "gh-pages:/": self.cli.configure_pages(gh, owner_repo, pages is not None)
        return GitHubDeploymentResult(True, username, repository, url, len(files), total, False, changed)
