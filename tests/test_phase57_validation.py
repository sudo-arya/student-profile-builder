from pathlib import Path
from urllib.parse import urlencode
from urllib.request import build_opener,ProxyHandler,Request
import json
import shutil
import threading

import pytest

from conftest import ROOT,make_project
from profile_builder.builder import build_site
from profile_builder.cli import main
from profile_builder.deployment.iitd import IITDDeploymentProvider
from profile_builder.deployment.iitd import _remote_script,check_reachability
from profile_builder.deployment.models import IITDTarget
from profile_builder.deployment.ssh import CommandResult
from profile_builder.gui import create_server
from profile_builder.mutations import import_asset_bytes,normalize_web_url,update_profile_fields
from profile_builder.profile import Profile,_render,parse_profile,serialize_profile
from profile_builder.utils import BuilderError


def project(tmp_path):
    root=make_project(tmp_path); shutil.copy(ROOT/"examples/profiles/full.md",root/"profile.md"); return root


@pytest.mark.parametrize(("value","expected"),[("",""),("https://example.com","https://example.com"),("http://example.com","http://example.com"),("github.com/user","https://github.com/user"),("abc","abc"),("javascript:alert(1)","javascript:alert(1)")])
def test_url_normalization_is_conservative(value,expected): assert normalize_web_url(value)==expected


def test_invalid_shared_mutation_is_transactional(tmp_path):
    root=project(tmp_path); before=(root/"profile.md").read_bytes()
    with pytest.raises(BuilderError,match="Invalid Github URL"): update_profile_fields(root,{"github":"abc"})
    assert (root/"profile.md").read_bytes()==before
    updated=update_profile_fields(root,{"github":"github.com/student"})
    assert updated.data["links"]["github"]=="https://github.com/student"


def test_failed_serialized_candidate_leaves_source_untouched(tmp_path):
    root=project(tmp_path); path=root/"profile.md"; before=path.read_bytes(); profile=parse_profile(path,root); data=dict(profile.data); data["links"]={"github":"javascript:bad"}
    with pytest.raises(BuilderError): serialize_profile(Profile(data,profile.markdown,profile.html,profile.sections,profile.theme),path)
    assert path.read_bytes()==before and not list(root.glob(".profile.md.*.tmp"))


def test_manual_corruption_keeps_gui_shell_and_recovery(tmp_path):
    root=project(tmp_path); shutil.copy(root/"profile.md",root/"profile.md.bak"); text=(root/"profile.md").read_text(); (root/"profile.md").write_text(text.replace('https://github.com/example','bad-value'))
    server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/").read().decode(); edit=opener.open(base+"/profile").read().decode()
        assert "Profile needs attention" in page and "Dashboard" in page and "Templates" in page
        assert "Repair mode" in edit and 'type="url"' in edit
    finally: server.shutdown();server.server_close();thread.join()


def test_invalid_gui_url_never_modifies_profile(tmp_path):
    root=project(tmp_path); before=(root/"profile.md").read_bytes(); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();opener=build_opener(ProxyHandler({}));base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); import re; token=re.search(r'name="csrf" value="([^"]+)',page).group(1); p=parse_profile(root/"profile.md",root)
        payload={"csrf":token,"name":p.data["name"],"designation":p.data["designation"],"institute":p.data["institute"],"link_github":"abc"}
        response=opener.open(Request(base+"/profile/save",data=urlencode(payload).encode())).read().decode()
        assert "Invalid Github URL" in response and "Edit Profile" in response and (root/"profile.md").read_bytes()==before
    finally: server.shutdown();server.server_close();thread.join()


def test_cli_invalid_url_uses_same_transaction(tmp_path,monkeypatch,capsys):
    root=project(tmp_path); before=(root/"profile.md").read_bytes(); monkeypatch.chdir(root)
    assert main(["profile","set","github","abc"])==2
    assert (root/"profile.md").read_bytes()==before and "Invalid Github URL" in capsys.readouterr().err


def test_markdown_academic_features_and_sanitization():
    html=_render("""# Heading\n\n**bold** *italic* `code`\n\n- one\n  - nested\n\n| Year | Degree |\n|---|---|\n| 2026 | PhD |\n\n```python\nprint('ok')\n```\n\n> quote\n\n---\n<script>alert(1)</script>""")
    for tag in ("<table>","<th>","<td>","<pre>","<code","<blockquote>","<hr") : assert tag in html
    assert "<script" not in html


def test_custom_icon_context_and_favicon(tmp_path):
    root=project(tmp_path); icon=import_asset_bytes(root,"icon",b"\x89PNG\r\n\x1a\nsmall"); update_profile_fields(root,{"icon":icon}); output=build_site(root)
    assert "site-icon-" in (output/"index.html").read_text() and (output/icon.replace("assets/","assets/user/")).is_file()


def test_private_url_is_http(): assert IITDTarget.PRIVATE.url("student")=="http://privateweb.iitd.ac.in/~student/"


