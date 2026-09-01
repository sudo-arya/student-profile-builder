from pathlib import Path
from typing import Callable
import json
import re
import secrets
import shlex
import shutil
import socket
import tempfile

from ..builder import validate_output
from ..utils import BuilderError
from .manifest import MANIFEST_NAME, collect_files, create_manifest, parse_manifest, stale_files
from .models import DeploymentRequest, DeploymentResult
from .ssh import OpenSSHRunner

IITD_SSH_HOST = "ssh1.iitd.ac.in"
USERID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
STAGING = re.compile(r"^\.student-profile-builder-upload-[0-9a-f]{32}$")


def validate_userid(value: str) -> str:
    if not USERID.fullmatch(value):
        raise BuilderError("Invalid IIT Delhi user ID. Use only letters, numbers, dots, underscores, and hyphens.")
    return value


def check_reachability(connector=socket.create_connection) -> None:
    try:
        connection=connector((IITD_SSH_HOST,22),timeout=5)
        if hasattr(connection,"close"): connection.close()
    except OSError as exc:
        raise BuilderError("Unable to reach IIT Delhi SSH service.\n\nCheck your network connection. If your environment requires IIT Delhi campus/VPN access, connect to the IIT Delhi network and try again.") from exc


class IITDDeploymentProvider:
    def __init__(self, runner: OpenSSHRunner | None = None, status: Callable[[str], None] = print,
                 confirm_first: Callable[[], bool] | None = None, retries: int = 0):
        self.runner = runner or OpenSSHRunner(); self.status = status
        self.confirm_first = confirm_first or (lambda: False)
        if not 0<=retries<=2: raise BuilderError("IITD retries must be between 0 and 2.")
        self.retries=retries

    def _run(self,arguments,*,capture=False):
        result=None
        for attempt in range(self.retries+1):
            result=self.runner.run(arguments,capture=capture)
            if result.returncode!=255: break
            if attempt<self.retries: self.status(f"SSH connection failed; retrying ({attempt+1}/{self.retries})...")
        return result

    def deploy(self, request: DeploymentRequest) -> DeploymentResult:
        userid = validate_userid(request.userid)
        output = request.output_directory.resolve()
        issues = validate_output(output)
        if issues: raise BuilderError("Deployment stopped: generated output is invalid.\n" + "\n".join(i.message for i in issues))
        files, total = collect_files(output)
        manifest = create_manifest(output, request.target)
        result = DeploymentResult(True, "iitd", request.target.value, request.target.url(userid), len(files), total, request.dry_run)
        ssh, scp = self.runner.check_tools()
        if request.dry_run:
            self.status("Dry run: local build and deployment package are valid. No SSH/SCP commands were run.")
            return result
        if isinstance(self.runner,OpenSSHRunner):
            check_reachability()
        destination = f"{userid}@{IITD_SSH_HOST}"
        target = request.target.directory
        self.status("IIT Delhi authentication is handled directly by OpenSSH. You may be prompted multiple times for separate manifest, upload, and install operations. Student Profile Builder never reads or stores your password.")
        options=list(getattr(self.runner,"connection_options",()))
        previous_result = self._run([ssh,*options,destination,f"test -f ~/{target}/{MANIFEST_NAME} && cat ~/{target}/{MANIFEST_NAME} || true"],capture=True)
        if previous_result.returncode: raise BuilderError("Deployment failed while checking the remote ownership manifest.")
        previous = parse_manifest(previous_result.stdout)
        if previous is None and not self.confirm_first():
            raise BuilderError("Deployment cancelled. No remote files were changed.")
        obsolete = stale_files(previous, manifest)
        staging_name = f".student-profile-builder-upload-{secrets.token_hex(16)}"
        with tempfile.TemporaryDirectory(prefix="profile-deploy-") as temporary:
            staging = Path(temporary) / staging_name
            shutil.copytree(output, staging)
            (staging / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            script = _remote_script(target, staging_name, files, obsolete)
            (staging / "deploy.sh").write_text(script, encoding="utf-8", newline="\n")
            # scp creates the unique staging directory beneath $HOME, avoiding a separate
            # authentication round trip solely for mkdir.
            upload = self._run([scp,*options,"-r",str(staging),f"{destination}:~/"])
            if upload.returncode: raise BuilderError("Deployment failed while uploading website files. The existing website was not intentionally deleted.")
            install = self._run([ssh,*options,destination,f"sh ~/{staging_name}/deploy.sh"],capture=True)
            if install.returncode: raise BuilderError("Remote installation or verification failed. Deployment success cannot be confirmed.")
            if "__SPB_CLEANUP_WARNING__" in install.stdout:
                warning="Temporary remote staging directory could not be removed. The website was published and verified."
                self.status("Warning: "+warning); result=DeploymentResult(**{**result.__dict__,"warnings":(warning,)})
        return result


def _remote_script(target: str, staging: str, files: list[str], obsolete: list[str]) -> str:
    if target not in {"public_html","private_html"} or not STAGING.fullmatch(staging):
        raise BuilderError("Refusing unsafe remote deployment path.")
    q = shlex.quote
    lines = ["set -eu", f"target=$HOME/{target}", f"stage=$HOME/{staging}",
             'chmod o+x "$HOME"', 'mkdir -p "$target"', 'chmod 755 "$target"']
    directories = sorted({str(Path(value).parent).replace("\\", "/") for value in files if "/" in value})
    for directory in directories:
        lines += [f'mkdir -p "$target"/{q(directory)}', f'chmod 755 "$target"/{q(directory)}']
    for value in files:
        lines += [f'cp "$stage"/{q(value)} "$target"/{q(value)}', f'chmod 644 "$target"/{q(value)}']
    lines += [f'cp "$stage"/{MANIFEST_NAME} "$target"/{MANIFEST_NAME}', f'chmod 644 "$target"/{MANIFEST_NAME}']
    for value in obsolete: lines.append(f'rm -f -- "$target"/{q(value)}')
    lines += ['test -f "$target/index.html"', 'test -r "$target/index.html"',
              f'test -f "$target/{MANIFEST_NAME}"',
              # This exact directory is generated by this deployment directly below $HOME.
              # Recursive deletion is never used for public_html/private_html or user input.
              'cd "$HOME"',
              'if rm -rf -- "$stage"; then :; else echo "__SPB_CLEANUP_WARNING__"; fi']
    return "\n".join(lines) + "\n"
