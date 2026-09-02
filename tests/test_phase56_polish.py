from pathlib import Path
from urllib.request import build_opener, ProxyHandler
import json
import shutil
import threading

import pytest

from conftest import ROOT, make_project
from profile_builder.builder import build_site, validate_output
from profile_builder.config import Config
from profile_builder.deployment.manifest import collect_files
from profile_builder.gui import create_server
from profile_builder.template_tools import check_template


def project(tmp_path: Path) -> Path:
    root=make_project(tmp_path); shutil.copy(ROOT/"examples/profiles/full.md",root/"profile.md"); return root


@pytest.mark.parametrize("template",["basic","basic-multipage","basic-hybrid"])
def test_reference_templates_conform_and_keep_sections(template,tmp_path):
    root=project(tmp_path); output=build_site(root,Config(),template_id=template)
    assert (output/"index.html").is_file() and not validate_output(output)
    assert (output/"favicon.svg").is_file() and any("favicon.svg" in p.read_text(encoding="utf-8") for p in output.rglob("*.html"))
    assert any("template-check" not in line for line in check_template(root,template))
    combined="\n".join(p.read_text(encoding="utf-8") for p in output.rglob("*.html"))
    assert "About" in combined


def test_multipage_tree_and_manifest_are_subpath_safe(tmp_path):
    root=project(tmp_path); output=build_site(root,Config(),template_id="basic-multipage")
    pages={p.relative_to(output).as_posix() for p in output.rglob("*.html")}
    files,_=collect_files(output)
    assert "index.html" in pages and len(pages)>2 and pages<=set(files)
    for page in output.rglob("*.html"):
        text=page.read_text(encoding="utf-8")
        assert 'href="/' not in text and 'src="/' not in text


def test_gui_health_and_visual_semantics(tmp_path):
    root=project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); base=f"http://127.0.0.1:{server.server_port}"; opener=build_opener(ProxyHandler({}))
    try:
        health=json.loads(opener.open(base+"/api/health").read())
        assert health=={"application":"student-profile-builder","status":"ok"}
        dashboard=opener.open(base+"/").read().decode(); profile=opener.open(base+"/profile").read().decode(); gallery=opener.open(base+"/templates").read().decode()
        assert "--surface" in dashboard and "aria-current" in dashboard and "primary" in dashboard and "danger" in profile
        assert "<details>" in profile and "Profile Media" in profile and "Choose Photo" in profile and "Markdown help" in profile
        assert 'class="badge">Previewing' in gallery and "Available" in gallery and "Draft Template Preview" in gallery
        assert opener.open(base+"/favicon.ico").status==200
    finally: server.shutdown(); server.server_close(); thread.join()
