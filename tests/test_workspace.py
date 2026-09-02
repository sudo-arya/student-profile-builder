import json
import re
import shutil
import threading
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

from conftest import ROOT, make_project
from profile_builder.gui import create_server
from profile_builder.profile import parse_profile


def workspace_project(tmp_path):
    root=make_project(tmp_path)
    shutil.copy2(ROOT/"examples"/"profiles"/"full.md",root/"profile.md")
    return root


def test_workspace_has_persistent_safe_preview_and_mobile_switch(tmp_path):
    root=workspace_project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/").read().decode()
        assert 'class="workspace"' in page and 'class="editor-pane"' in page and 'class="preview-pane"' in page
        assert page.count('id="site-preview"')==1 and 'src="/site/"' in page
        assert 'data-pane="edit"' in page and 'data-pane="preview"' in page and 'class="divider"' in page
        assert '<a class="button ghost" href="/preview">' not in page
    finally: server.shutdown();server.server_close();thread.join()


def test_temporary_template_uses_workspace_preview_status(tmp_path):
    root=workspace_project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/templates").read().decode(); token=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        opener.open(Request(base+"/template/preview",data=urlencode({"csrf":token,"id":"basic-hybrid"}).encode()))
        status=json.loads(opener.open(base+"/api/build-status").read())
        assert status["preview_url"]=="/draft-site/" and status["preview_template"]=="basic-hybrid"
        assert 'class="directory"' in opener.open(base+"/draft-site/").read().decode()
        assert "<aside>" not in opener.open(base+"/site/").read().decode()
        opener.open(Request(base+"/template/return",data=urlencode({"csrf":token}).encode()))
        assert json.loads(opener.open(base+"/api/build-status").read())["preview_url"]=="/site/"
    finally: server.shutdown();server.server_close();thread.join()


def test_workspace_move_buttons_send_action_and_reorder_sections(tmp_path):
    root=workspace_project(tmp_path); server=create_server(root,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/profile").read().decode(); token=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        original=[section.id for section in parse_profile(root/"profile.md",root).sections]
        target=original[1]
        opener.open(Request(base+"/section/action",data=urlencode({"csrf":token,"id":target,"action":"up"}).encode()))
        assert [section.id for section in parse_profile(root/"profile.md",root).sections] == original
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":token}).encode()))
        moved=[section.id for section in parse_profile(root/"profile.md",root).sections]
        assert moved[:2] == [target,original[0]]
        opener.open(Request(base+"/section/action",data=urlencode({"csrf":token,"id":target,"action":"down"}).encode()))
        assert [section.id for section in parse_profile(root/"profile.md",root).sections] == moved
        opener.open(Request(base+"/profile/draft-save",data=urlencode({"csrf":token}).encode()))
        assert [section.id for section in parse_profile(root/"profile.md",root).sections] == original
        assert "if(e.submitter?.name)data.set(e.submitter.name,e.submitter.value)" in page
        assert "const destination=f.getAttribute('action')||location.pathname" in page
        assert "fetch(f.action" not in page
    finally: server.shutdown();server.server_close();thread.join()
