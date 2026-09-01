"""Serialization boundary shared by every renderer."""
from datetime import datetime, timezone
from typing import Any
from . import __version__
from .profile import Profile
from .template_manifest import PROFILE_SCHEMA_VERSION, TemplateManifest


def create_context(profile: Profile, template: TemplateManifest) -> dict[str, Any]:
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile": dict(profile.data),
        "theme": {"enabled": profile.theme.enabled, "default": profile.theme.default},
        "sections": [{"id": section.id, "title": section.title, "type": section.type,
                      "visible": section.visible, "order": section.order,
                      "markdown": section.markdown, "html": section.html}
                     for section in profile.sections if section.visible],
        "content": {"markdown": profile.markdown, "html": profile.html},
        "site": {"generator": f"Student Profile Builder {__version__}", "icon": profile.data.get("icon", ""),
                 "template_id": template.id, "template_name": template.name,
                 "template_version": template.version,
                 "generated_at": datetime.now(timezone.utc).isoformat()},
    }
