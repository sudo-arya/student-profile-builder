"""Safe GitHub CLI boundary. It never retrieves authentication tokens."""
from dataclasses import dataclass
from typing import Sequence
import json
import shutil
import subprocess

from ..utils import BuilderError


@dataclass(frozen=True)
class CLIResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class GitHubCLI:
    def check_tools(self) -> tuple[str, str]:
        git, gh = shutil.which("git"), shutil.which("gh")
        if not git: raise BuilderError("GitHub Pages deployment cannot start.\n\nRequired command not found: git")
        if not gh: raise BuilderError("GitHub Pages deployment cannot start.\n\nRequired command not found: gh\n\nInstall GitHub CLI, run `gh auth login`, and try again.")
        return git, gh

    def run(self, arguments: Sequence[str], *, capture: bool = True, cwd=None) -> CLIResult:
        result = subprocess.run(list(arguments), cwd=cwd, shell=False, check=False, text=True,
            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
        return CLIResult(result.returncode, result.stdout or "", result.stderr or "")

    def username(self, gh: str) -> str | None:
        result = self.run([gh, "api", "user", "--jq", ".login"])
        return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    def login(self, gh: str) -> None:
        result = self.run([gh, "auth", "login"], capture=False)
        if result.returncode: raise BuilderError("GitHub CLI authentication did not complete successfully.")

    def repository_exists(self, gh: str, owner_repo: str) -> bool:
        result = self.run([gh, "repo", "view", owner_repo, "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
        if result.returncode == 0: return True
        combined = (result.stdout + result.stderr).lower()
        if "not found" in combined or "could not resolve" in combined: return False
        raise BuilderError(f"Unable to check GitHub repository {owner_repo}.")

    def create_repository(self, gh: str, owner_repo: str) -> None:
        result = self.run([gh, "repo", "create", owner_repo, "--public"], capture=False)
        if result.returncode: raise BuilderError(f"Unable to create public GitHub repository {owner_repo}.")

    def branch_marker(self, gh: str, owner_repo: str) -> tuple[bool, bool]:
        branch = self.run([gh, "api", f"repos/{owner_repo}/branches/gh-pages", "--silent"])
        if branch.returncode: return False, False
        marker = self.run([gh, "api", f"repos/{owner_repo}/contents/.profile-builder-pages.json?ref=gh-pages", "--silent"])
        return True, marker.returncode == 0

    def pages_source(self, gh: str, owner_repo: str) -> str | None:
        result = self.run([gh, "api", f"repos/{owner_repo}/pages"])
        if result.returncode: return None
        try:
            source = json.loads(result.stdout).get("source", {})
            return f"{source.get('branch', '')}:{source.get('path', '')}"
        except (json.JSONDecodeError, AttributeError):
            raise BuilderError("GitHub returned an unexpected Pages configuration response.")

    def configure_pages(self, gh: str, owner_repo: str, existing: bool) -> None:
        method = "PUT" if existing else "POST"
        result = self.run([gh, "api", "--method", method, f"repos/{owner_repo}/pages",
                           "-f", "source[branch]=gh-pages", "-f", "source[path]=/"])
        if result.returncode:
            raise BuilderError("Website files were pushed successfully, but GitHub Pages configuration failed.")
