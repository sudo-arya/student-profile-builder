from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

from .utils import BuilderError, confined_path


@dataclass(frozen=True)
class Config:
    template: str = "basic"
    output_directory: str = "dist"
    preview_port: int = 8000

    @property
    def as_dict(self) -> dict[str, Any]:
        return {"template": self.template, "output_directory": self.output_directory,
                "preview": {"port": self.preview_port}}


def load_config(path: Path) -> Config:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise BuilderError(f"Unable to read configuration: {exc}") from exc
    if not isinstance(raw, dict):
        raise BuilderError("Configuration must be a YAML mapping.")
    preview = raw.get("preview", {})
    if not isinstance(preview, dict):
        raise BuilderError('Configuration field "preview" must be a mapping.')
    try:
        port = int(preview.get("port", 8000))
    except (TypeError, ValueError) as exc:
        raise BuilderError("Preview port must be a number.") from exc
    if not 1 <= port <= 65535:
        raise BuilderError("Preview port must be between 1 and 65535.")
    config = Config(str(raw.get("template", "basic")),
                    str(raw.get("output_directory", "dist")), port)
    output = confined_path(path.parent, config.output_directory, "Output directory")
    protected = {"assets", "templates", "src", "tests", "docs", ".git", ".venv"}
    relative = output.relative_to(path.parent.resolve())
    if relative.parts and relative.parts[0].lower() in protected:
        raise BuilderError(f'Output directory cannot be inside protected source folder "{relative.parts[0]}".')
    return config


def save_config(path: Path, config: Config) -> None:
    path.write_text(yaml.safe_dump(config.as_dict, sort_keys=False), encoding="utf-8")
