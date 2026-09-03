from pathlib import Path
import json
import re
import shutil
import threading
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from profile_builder.template_tools import contribution_check, create_template, promote_template
from profile_builder.templates import TemplateRegistry
from profile_builder.workspace import (ensure_working_profile, git_safety_status,
                                       normalize_raw_profile, restore_default_profile,
                                       save_profile_text)
from profile_builder.gui import create_server
from profile_builder.builder import build_site
from profile_builder.profile import Profile, Theme, parse_profile, serialize_profile
from profile_builder.config import Config, load_config, save_config
from conftest import make_project


PROFILE = """---
name: Example Student
designation: Researcher
institute: Example Institute
sections: []
---
"""
REPOSITORY_ROOT = Path(__file__).parents[1]
PRODUCTION_TEMPLATES=("basic","basic-multipage","basic-hybrid",
                      "ta-arya-editorial","ta-balaji-tailwind","ta-krishna-sidebar","ta-yamini-research")


def project(tmp_path: Path) -> Path:
    (tmp_path / "defaults").mkdir()
    (tmp_path / "defaults/profile.default.md").write_text(PROFILE, encoding="utf-8")
    return tmp_path


def test_first_run_copies_default_but_never_overwrites_existing(tmp_path):
    root = project(tmp_path)
    assert ensure_working_profile(root).read_text(encoding="utf-8") == PROFILE
    (root / "profile.md").write_text(PROFILE.replace("Example Student", "Local Student"), encoding="utf-8")
    ensure_working_profile(root)
    assert "Local Student" in (root / "profile.md").read_text(encoding="utf-8")


def test_restore_keeps_bounded_backup_and_default_unchanged(tmp_path):
    root = project(tmp_path); ensure_working_profile(root)
    local = PROFILE.replace("Example Student", "Local Student")
    save_profile_text(root, local); restore_default_profile(root)
    assert (root / "profile.md").read_text(encoding="utf-8") == PROFILE
    assert "Local Student" in (root / "profile.md.bak").read_text(encoding="utf-8")
    assert (root / "defaults/profile.default.md").read_text(encoding="utf-8") == PROFILE


def test_gitignore_policy_and_gui_draft_contract():
    assert all(git_safety_status(REPOSITORY_ROOT).values())
    gui=(REPOSITORY_ROOT / "src/profile_builder/gui.py").read_text(encoding="utf-8")
    assert "beforeunload" in gui
    assert ".runtime/live-preview-" in gui
    assert "Unsaved preview" in gui
    assert "data-raw-draft" in gui


def test_dashboard_appearance_is_explicit_and_active_preview_opens_in_new_tab():
    gui=(REPOSITORY_ROOT/"src/profile_builder/gui.py").read_text(encoding="utf-8")
    assert "body=body.replace('<form method=\"post\" action=\"/appearance\">'" not in gui
    assert "draftBanner" not in gui
    assert "openPreview.href='/preview-window'" in gui
    assert "if(!draftActive)dirtyForm=null" in gui
    assert "previewController.abort()" in gui


def test_live_preview_window_and_incapable_template_disable_theme_switching(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT/"examples/profiles/minimal.md",root/"profile.md"); profile=parse_profile(root/"profile.md",root)
    serialize_profile(Profile(profile.data,profile.markdown,profile.html,profile.sections,Theme(True,"dark")),root/"profile.md",backup=False)
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/templates").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        assert "/api/build-status" in opener.open(base+"/preview-window").read().decode()
        assert "Professional single-page" not in page
        opener.open(Request(base+"/template/select",data=urlencode({"csrf":csrf,"id":"ta-arya-editorial"}).encode()))
        assert load_config(root/"config.yml").template=="ta-arya-editorial"
        assert parse_profile(root/"profile.md",root).theme==Theme(False,"dark")
        assert (root/"dist/index.html").is_file()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_production_templates_do_not_embed_demo_person_content_and_are_numbered():
    registry=TemplateRegistry(REPOSITORY_ROOT/"templates").discover()
    assert [item.name for item in registry.values()] == [f"Template {number}" for number in range(1,8)]
    for directory in (REPOSITORY_ROOT/"templates").iterdir():
        if not (directory/"template.yml").is_file(): continue
        source="\n".join(path.read_text(encoding="utf-8",errors="replace") for path in directory.rglob("*")
                         if path.is_file() and path.name!="README.md")
        for fixed in ("Aarya Mehta","Bharosa","Samvaad","example.edu"):
            assert fixed not in source, f"{directory.name} embeds demo content: {fixed}"
    assert "profile.photo" in (REPOSITORY_ROOT/"templates/basic/index.html.j2").read_text(encoding="utf-8")
    assert "profile.cv" in (REPOSITORY_ROOT/"templates/basic/index.html.j2").read_text(encoding="utf-8")
    assert 'profile.get("photo")' in (REPOSITORY_ROOT/"templates/basic-hybrid/build.py").read_text(encoding="utf-8")
    assert 'profile.get("cv")' in (REPOSITORY_ROOT/"templates/basic-multipage/build.py").read_text(encoding="utf-8")


