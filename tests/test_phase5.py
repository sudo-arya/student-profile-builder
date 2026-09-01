from pathlib import Path
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from urllib.error import HTTPError
from urllib.parse import urlencode
import re
import shutil
import threading
import pytest
import yaml

from conftest import ROOT, make_project
from profile_builder.builder import build_site, validate_output
from profile_builder.build_state import build_status
from profile_builder.config import Config
from profile_builder.deployment.manifest import collect_files
from profile_builder.gui import GUI_HOST, create_server
from profile_builder.profile import Profile, Section, Theme, _render, parse_profile, serialize_profile
from profile_builder.utils import BuilderError


def project(tmp_path):
    root=make_project(tmp_path); shutil.copy(ROOT/"examples/profiles/full.md",root/"profile.md"); return root


def section(sid,title,content="Text",visible=True,order=10,kind="custom"):
    return Section(sid,title,kind,visible,order,content,_render(content))


def test_legacy_headings_normalize_in_order(tmp_path):
    path=tmp_path/"profile.md"; path.write_text("---\nname: A\ndesignation: B\ninstitute: C\n---\n# Research\nR\n# About\nA",encoding="utf-8")
    profile=parse_profile(path)
    assert [s.id for s in profile.sections]==["research","about"]


def test_arbitrary_hidden_and_optional_sections(tmp_path):
    path=tmp_path/"profile.md"; path.write_text("""---
name: A
designation: B
institute: C
sections:
- id: teaching
  title: "शिक्षण & Teaching"
  type: custom
  visible: true
  order: 20
  content: "**Course**"
- id: hidden
  title: Hidden
  type: news
  visible: false
  order: 10
  content: Secret
---
""",encoding="utf-8")
    p=parse_profile(path)
    assert [s.id for s in p.sections]==["hidden","teaching"]
    assert "Secret" not in p.html and "Course" in p.html
    assert not any(s.type in {"publications","projects","awards"} for s in p.sections)


def test_duplicate_section_id_rejected(tmp_path):
    path=tmp_path/"profile.md"; path.write_text("---\nname: A\ndesignation: B\ninstitute: C\nsections:\n- {id: same, title: One}\n- {id: same, title: Two}\n---\n",encoding="utf-8")
    with pytest.raises(BuilderError,match="Duplicate section ID"): parse_profile(path)


def test_round_trip_unicode_markdown_theme_and_order(tmp_path):
    path=tmp_path/"profile.md"; base={"name":"अनन्या","designation":"PhD","institute":"IIT Delhi","links":{"github":"https://github.com/a"},"research_interests":["AI"]}
    original=Profile(base,"","",(section("two","Deux","`code`",order=20),section("one","एक","**bold**",order=10)),Theme(True,"dark"))
    serialize_profile(original,path,backup=False); parsed=parse_profile(path)
    assert parsed.data["name"]=="अनन्या" and parsed.theme==Theme(True,"dark")
    assert [s.id for s in parsed.sections]==["two","one"] and parsed.sections[1].markdown=="**bold**"


@pytest.mark.parametrize("default",["light","dark","system"])
def test_theme_enabled_basic(default,tmp_path):
    root=project(tmp_path); p=parse_profile(root/"profile.md",root)
    serialize_profile(Profile(p.data,p.markdown,p.html,p.sections,Theme(True,default)),root/"profile.md",backup=False)
    html=(build_site(root)/"index.html").read_text(encoding="utf-8")
    assert 'data-theme-choice="light"' in html and f'data-theme="{default}"' in html
    css=(root/"dist/assets/template/css/style.css").read_text(); assert 'data-theme="light"' in css and 'data-theme="dark"' in css


