"""Non-secret deployment jobs and cross-platform terminal launching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid

from .utils import BuilderError

JOB_ID = re.compile(r"^[0-9a-f]{32}$")
ACTIVE = {"waiting", "running"}
FINAL = {"success", "failed", "cancelled", "warning", "interrupted"}
WAITING_TIMEOUT_SECONDS = 30
SAFE_KEYS = {"id","provider","state","started_at","updated_at","finished_at","target","userid",
             "site","repository","username","dry_run","url","repository_url","message","pid"}


def _now() -> str: return datetime.now(timezone.utc).isoformat()


def process_alive(pid: int) -> bool:
    if not isinstance(pid,int) or pid <= 0: return False
    try: os.kill(pid,0); return True
    except OSError: return False


class DeploymentJobStore:
    def __init__(self, root: Path, alive: Callable[[int],bool] = process_alive):
        self.root=root.resolve(); self.directory=self.root/".runtime"/"deployments"; self.alive=alive

    def path(self, job_id: str) -> Path:
        if not JOB_ID.fullmatch(job_id): raise BuilderError("Invalid deployment job ID.")
        return self.directory/f"{job_id}.json"

    def _write(self, job: dict) -> dict:
        self.directory.mkdir(parents=True,exist_ok=True); path=self.path(job["id"]); temporary=path.with_suffix(".tmp")
        safe={key:value for key,value in job.items() if key in SAFE_KEYS}
        temporary.write_text(json.dumps(safe,indent=2),encoding="utf-8"); temporary.replace(path); return safe

    def create(self, provider: str, **options) -> dict:
        if provider not in {"iitd","github"}: raise BuilderError("Unknown deployment provider.")
        for job in self.recent():
            if job.get("provider")==provider and job.get("target")==options.get("target") and job.get("state") in ACTIVE:
                raise BuilderError(f"A {provider.upper()} deployment is already running.")
        now=_now(); job={"id":uuid.uuid4().hex,"provider":provider,"state":"waiting","started_at":now,
                         "updated_at":now,"finished_at":None,"url":None,"message":"",**options}
        return self._write(job)

    def read(self, job_id: str) -> dict:
        try: job=json.loads(self.path(job_id).read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise BuilderError("Deployment job not found.") from exc
        if job.get("state")=="running" and job.get("pid") and not self.alive(job["pid"]):
            job=self.update(job_id,state="interrupted",message="Deployment terminal closed before completion.",finished_at=_now())
        elif job.get("state")=="waiting":
            try: age=(datetime.now(timezone.utc)-datetime.fromisoformat(job["updated_at"])).total_seconds()
            except (KeyError,TypeError,ValueError): age=0
            if age>WAITING_TIMEOUT_SECONDS: job=self.update(job_id,state="interrupted",message="Deployment worker did not start.",finished_at=_now())
        return job

    def update(self, job_id: str, **changes) -> dict:
        try: job=json.loads(self.path(job_id).read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise BuilderError("Deployment job not found.") from exc
        job.update(changes); job["updated_at"]=_now()
        if job.get("state") in FINAL and not job.get("finished_at"): job["finished_at"]=_now()
        return self._write(job)

    def recent(self, limit: int = 12) -> list[dict]:
        if not self.directory.is_dir(): return []
        jobs=[]
        for path in sorted(self.directory.glob("*.json"),key=lambda item:item.stat().st_mtime,reverse=True)[:limit]:
            try: jobs.append(self.read(path.stem))
            except BuilderError: continue
        return jobs


@dataclass(frozen=True)
class LaunchResult:
    started: bool
    manual_command: str
    terminal: str | None = None
    message: str = ""


class TerminalLauncher:
    def __init__(self, *, platform: str | None = None, which=shutil.which, popen=subprocess.Popen):
        self.platform=platform or sys.platform; self.which=which; self.popen=popen

    def launch(self, command: list[str], title: str, runtime: Path) -> LaunchResult:
        manual=subprocess.list2cmdline(command) if self.platform.startswith("win") else shlex.join(command)
        try:
            if self.platform.startswith("win"):
                # Launch the argument array directly. Passing a pre-quoted command through
                # ``cmd /k`` loses arguments on some Windows installations when the project
                # path contains spaces, causing the worker to use the terminal's home folder.
                creation_flags=getattr(subprocess,"CREATE_NEW_CONSOLE",0x00000010)
                self.popen(command,shell=False,cwd=runtime.parent,creationflags=creation_flags)
                return LaunchResult(True,manual,"Windows console")
            if self.platform=="darwin":
                opener=self.which("open")
                if not opener: return LaunchResult(False,manual,message="macOS Terminal launcher was not found.")
                runtime.mkdir(parents=True,exist_ok=True); suffix=command[-1] if command and JOB_ID.fullmatch(command[-1]) else uuid.uuid4().hex; script=runtime/f"deployment-worker-{suffix}.command"
                script.write_text("#!/bin/sh\n"+shlex.join(command)+"\n",encoding="utf-8"); script.chmod(0o700)
                self.popen([opener,"-a","Terminal",str(script)],shell=False,cwd=runtime.parent)
                return LaunchResult(True,manual,"Terminal")
            candidates=(("x-terminal-emulator",["-e"]),("gnome-terminal",["--"]),("konsole",["-e"]),("xfce4-terminal",["-x"]))
            for name,prefix in candidates:
                executable=self.which(name)
                if executable:
                    self.popen([executable,*prefix,*command],shell=False,cwd=runtime.parent)
                    return LaunchResult(True,manual,name)
            return LaunchResult(False,manual,message="No supported desktop terminal was found.")
        except OSError as exc:
            return LaunchResult(False,manual,message=f"Unable to open deployment terminal: {exc}")


def worker_command(root: Path, job_id: str) -> list[str]:
    root=root.resolve()
    if not JOB_ID.fullmatch(job_id): raise BuilderError("Invalid deployment job ID.")
    python=root/".venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not python.is_file(): python=Path(sys.executable)
    return [str(python),str(root/"manage.py"),"deployment-worker",job_id,"--project-root",str(root)]
