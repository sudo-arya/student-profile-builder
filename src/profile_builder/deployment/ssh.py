from dataclasses import dataclass
from typing import Sequence
import shutil
import subprocess

from ..utils import BuilderError


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""


class OpenSSHRunner:
    connection_options = ("-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3")
    def check_tools(self) -> tuple[str, str]:
        ssh, scp = shutil.which("ssh"), shutil.which("scp")
        if not ssh: raise BuilderError("IIT Delhi deployment cannot start.\n\nRequired command not found: ssh\nInstall/enable OpenSSH Client and try again.")
        if not scp: raise BuilderError("IIT Delhi deployment cannot start.\n\nRequired command not found: scp\nInstall/enable OpenSSH Client and try again.")
        return ssh, scp

    def run(self, arguments: Sequence[str], *, capture: bool = False) -> CommandResult:
        result = subprocess.run(list(arguments), shell=False, check=False, text=True,
                                stdout=subprocess.PIPE if capture else None)
        return CommandResult(result.returncode, result.stdout or "")