@pytest.mark.parametrize("default",["light","dark","system"])
def test_theme_disabled_locks_configured_appearance_without_storage(default,tmp_path):
    root=project(tmp_path); p=parse_profile(root/"profile.md",root)
    serialize_profile(Profile(p.data,p.markdown,p.html,p.sections,Theme(False,default)),root/"profile.md",backup=False)
    html=(build_site(root)/"index.html").read_text(encoding="utf-8")
    assert "data-theme-choice" not in html and f'data-theme="{default}"' in html
    assert "localStorage" not in html and "main.js" not in html
    css=(root/"dist/assets/template/css/style.css").read_text()
    assert 'data-theme="system"' in css and "prefers-color-scheme: dark" in css


def test_invalid_theme_and_unsupported_template(tmp_path):
    root=project(tmp_path); text=(root/"profile.md").read_text().replace("---\n# About","theme:\n  enabled: true\n  default: invalid\n---\n# About",1); (root/"profile.md").write_text(text)
    with pytest.raises(BuilderError,match="Theme default"): parse_profile(root/"profile.md",root)


def test_theme_enabled_blocks_incapable_template(tmp_path):
    root=project(tmp_path); p=parse_profile(root/"profile.md",root)
    serialize_profile(Profile(p.data,p.markdown,p.html,p.sections,Theme(True,"system")),root/"profile.md",backup=False)
    shutil.copytree(ROOT/"examples/templates/static-example",root/"templates/static-example")
    with pytest.raises(BuilderError,match="does not support light/dark"):
        build_site(root,Config(),template_id="static-example")


def test_multi_page_static_output_and_manifest(tmp_path):
    root=project(tmp_path); folder=root/"templates/multi"; (folder/"site/projects").mkdir(parents=True)
    (folder/"template.yml").write_text("id: multi\nname: Multi\nversion: '1'\ndescription: Multi page\nengine: static\nsource_directory: site\n")
    (folder/"site/index.html").write_text('<a href="./projects/">Projects</a>')
    (folder/"site/projects/index.html").write_text('<a href="../index.html">Home</a>')
    output=build_site(root,Config(),template_id="multi")
    files,_=collect_files(output)
    assert "index.html" in files and "projects/index.html" in files and validate_output(output)==[]


def test_gui_home_profile_add_theme_and_build(tmp_path):
    root=project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f"http://{GUI_HOST}:{server.server_port}"
    try:
        opener=build_opener(ProxyHandler({}))
        home=opener.open(base+"/").read().decode(); assert "Student Profile Builder" in home and "password" in home.lower()
        page=opener.open(base+"/profile").read().decode(); token=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        data=urlencode({"csrf":token,"title":"Teaching","type":"teaching","visible":"on","content":"# Course"}).encode()
        assert opener.open(Request(base+"/section/add",data=data)).status==200
        page=opener.open(base+"/profile").read().decode(); assert "Teaching" in page
        save={"csrf":token,"name":"GUI Student","designation":"PhD","institute":"IIT Delhi","theme_enabled":"on","theme_default":"system"}
        assert opener.open(Request(base+"/profile/save",data=urlencode(save).encode())).status==200
        assert parse_profile(root/"profile.md",root).theme.enabled
        assert opener.open(Request(base+"/build",data=urlencode({"csrf":token}).encode())).status==200
        assert (root/"dist/index.html").is_file() and (root/"profile.md.bak").is_file()
    finally: server.shutdown(); server.server_close(); thread.join()


def test_gui_localhost_and_no_credential_fields(tmp_path):
    root=project(tmp_path); server=create_server(root,0)
    try:
        assert server.server_address[0]=="127.0.0.1"
        thread=threading.Thread(target=server.handle_request); thread.start(); page=build_opener(ProxyHandler({})).open(f"http://127.0.0.1:{server.server_port}/").read().decode(); thread.join()
        assert 'type="password"' not in page and 'name="token"' not in page
    finally: server.server_close()


def gui_client(root):
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    return server,thread,build_opener(ProxyHandler({})),f"http://127.0.0.1:{server.server_port}"


def csrf(opener,base,path="/"):
    page=opener.open(base+path).read().decode(); return re.search(r'name="csrf" value="([^"]+)',page).group(1),page