def test_network_preflight_is_credential_free_and_friendly():
    class Connection:
        def close(self): pass
    calls=[]; check_reachability(lambda address,timeout:(calls.append((address,timeout)) or Connection()))
    assert calls==[(('ssh1.iitd.ac.in',22),5)]
    with pytest.raises(BuilderError,match="campus/VPN"):
        check_reachability(lambda *_args,**_kwargs:(_ for _ in ()).throw(OSError("offline")))


def test_realistic_staging_cleanup_leaves_stage_before_recursive_remove():
    files=["index.html","favicon.svg",".hidden",".profile-builder-manifest.json","assets/css/style.css","assets/js/main.js","assets/user/photo.png","README.md"]
    script=_remote_script("private_html",".student-profile-builder-upload-0123456789abcdef0123456789abcdef",files,[])
    assert script.index('cd "$HOME"')<script.index('rm -rf -- "$stage"')
    assert 'rm -rf -- "$target"' not in script and all(f'"$stage"/{name}' in script for name in files)


class RetryRunner:
    connection_options=()
    def __init__(self): self.calls=0
    def check_tools(self): return "ssh","scp"
    def run(self,args,*,capture=False): self.calls+=1; return CommandResult(255 if self.calls==1 else 0,'{"manifest_version":"1.0","files":[]}' if self.calls==2 else "")


def test_retry_is_bounded_and_does_not_handle_passwords(tmp_path):
    root=project(tmp_path); output=build_site(root); runner=RetryRunner(); from profile_builder.deployment.models import DeploymentRequest
    result=IITDDeploymentProvider(runner,status=lambda _:None,retries=1).deploy(DeploymentRequest(output,"student",IITDTarget.PUBLIC))
    assert result.success and runner.calls==4


def test_isolated_template_preview_state_machine(tmp_path):
    root=project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();opener=build_opener(ProxyHandler({}));base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/preview").read().decode(); import re
        assert "Choose a template" not in page and "Responsive Preview" in page
        templates=opener.open(base+"/templates").read().decode()
        token=re.search(r'name="csrf" value="([^"]+)',templates).group(1)
        assert "Choose a template" in templates and "Draft Template Preview" in templates
        opener.open(Request(base+"/template/preview",data=urlencode({"csrf":token,"id":"basic-sidebar"}).encode()))
        assert "<aside>" in opener.open(base+"/draft-site/").read().decode()
        # A rapid serve/rebuild cycle must never expose a half-deleted draft on Windows.
        for _ in range(3):
            opener.open(Request(base+"/template/preview",data=urlencode({"csrf":token,"id":"basic-sidebar"}).encode()))
            assert "<aside>" in opener.open(base+"/draft-site/").read().decode()
        assert "<aside>" not in opener.open(base+"/site/").read().decode()
        # Leaving Templates restores the main site from the stored template.
        opener.open(base+"/profile"); assert "<aside>" not in opener.open(base+"/site/").read().decode()
        templates=opener.open(base+"/templates").read().decode()
        assert 'class="badge">Previewing' in templates
        opener.open(Request(base+"/template/preview",data=urlencode({"csrf":token,"id":"basic-sidebar"}).encode()))
        opener.open(Request(base+"/template/select",data=urlencode({"csrf":token,"id":"basic-sidebar"}).encode()))
        assert "<aside>" in opener.open(base+"/site/").read().decode()
        assert "Choose a template" not in opener.open(base+"/preview").read().decode()
        from profile_builder.config import load_config
        assert load_config(root/"config.yml").template=="basic-sidebar"
    finally: server.shutdown();server.server_close();thread.join()


def test_gui_serializes_live_preview_reads_with_rebuilds(tmp_path, monkeypatch):
    root=project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();opener=build_opener(ProxyHandler({}));base=f"http://127.0.0.1:{server.server_port}"
    started=threading.Event(); release=threading.Event(); blocked=False; original_read=Path.read_bytes
    try:
        page=opener.open(base+"/").read().decode(); import re
        token=re.search(r'name="csrf" value="([^"]+)',page).group(1)

        def held_preview_read(path):
            nonlocal blocked
            if not blocked and path == root/"dist"/"index.html":
                blocked=True; started.set(); assert release.wait(5)
            return original_read(path)

        monkeypatch.setattr(Path,"read_bytes",held_preview_read)
        results=[]
        reader=threading.Thread(target=lambda: results.append(opener.open(base+"/site/").read()))
        builder=threading.Thread(target=lambda: results.append(opener.open(Request(base+"/build",data=urlencode({"csrf":token}).encode())).read()))
        reader.start(); assert started.wait(5); builder.start()
        assert builder.is_alive()
        release.set(); reader.join(10); builder.join(10)
        assert not reader.is_alive() and not builder.is_alive()
        assert any(b"Generated by Student Profile Builder" in result for result in results)
        assert b"Not found" not in results
        assert "Generated by Student Profile Builder" in opener.open(base+"/site/").read().decode()
    finally:
        release.set(); server.shutdown();server.server_close();thread.join()
