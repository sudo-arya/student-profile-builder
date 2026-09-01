from pathlib import Path
import shutil
import tempfile
import yaml
from .builder import build_site
from .config import Config
from .renderers import renderer_for
from .template_manifest import PROFILE_SCHEMA_VERSION, TemplateManifest, check_compatibility
from .templates import TemplateRegistry
from .utils import BuilderError


def format_info(item: TemplateManifest) -> str:
    lines = [f"Template: {item.name}", f"ID: {item.id}", f"Version: {item.version}",
             f"Author: {item.author or '(not specified)'}", f"Engine: {item.engine}", "",
             "Description:", item.description, "", "Requirements:"]
    lines.extend(f"- {name}" for name in item.executables)
    if not item.executables: lines.append("- none")
    lines += ["", "Profile schema:"] + [f"- {value}" for value in item.profile_schemas]
    if item.engine == "external-build":
        lines += ["", f"Build command: {' '.join(item.build.command)}",
                  f"Build output: {item.build.output_directory}"]
    return "\n".join(lines)


def check_template(root: Path, template_id: str, profile: Path | None = None) -> list[str]:
    checks: list[str] = []
    item = TemplateRegistry(root / "templates").get(template_id, compatible=False)
    checks.append("[OK] template.yml valid")
    check_compatibility(item); checks.append(f"[OK] profile schema {PROFILE_SCHEMA_VERSION} compatible")
    renderer_for(item.engine); checks.append(f"[OK] {item.engine} renderer available")
    if item.engine == "external-build":
        missing = [name for name in item.executables if shutil.which(name) is None]
        if missing: raise BuilderError(f"Required executable missing: {', '.join(missing)}")
    with tempfile.TemporaryDirectory(dir=root, prefix=".template-check-") as temporary:
        output = Path(temporary) / "output"
        build_site(root, Config(template=item.id), template_id=item.id,
                   profile_path=profile or Path("profile.md"), output_directory=output)
        checks += ["[OK] build succeeded", "[OK] index.html generated",
                   "[OK] output paths and relative URLs valid"]
    return checks


def create_template(root: Path, template_id: str, name: str, author: str, engine: str) -> Path:
    from .template_manifest import ENGINES, ID_PATTERN
    if not ID_PATTERN.fullmatch(template_id): raise BuilderError("Template ID must use lowercase letters, numbers, and hyphens.")
    if engine not in ENGINES: raise BuilderError(f"Engine must be one of: {', '.join(sorted(ENGINES))}.")
    folder = root / "templates" / template_id
    if folder.exists(): raise BuilderError(f"Template already exists: {template_id}")
    folder.mkdir(parents=True)
    manifest = {"manifest_version": "1.0", "id": template_id, "name": name, "version": "0.1.0",
                "author": author, "description": "TODO: describe this template.", "engine": engine,
                "compatibility": {"profile_schema": ["1.0"]},
                "capabilities": {"profile_photo": True, "research_interests": True,
                                 "social_links": True, "markdown_content": True}}
    if engine == "jinja":
        manifest.update({"entry": "index.html.j2", "static_directory": "static"})
        (folder / "static").mkdir()
        (folder / "index.html.j2").write_text("<!doctype html>\n<title>{{ profile.name }}</title>\n<main>{{ content.html | safe }}</main>\n", encoding="utf-8")
    elif engine == "static":
        manifest["source_directory"] = "site"
        site = folder / "site"; site.mkdir()
        (site / "index.html").write_text("<!doctype html><title>Profile</title><main id=profile></main><script src=app.js></script>", encoding="utf-8")
        (site / "app.js").write_text("fetch('./profile-data.json').then(r=>r.json()).then(d=>{document.querySelector('#profile').textContent=d.profile.name})", encoding="utf-8")
    else:
        manifest["requirements"] = {"executables": ["npm"]}
        manifest["build"] = {"command": ["npm", "run", "build"], "output_directory": "dist",
                             "data_file": "public/profile-data.json"}
    (folder / "template.yml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (folder / "README.md").write_text(f"# {name}\n\nStarter only. Complete the template, then run `python manage.py template-check {template_id}`.\n", encoding="utf-8")
    return folder
