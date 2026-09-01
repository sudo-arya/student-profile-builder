from pathlib import Path
from typing import Any
import shutil
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from ..template_manifest import TemplateManifest


class JinjaRenderer:
    def build(self, template: TemplateManifest, context: dict[str, Any], output: Path) -> None:
        env = Environment(loader=FileSystemLoader(template.directory), undefined=StrictUndefined,
                          autoescape=select_autoescape(["html", "xml"]))
        rendered = env.get_template(template.entry or "").render(**context)
        (output / "index.html").write_text(rendered, encoding="utf-8")
        if template.static_directory:
            shutil.copytree(template.directory / template.static_directory,
                            output / "assets" / "template", dirs_exist_ok=True)
