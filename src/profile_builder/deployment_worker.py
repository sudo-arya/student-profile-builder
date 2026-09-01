"""Separate terminal worker for GUI-created deployment jobs."""
from pathlib import Path
import os
import traceback

from .deployment_jobs import DeploymentJobStore
from .utils import BuilderError


def _yes(message: str, default: bool = False) -> bool:
    answer=input(message+(" [Y/n]: " if default else " [y/N]: ")).strip().lower()
    return default if not answer else answer in {"y","yes"}


def run_worker(root: Path, job_id: str, *, pause: bool = True) -> int:
    store=DeploymentJobStore(root); job=store.read(job_id)
    store.update(job_id,state="running",pid=os.getpid(),message="Deployment is running in the terminal.")
    provider=job["provider"]
    print("\nStudent Profile Builder")
    print("IIT Delhi Deployment\n" if provider=="iitd" else "GitHub Pages Deployment\n")
    try:
        from .cli import _deploy, _github_deploy
        from .config import load_config
        config=load_config(root/"config.yml")
        if provider=="iitd":
            print(f"Target: {job['target'].title()}\nAccount: {job['userid']}\n\nAuthentication is handled by OpenSSH.\nYou may be prompted for your password multiple times.\nDo not close this terminal until deployment completes.\n")
            try: result=_deploy(root,config,userid=job["userid"],target=job["target"],dry_run=job.get("dry_run",False),retries=1)
            except BuilderError:
                if job.get("dry_run",False) or not _yes("The SSH connection/authentication failed. Retry deployment?",True): raise
                result=_deploy(root,config,userid=job["userid"],target=job["target"],dry_run=False,retries=1)
            repository_url=None
        else:
            print("Authentication is handled by GitHub CLI.\nIf you are not signed in, GitHub CLI will guide you through browser/device login.\n")
            result=_github_deploy(root,config,site=job["site"],repo=job.get("repository"),username=job.get("username") or None,
                                  dry_run=job.get("dry_run",False),allow_login=not job.get("dry_run",False))
            repository_url=f"https://github.com/{result.username}/{result.repository}"
        state="warning" if getattr(result,"warnings",()) else "success"
        store.update(job_id,state=state,url=result.url,repository_url=repository_url,message="Deployment completed successfully.")
        print("\nDeployment completed successfully.\nYou may close this window.")
        code=0
    except (BuilderError,Exception) as exc:
        store.update(job_id,state="failed",message=str(exc)[:1000])
        print(f"\nDeployment did not complete.\n\n{exc}\n\nThe Student Profile Builder GUI is still running.")
        if not isinstance(exc,BuilderError): traceback.print_exc()
        code=2
    if pause and os.environ.get("SPB_WORKER_NO_PAUSE")!="1":
        try: input("\nPress Enter to close this window.")
        except EOFError: pass
    return code
