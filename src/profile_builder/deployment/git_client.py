from pathlib import Path
from typing import Sequence
import shutil
import subprocess

from ..utils import BuilderError


class GitClient:
    def run(self, git: str, arguments: Sequence[str], cwd: Path, *, capture: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run([git, *arguments], cwd=cwd, shell=False, check=False, text=True,
            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)

    def publish(self, git: str, source: Path, workspace: Path, remote_url: str, branch_exists: bool) -> bool:
        repo = workspace / "site"; repo.mkdir()
        init = self.run(git, ["init", "--initial-branch=gh-pages"], repo)
        if init.returncode: raise BuilderError("Unable to initialize the temporary Git deployment workspace.")
        self._check(git, ["config", "user.name", "Student Profile Builder"], repo, "configure local Git identity")
        self._check(git, ["config", "user.email", "student-profile-builder@users.noreply.github.com"], repo, "configure local Git identity")
        self._check(git, ["remote", "add", "origin", remote_url], repo, "configure GitHub remote")
        if branch_exists:
            self._check(git, ["fetch", "--depth=1", "origin", "gh-pages"], repo, "fetch gh-pages")
            self._check(git, ["checkout", "-B", "gh-pages", "FETCH_HEAD"], repo, "check out gh-pages")
            for child in repo.iterdir():
                if child.name != ".git":
                    if child.is_dir(): shutil.rmtree(child)
                    else: child.unlink()
        for child in source.iterdir():
            target = repo / child.name
            if child.is_dir(): shutil.copytree(child, target)
            else: shutil.copy2(child, target)
        (repo / ".nojekyll").touch()
        self._check(git, ["add", "--all"], repo, "stage generated website")
        diff = self.run(git, ["diff", "--cached", "--quiet"], repo)
        if diff.returncode == 0: return False
        if diff.returncode != 1: raise BuilderError("Unable to compare generated GitHub Pages content.")
        self._check(git, ["commit", "-m", "Deploy student profile website"], repo, "commit generated website")
        push = ["push", "origin", "gh-pages"]
        if branch_exists: push.append("--force-with-lease")
        result = self.run(git, push, repo, capture=False)
        if result.returncode: raise BuilderError("Unable to publish the website to GitHub. Git push to gh-pages failed; the repository was not deleted.")
        return True

    def _check(self, git: str, arguments: list[str], cwd: Path, action: str) -> None:
        result = self.run(git, arguments, cwd)
        if result.returncode: raise BuilderError(f"Unable to {action} in the temporary deployment workspace.")
