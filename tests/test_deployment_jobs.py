import json
import re
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import pytest
from conftest import ROOT, make_project
from profile_builder.deployment_jobs import DeploymentJobStore, LaunchResult, TerminalLauncher, process_alive, worker_command
from profile_builder.deployment_worker import run_worker
from profile_builder.gui import create_server


def project(tmp_path):
    root=make_project(tmp_path); shutil.copy2(ROOT/"examples"/"profiles"/"full.md",root/"profile.md"); return root


def test_job_storage_filters_secrets_and_supports_states(tmp_path):
    store=DeploymentJobStore(tmp_path,alive=lambda _pid:True)
    job=store.create("iitd",target="public",userid="student",password="never",token="never")
    raw=(store.path(job["id"])).read_text()
    assert "password" not in raw and "token" not in raw
    for state in ("running","success","failed","warning","cancelled"):
        assert store.update(job["id"],state=state)["state"]==state


def test_dead_running_worker_becomes_interrupted(tmp_path):
    store=DeploymentJobStore(tmp_path,alive=lambda _pid:False); job=store.create("iitd",target="public",userid="student")
    store.update(job["id"],state="running",pid=999999)
    assert store.read(job["id"])["state"]=="interrupted"


def test_process_alive_handles_current_and_missing_processes():
    import os
    assert process_alive(os.getpid())
    assert not process_alive(2_147_483_647)


def test_stale_waiting_job_becomes_interrupted(tmp_path):
    store=DeploymentJobStore(tmp_path); job=store.create("iitd",target="private",userid="student")
    path=store.path(job["id"]); data=json.loads(path.read_text()); data["updated_at"]="2000-01-01T00:00:00+00:00"; path.write_text(json.dumps(data))
    assert store.read(job["id"])["state"]=="interrupted"


def test_duplicate_active_provider_target_is_rejected(tmp_path):
    store=DeploymentJobStore(tmp_path,alive=lambda _pid:True); store.create("iitd",target="public",userid="one")
    with pytest.raises(Exception,match="already running"): store.create("iitd",target="public",userid="two")


def test_windows_terminal_uses_argument_array_without_credentials(tmp_path):
    calls=[]; launcher=TerminalLauncher(platform="win32",popen=lambda args,**kw:calls.append((args,kw)))
    result=launcher.launch(["C:/Project/.venv/Scripts/python.exe","manage.py","deployment-worker","a"*32],"Deploy",tmp_path/".runtime")
    assert result.started and calls and calls[0][1]["shell"] is False
    assert calls[0][0][0]=="C:/Project/.venv/Scripts/python.exe"
    assert calls[0][1]["cwd"]==tmp_path
    assert calls[0][1]["creationflags"]
    joined=" ".join(calls[0][0]).lower(); assert "password" not in joined and "token" not in joined


def test_worker_command_carries_absolute_project_root(tmp_path):
    root=tmp_path.resolve(); (root/".venv"/"Scripts").mkdir(parents=True); (root/".venv"/"Scripts"/"python.exe").write_text("")
    command=worker_command(root,"d"*32)
    assert command[-2:]==["--project-root",str(root)]


def test_worker_cli_uses_explicit_root_before_workspace_initialization(monkeypatch,tmp_path):
    root=project(tmp_path/"project"); (root/"manage.py").write_text("",encoding="utf-8"); outside=tmp_path/"home"; outside.mkdir()
    import profile_builder.cli as cli
    calls=[]
    monkeypatch.chdir(outside)
    monkeypatch.setattr(cli,"ensure_working_profile",lambda _root:(_ for _ in ()).throw(AssertionError("must not initialize terminal cwd")))
    monkeypatch.setattr("profile_builder.deployment_worker.run_worker",lambda worker_root,job_id:(calls.append((worker_root,job_id)) or 0))
    job_id="e"*32
    assert cli.main(["deployment-worker",job_id,"--project-root",str(root)])==0
    assert calls==[(root.resolve(),job_id)]