def test_local_template_can_be_checked_and_promoted(tmp_path):
    root=project(tmp_path); ensure_working_profile(root)
    create_template(root,"sample","Sample","Template Author","jinja",location="local")
    assert contribution_check(root,"sample",local=True)
    target=promote_template(root,"sample")
    assert target == root / "templates/sample"
    assert TemplateRegistry(root / "templates").get("sample").author == "Template Author"


def test_contribution_check_rejects_working_profile_dependency(tmp_path):
    root=project(tmp_path); ensure_working_profile(root)
    folder=create_template(root,"unsafe","Unsafe","Template Author","jinja",location="local")
    (folder / "README.md").write_text("Read profile.md at runtime",encoding="utf-8")
    with pytest.raises(Exception,match="forbidden local dependency"):
        contribution_check(root,"unsafe",local=True)


def test_contributed_template_display_names_and_credits():
    registry=TemplateRegistry(REPOSITORY_ROOT / "templates")
    expected={"ta-arya-editorial":"Template 1","ta-balaji-tailwind":"Template 2",
              "ta-krishna-sidebar":"Template 3","ta-yamini-research":"Template 4"}
    for template_id,name in expected.items():
        item=registry.get(template_id)
        assert item.name == name
        assert item.author and f"Designed by {item.author}" in item.description


@pytest.mark.parametrize("template_id",PRODUCTION_TEMPLATES)
def test_canonical_default_builds_with_every_production_template(tmp_path,template_id):
    root=make_project(tmp_path); (root/"defaults").mkdir()
    shutil.copy2(REPOSITORY_ROOT/"defaults/profile.default.md",root/"defaults/profile.default.md")
    output=build_site(root,template_id=template_id,
                      profile_path=Path("defaults/profile.default.md"),
                      output_directory=root/".runtime/default-build"/template_id)
    assert (output/"index.html").is_file()


