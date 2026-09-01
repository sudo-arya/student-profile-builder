"""Dynamic template registry."""
from pathlib import Path
from .template_manifest import TemplateManifest, check_compatibility, load_manifest
from .utils import BuilderError

Template = TemplateManifest  # Backwards-compatible public name.


def discover_templates(root: Path) -> dict[str, TemplateManifest]:
    found: dict[str, TemplateManifest] = {}
    if not root.is_dir(): return found
    for manifest_path in sorted(root.glob("*/template.yml")):
        item = load_manifest(manifest_path)
        if item.id in found: raise BuilderError(f"Duplicate template id: {item.id}")
        found[item.id] = item
    return found


class TemplateRegistry:
    def __init__(self, root: Path): self.root = root
    def discover(self) -> dict[str, TemplateManifest]: return discover_templates(self.root)
    def get(self, template_id: str, compatible: bool = True) -> TemplateManifest:
        item = selected_template(self.discover(), template_id)
        if compatible: check_compatibility(item)
        return item


def selected_template(templates: dict[str, TemplateManifest], template_id: str) -> TemplateManifest:
    if template_id not in templates:
        raise BuilderError(f'Configured template "{template_id}" was not found. Available: '
                           f'{", ".join(templates) or "none discovered"}.')
    return templates[template_id]