def tree_bytes(root):
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_gui_and_core_build_parity_and_styled_assets(tmp_path):
    root=project(tmp_path); direct=root/"direct-output"; build_site(root,output_directory=direct)
    server,thread,opener,base=gui_client(root)
    try:
        token,_=csrf(opener,base); opener.open(Request(base+"/build",data=urlencode({"csrf":token}).encode()))
        assert tree_bytes(direct)==tree_bytes(root/"dist")
        css=opener.open(base+"/site/assets/template/css/style.css").read().decode()
        assert "profile-header" in css and opener.open(base+"/site/").status==200
    finally: server.shutdown(); server.server_close(); thread.join()


def test_preview_rebuilds_after_profile_change_and_updates_state(tmp_path):
    root=project(tmp_path); build_site(root); assert build_status(root,"basic",root/"dist")[0]
    path=root/"profile.md"; original=parse_profile(path,root); data=dict(original.data); data["name"]="Fresh Preview Name"; serialize_profile(Profile(data,original.markdown,original.html,original.sections,original.theme),path,backup=False)
    assert not build_status(root,"basic",root/"dist")[0]
    server,thread,opener,base=gui_client(root)
    try:
        page=opener.open(base+"/preview").read().decode(); assert "Saved website rebuilt" in page and "Choose a template" not in page
        assert "Fresh Preview Name" in opener.open(base+"/site/").read().decode()
        assert build_status(root,"basic",root/"dist")[0]
    finally: server.shutdown(); server.server_close(); thread.join()