def test_raw_live_preview_is_isolated_and_invalid_draft_keeps_last_valid(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT / "examples/profiles/minimal.md",root / "profile.md")
    original=(root / "profile.md").read_text(encoding="utf-8")
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        valid=original.replace("Minimal Student","Unsaved Student")
        response=opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":valid}).encode())).read()
        assert json.loads(response)["valid"] is True
        assert (root / "profile.md").read_text(encoding="utf-8") == original
        assert (root / ".runtime/live-preview-1/index.html").is_file()
        structured={"csrf":csrf,"draft_kind":"profile","name":"Structured Draft",
                    "designation":"Student","department":"","institute":"Indian Institute of Technology Delhi",
                    "email":"","interests":"Reliable systems","link_github":"","link_linkedin":"",
                    "link_scholar":"","link_website":""}
        response=opener.open(Request(base+"/profile/structured-preview",data=urlencode(structured).encode())).read()
        assert json.loads(response)["valid"] is True
        assert "Structured Draft" in opener.open(base+"/live-site/").read().decode()
        assert (root / "profile.md").read_text(encoding="utf-8") == original
        invalid="---\nname: [broken\n---\n"
        response=opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":invalid}).encode())).read()
        assert json.loads(response)["valid"] is False
        assert (root / "profile.md").read_text(encoding="utf-8") == original
        status=json.loads(opener.open(base+"/api/build-status").read())
        assert status["live_error"] and status["preview_url"] == "/live-site/"
        assert status["mode"] == "invalid-draft"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_raw_editor_replaces_complete_profile_and_rebuilds_portfolio(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT/"examples/profiles/minimal.md",root/"profile.md")
    replacement=(REPOSITORY_ROOT/"examples/profiles/full.md").read_text(encoding="utf-8").replace("Asha Student","Replacement Student")
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        preview=json.loads(opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":replacement}).encode())).read())
        assert preview["valid"] is True and preview["unsaved"] is True
        assert "Replacement Student" in opener.open(base+"/live-site/").read().decode()
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":csrf}).encode())).read()
        assert (root/"profile.md").read_text(encoding="utf-8")==replacement
        saved=parse_profile(root/"profile.md",root)
        assert saved.data["name"]=="Replacement Student"
        assert [section.title for section in saved.sections]==["About","Education","Publications","Projects","Awards"]
        assert "Replacement Student" in (root/"dist/index.html").read_text(encoding="utf-8")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_raw_editor_repairs_missing_optional_media_before_complete_save(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT/"examples/profiles/minimal.md",root/"profile.md")
    replacement=(REPOSITORY_ROOT/"examples/profiles/full.md").read_text(encoding="utf-8")
    replacement=replacement.replace("assets/profile-placeholder.svg","assets/avatar-placeholder.png").replace('cv: ""','cv: assets/curriculum-vitae.pdf')
    normalized,warnings=normalize_raw_profile(root,replacement)
    assert 'photo: assets/profile-placeholder.svg' in normalized
    assert "cv: ''" in normalized
    assert len(warnings)==2
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        preview=json.loads(opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":replacement}).encode())).read())
        assert preview["valid"] is True and "was not found" in preview["warning"]
        assert preview["markdown"]==normalized
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":csrf}).encode())).read()
        saved=parse_profile(root/"profile.md",root)
        assert saved.data["photo"]=="assets/profile-placeholder.svg" and saved.data["cv"]==""
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_raw_editor_disables_theme_switching_for_selected_incapable_template(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT/"examples/profiles/minimal.md",root/"profile.md")
    config=load_config(root/"config.yml")
    save_config(root/"config.yml",Config("ta-arya-editorial",config.output_directory,config.preview_port))
    replacement_profile=parse_profile(REPOSITORY_ROOT/"examples/profiles/full.md",REPOSITORY_ROOT)
    candidate=root/"replacement.md"
    serialize_profile(Profile(replacement_profile.data,replacement_profile.markdown,replacement_profile.html,replacement_profile.sections,Theme(True,"dark")),candidate,backup=False,project_root=root)
    replacement=candidate.read_text(encoding="utf-8")
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        preview=json.loads(opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":replacement}).encode())).read())
        assert preview["valid"] is True
        assert "theme switching was disabled" in preview["warning"]
        assert "enabled: false" in preview["markdown"] and "default: dark" in preview["markdown"]
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":csrf}).encode())).read()
        saved=parse_profile(root/"profile.md",root)
        assert saved.theme==Theme(False,"dark")
        assert saved.data["name"]==replacement_profile.data["name"]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def multipart(fields):
    boundary="----profile-builder-live-preview-test"
    chunks=[]
    for name,value in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def test_structured_live_preview_accepts_browser_formdata_before_save(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT / "examples/profiles/minimal.md",root / "profile.md")
    original=(root / "profile.md").read_text(encoding="utf-8")
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        fields={"csrf":csrf,"draft_kind":"profile","name":"Browser FormData Draft",
                "designation":"Research Student","department":"","institute":"Indian Institute of Technology Delhi",
                "email":"","interests":"Live preview systems","link_github":"","link_linkedin":"",
                "link_scholar":"","link_website":"","photo_action":"keep"}
        body,content_type=multipart(fields)
        response=opener.open(Request(base+"/profile/structured-preview",data=body,headers={"Content-Type":content_type})).read()
        assert json.loads(response)["valid"] is True
        status=json.loads(opener.open(base+"/api/build-status").read())
        assert status["preview_url"] == "/live-site/"
        assert "Browser FormData Draft" in opener.open(base+"/live-site/").read().decode()
        assert (root / "profile.md").read_text(encoding="utf-8") == original
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":csrf}).encode()))
        assert "Browser FormData Draft" in (root / "profile.md").read_text(encoding="utf-8")
        assert "Browser FormData Draft" in (root / "dist/index.html").read_text(encoding="utf-8")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_structured_draft_protects_profile_and_dist_until_explicit_save(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT / "examples/profiles/minimal.md",root / "profile.md")
    build_site(root); saved=(root/"profile.md").read_bytes(); built=(root/"dist/index.html").read_bytes()
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        fields={"csrf":csrf,"draft_kind":"profile","name":"Only In Draft","designation":"Student",
                "department":"","institute":"Indian Institute of Technology Delhi","email":"",
                "interests":"Safety","link_github":"","link_linkedin":"","link_scholar":"","link_website":""}
        opener.open(Request(base+"/profile/structured-preview",data=urlencode(fields).encode()))
        assert b"Only In Draft" in opener.open(base+"/live-site/").read()
        assert (root/"profile.md").read_bytes()==saved
        assert (root/"dist/index.html").read_bytes()==built
        status=json.loads(opener.open(base+"/api/build-status").read())
        assert status["mode"]=="draft" and status["dirty"] is True
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_draft_save_detects_external_profile_change(tmp_path):
    root=make_project(tmp_path); shutil.copy2(REPOSITORY_ROOT / "examples/profiles/minimal.md",root / "profile.md")
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); csrf=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        saved=(root/"profile.md").read_text(encoding="utf-8")
        draft=saved.replace("Minimal Student","Browser Draft")
        opener.open(Request(base+"/profile/raw-preview",data=urlencode({"csrf":csrf,"markdown":draft}).encode()))
        external=saved.replace("Minimal Student","External Editor")
        save_profile_text(root,external)
        with pytest.raises(HTTPError) as error:
            opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":csrf}).encode()))
        assert error.value.code==400 and "External Editor" in (root/"profile.md").read_text(encoding="utf-8")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
