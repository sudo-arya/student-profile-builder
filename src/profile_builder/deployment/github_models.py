from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..utils import BuilderError


class GitHubSiteType(str, Enum):
    PERSONAL = "personal"
    PROJECT = "project"

    @classmethod
    def parse(cls, value: str) -> "GitHubSiteType":
        try: return cls(value.lower())
        except (ValueError, AttributeError) as exc:
            raise BuilderError('GitHub site type must be "personal" or "project".') from exc


@dataclass(frozen=True)
class GitHubDeploymentRequest:
    output_directory: Path
    site_type: GitHubSiteType
    repository: str | None = None
    expected_username: str | None = None
    dry_run: bool = False
    assume_yes: bool = False
    allow_login: bool = False


@dataclass(frozen=True)
class GitHubDeploymentResult:
    success: bool
    username: str
    repository: str
    url: str
    file_count: int
    total_bytes: int
    dry_run: bool = False
    changed: bool = True
