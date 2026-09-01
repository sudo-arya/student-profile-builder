from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class IITDTarget(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

    @property
    def directory(self) -> str:
        return "public_html" if self is IITDTarget.PUBLIC else "private_html"

    def url(self, userid: str) -> str:
        host = "web.iitd.ac.in" if self is IITDTarget.PUBLIC else "privateweb.iitd.ac.in"
        scheme = "https" if self is IITDTarget.PUBLIC else "http"
        return f"{scheme}://{host}/~{userid}/"

    @classmethod
    def parse(cls, value: str) -> "IITDTarget":
        try: return cls(value.lower())
        except (ValueError, AttributeError) as exc:
            from ..utils import BuilderError
            raise BuilderError('Deployment target must be "public" or "private".') from exc


@dataclass(frozen=True)
class DeploymentRequest:
    output_directory: Path
    userid: str
    target: IITDTarget
    dry_run: bool = False


@dataclass(frozen=True)
class DeploymentResult:
    success: bool
    provider: str
    target: str
    url: str
    file_count: int
    total_bytes: int
    dry_run: bool = False
    warnings: tuple[str, ...] = ()