def test_preview_is_one_stable_session_with_status_api(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        page=opener.open(base+"/preview").read().decode()
        assert "/api/build-status" in page and "setInterval" in page and "profile-preview-mode" in page
        status=yaml.safe_load(opener.open(base+"/api/build-status").read())
        assert status["current"] is True and status["fingerprint"]
    finally: server.shutdown(); server.server_close(); thread.join()


def multipart(fields,files):
    boundary="----profile-builder-test"; chunks=[]
    for name,value in fields.items(): chunks += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()]
    for name,(filename,kind,data) in files.items(): chunks += [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {kind}\r\n\r\n".encode()+data+b"\r\n"]
    chunks += [f"--{boundary}--\r\n".encode()]
    return b"".join(chunks),f"multipart/form-data; boundary={boundary}"


def test_gui_imports_photo_and_cv_to_safe_managed_names(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        token,_=csrf(opener,base,"/profile"); p=parse_profile(root/"profile.md",root)
        fields={"csrf":token,"name":p.data["name"],"designation":p.data["designation"],"department":p.data["department"],"institute":p.data["institute"],"email":p.data["email"],"interests":"AI"}
        body,kind=multipart(fields,{"photo_file":("../../evil.png","image/png",b"\x89PNG\r\n\x1a\ncontent"),"cv_file":("resume.pdf","application/pdf",b"%PDF-1.4\ncontent")})
        opener.open(Request(base+"/profile/save",data=body,headers={"Content-Type":kind}))
        saved=parse_profile(root/"profile.md",root)
        assert re.fullmatch(r"assets/managed/photo-[0-9a-f]{16}\.png",saved.data["photo"])
        assert re.fullmatch(r"assets/managed/cv-[0-9a-f]{16}\.pdf",saved.data["cv"])
        assert (root/saved.data["photo"]).is_file() and (root/saved.data["cv"]).is_file()
    finally: server.shutdown(); server.server_close(); thread.join()


def test_gui_can_replace_upload_with_default_placeholder_without_hiding_photo(tmp_path):
    root=project(tmp_path); managed=root/"assets/managed/photo-0123456789abcdef.jpg"; managed.parent.mkdir(parents=True,exist_ok=True); managed.write_bytes(b"old upload")
    current=parse_profile(root/"profile.md",root); data=dict(current.data); data["photo"]="assets/managed/photo-0123456789abcdef.jpg"
    serialize_profile(Profile(data,current.markdown,current.html,current.sections,current.theme),root/"profile.md",backup=False)
    server,thread,opener,base=gui_client(root)
    try:
        token,page=csrf(opener,base,"/profile")
        assert "Remove upload and use default placeholder" in page and "Hide photo entirely" in page
        p=parse_profile(root/"profile.md",root); payload={"csrf":token,"name":p.data["name"],"designation":p.data["designation"],"department":p.data["department"],"institute":p.data["institute"],"email":p.data["email"],"interests":"AI","photo_action":"placeholder"}
        opener.open(Request(base+"/profile/save",data=urlencode(payload).encode()))
        saved=parse_profile(root/"profile.md",root)
        assert saved.data["photo"]=="assets/profile-placeholder.svg" and not managed.exists()
        assert "assets/user/profile-placeholder.svg" in opener.open(base+"/site/").read().decode()
    finally: server.shutdown(); server.server_close(); thread.join()


def test_dashboard_separates_theme_capability_and_setting(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        page=opener.open(base+"/").read().decode()
        assert "Template supports theme switching: <strong>Yes" in page and "Visitor theme control: <strong>Off" in page
        assert "Site appearance: <strong>System" in page
    finally: server.shutdown(); server.server_close(); thread.join()


def test_duplicate_delete_and_undo_section(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        token,page=csrf(opener,base,"/profile"); first=parse_profile(root/"profile.md",root).sections[0]
        payload={"csrf":token,"id":first.id,"action":"duplicate","title":first.title,"type":first.type,"content":first.markdown}
        opener.open(Request(base+"/section/action",data=urlencode(payload).encode()))
        p=parse_profile(root/"profile.md",root); copy=next(s for s in p.sections if s.title.endswith(" Copy"))
        response=opener.open(Request(base+"/section/action",data=urlencode({"csrf":token,"id":copy.id,"action":"delete"}).encode())).read().decode(); assert "Undo delete" in response
        opener.open(Request(base+"/section/undo",data=urlencode({"csrf":token}).encode()))
        assert any(s.id==copy.id for s in parse_profile(root/"profile.md",root).sections)
    finally: server.shutdown(); server.server_close(); thread.join()


def test_template_preview_does_not_change_selection(tmp_path):
    root=project(tmp_path); shutil.copytree(ROOT/"examples/templates/static-example",root/"templates/static-example")
    server,thread,opener,base=gui_client(root)
    try:
        token,_=csrf(opener,base,"/templates"); opener.open(Request(base+"/template/preview",data=urlencode({"csrf":token,"id":"static-example"}).encode()))
        assert Config().template=="basic" and yaml.safe_load((root/"config.yml").read_text())["template"]=="basic"
    finally: server.shutdown(); server.server_close(); thread.join()


def test_publish_page_has_integrated_forms_without_credentials(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        page=opener.open(base+"/publish").read().decode().lower()
        assert 'action="/deploy/iitd"' in page and 'action="/deploy/github"' in page
        assert 'type="password"' not in page and 'name="token"' not in page and "pat" in page
    finally: server.shutdown(); server.server_close(); thread.join()


def test_export_contains_only_profile_config_and_assets(tmp_path):
    root=project(tmp_path); server,thread,opener,base=gui_client(root)
    try:
        data=opener.open(base+"/export").read(); import io,zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names=archive.namelist()
        assert "profile.md" in names and "config.yml" in names and any(n.startswith("assets/") for n in names)
        assert not any(n.startswith(("dist/",".venv/")) for n in names)
    finally: server.shutdown(); server.server_close(); thread.join()


def test_gui_port_collision_is_not_silent(tmp_path):
    root=project(tmp_path); first=create_server(root,0)
    thread=threading.Thread(target=first.serve_forever,daemon=True); thread.start()
    try:
        with pytest.raises(OSError): create_server(root,first.server_port)
    finally: first.shutdown(); first.server_close(); thread.join()