def test_linux_terminal_and_missing_fallback(tmp_path):
    calls=[]; available=lambda name:"/usr/bin/gnome-terminal" if name=="gnome-terminal" else None
    result=TerminalLauncher(platform="linux",which=available,popen=lambda args,**kw:calls.append(args)).launch(["python3","manage.py","deployment-worker","b"*32],"Deploy",tmp_path/".runtime")
    assert result.started and calls[0][:2]==["/usr/bin/gnome-terminal","--"]
    missing=TerminalLauncher(platform="linux",which=lambda _name:None).launch(["python3","manage.py"],"Deploy",tmp_path/".runtime")
    assert not missing.started and missing.manual_command


def test_macos_terminal_command_generation(tmp_path):
    calls=[]; launcher=TerminalLauncher(platform="darwin",which=lambda name:"/usr/bin/open" if name=="open" else None,popen=lambda args,**kw:calls.append(args))
    result=launcher.launch(["python3","manage.py","deployment-worker","c"*32],"Deploy",tmp_path/".runtime")
    assert result.started and calls[0][:3]==["/usr/bin/open","-a","Terminal"]
    assert list((tmp_path/".runtime").glob("deployment-worker-*.command"))


def test_worker_failure_updates_job_without_gui(monkeypatch,tmp_path):
    root=project(tmp_path); store=DeploymentJobStore(root); job=store.create("iitd",target="public",userid="student",dry_run=True)
    import profile_builder.cli as cli
    monkeypatch.setattr(cli,"_deploy",lambda *_a,**_k:(_ for _ in ()).throw(RuntimeError("provider failed")))
    assert run_worker(root,job["id"],pause=False)==2
    failed=store.read(job["id"]); assert failed["state"]=="failed" and "provider failed" in failed["message"]


def test_gui_starts_job_without_running_provider_and_has_status_api(monkeypatch,tmp_path):
    root=project(tmp_path); launches=[]
    class FakeLauncher:
        def launch(self,command,title,runtime):
            launches.append((command,title,runtime)); return LaunchResult(True,"manual command","Test Terminal")
    import profile_builder.gui as gui
    monkeypatch.setattr(gui.IITDDeploymentProvider,"deploy",lambda *_:(_ for _ in ()).throw(AssertionError("provider must not run in GUI")))
    server=create_server(root,0,terminal_launcher=FakeLauncher()); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/publish").read().decode(); token=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        response=opener.open(Request(base+"/deploy/iitd",data=urlencode({"csrf":token,"userid":"student","target":"public","mode":"dry"}).encode())).read().decode()
        assert "Deployment started" in response and launches
        job_id=re.search(r'data-deployment-job="([0-9a-f]{32})"',response).group(1)
        status=json.loads(opener.open(base+"/api/deployments/"+job_id).read())
        assert status["provider"]=="iitd" and status["state"]=="waiting"
        assert opener.open(base+"/api/health").status==200
    finally: server.shutdown();server.server_close();thread.join()


def test_gui_terminal_failure_returns_manual_command_not_http_500(tmp_path):
    root=project(tmp_path)
    class MissingTerminal:
        def launch(self,command,title,runtime): return LaunchResult(False,"safe manual command",message="No terminal found")
    server=create_server(root,0,terminal_launcher=MissingTerminal()); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); opener=build_opener(ProxyHandler({})); base=f"http://127.0.0.1:{server.server_port}"
    try:
        page=opener.open(base+"/publish").read().decode(); token=re.search(r'name="csrf" value="([^"]+)',page).group(1)
        response=opener.open(Request(base+"/deploy/iitd",data=urlencode({"csrf":token,"userid":"student","target":"private","mode":"dry"}).encode())).read().decode()
        assert "Unable to start deployment terminal" in response and "safe manual command" in response
        assert 'id="site-preview"' in response
    finally: server.shutdown();server.server_close();thread.join()
