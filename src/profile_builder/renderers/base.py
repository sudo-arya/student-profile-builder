from pathlib import Path
from typing import Any, Protocol
from ..template_manifest import TemplateManifest
from ..utils import BuilderError


class Renderer(Protocol):
    def build(self, template: TemplateManifest, context: dict[str, Any], output: Path) -> None: ...


def renderer_for(engine: str) -> Renderer:
    if engine == "jinja":
        from .jinja import JinjaRenderer
        return JinjaRenderer()
    if engine == "static":
        from .static import StaticRenderer
        return StaticRenderer()
    if engine == "external-build":
        from .external import ExternalBuildRenderer
        return ExternalBuildRenderer()
    raise BuilderError(f'No renderer is available for engine "{engine}".')
