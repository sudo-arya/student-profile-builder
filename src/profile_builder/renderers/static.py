from pathlib import Path
from typing import Any
import json
import shutil
from ..template_manifest import TemplateManifest


class StaticRenderer:
    def build(self, template: TemplateManifest, context: dict[str, Any], output: Path) -> None:
        shutil.copytree(template.directory / (template.source_directory or ""), output, dirs_exist_ok=True)
        (output / "profile-data.json").write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
