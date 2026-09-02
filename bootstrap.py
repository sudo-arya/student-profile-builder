"""Cross-platform, source-distribution bootstrap for Student Profile Builder."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import venv

MINIMUM_PYTHON = (3, 11)
DEPENDENCY_MARKER = "bootstrap-v1"
STATE_FILE = ".student-profile-builder-dependencies.json"


def python_supported(version_info=None) -> bool:
    version = version_info or sys.version_info
    return tuple(version[:2]) >= MINIMUM_PYTHON


def venv_python(project: Path, platform: str | None = None) -> Path:
    platform = platform or os.name
    return project / ".venv" / ("Scripts/python.exe" if platform == "nt" else "bin/python")


def dependency_fingerprint(project: Path, version_info=None) -> str:
    version = version_info or sys.version_info
    digest = sha256()
    digest.update(f"{version[0]}.{version[1]}\0{DEPENDENCY_MARKER}\0".encode())
    digest.update((project / "requirements.txt").read_bytes())
    return digest.hexdigest()


def run(arguments: list[str], project: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, cwd=project, shell=False, check=check)


def environment_works(python: Path, project: Path) -> bool:
    if not python.is_file(): return False
    result=subprocess.run([str(python),"-c","import sys; raise SystemExit(sys.version_info < (3,11))"],
                          cwd=project,shell=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return result.returncode == 0


def recreate_environment(project: Path, input_fn=input) -> bool:
    environment=(project/".venv").resolve()
    if environment.parent != project.resolve(): raise RuntimeError("Refusing unsafe environment path")
    answer=input_fn("The project environment appears damaged.\n\nRecreate it? [Y/n] ").strip().lower()
    if answer not in {"", "y", "yes"}: return False
    shutil.rmtree(environment)
    return True


def ensure_environment(project: Path, *, input_fn=input) -> Path:
    python=venv_python(project)
    environment=project/".venv"
    if environment.exists() and not environment_works(python,project):
        if not recreate_environment(project,input_fn):
            raise RuntimeError("The damaged project environment was left unchanged.")
    if not environment.exists():
        print("Creating isolated Python environment...")
        venv.EnvBuilder(with_pip=True).create(environment)
    python=venv_python(project)
    if not environment_works(python,project):
        raise RuntimeError("The isolated Python environment could not run a supported Python interpreter.")
    pip=subprocess.run([str(python),"-m","pip","--version"],cwd=project,shell=False,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if pip.returncode:
        run([str(python),"-m","ensurepip","--upgrade"],project)
    return python


def ensure_dependencies(project: Path, python: Path) -> bool:
    fingerprint=dependency_fingerprint(project); state=project/".venv"/STATE_FILE
    try: ready=json.loads(state.read_text(encoding="utf-8")).get("fingerprint") == fingerprint
    except (OSError,json.JSONDecodeError): ready=False
    if ready:
        print("Dependencies are ready [OK]")
        return False
    print("Updating project environment...")
    try: run([str(python),"-m","pip","install","-r",str(project/"requirements.txt")],project)
    except subprocess.CalledProcessError as error:
        raise RuntimeError("Unable to install Student Profile Builder dependencies.\n\nCheck:\n- internet connection\n- proxy configuration\n- Python installation\n\nThe rest of your system was not modified.") from error
    state.write_text(json.dumps({"fingerprint":fingerprint},indent=2),encoding="utf-8")
    return True


def optional_tools(which=shutil.which) -> dict[str, bool]:
    return {name: bool(which(name)) for name in ("ssh","scp","git","gh")}


def print_summary(python: Path, project: Path) -> None:
    version=subprocess.run([str(python),"-c","import platform; print(platform.python_version())"],cwd=project,
                           shell=False,text=True,capture_output=True,check=True).stdout.strip()
    tools=optional_tools()
    print(f"\nStudent Profile Builder\n\nCore application\n[OK] Python {version}\n[OK] Isolated environment\n[OK] Interpreter: {python.resolve()}\n[OK] Python dependencies")
    print("\nIITD deployment\n"+("[OK] OpenSSH Client\n[OK] ssh\n[OK] scp" if tools["ssh"] and tools["scp"] else "[ACTION REQUIRED] OpenSSH Client is required before IITD publishing.\nInstall/enable both ssh and scp, then run bootstrap.py --check again."))
    print("\nGitHub deployment\n"+("[OK] git" if tools["git"] else "[WARN] git not installed")+"\n"+("[OK] gh" if tools["gh"] else "[WARN] GitHub CLI not installed"))


def main() -> int:
    project=Path(__file__).resolve().parent
    if not python_supported():
        detected=".".join(map(str,sys.version_info[:3]))
        print(f"Student Profile Builder requires Python 3.11 or newer.\n\nDetected:\nPython {detected}\n\nPlease install a supported Python version and run bootstrap.py again.")
        return 1
    try:
        if not (project / ".gitignore").is_file():
            print("[WARN] .gitignore is missing; local profile and runtime files may be exposed.")
        python=ensure_environment(project)
        ensure_dependencies(project,python)
        run([str(python),"-c","import sys; from pathlib import Path; sys.path.insert(0, 'src'); from profile_builder.workspace import ensure_working_profile; ensure_working_profile(Path.cwd())"],project)
        run([str(python),"-c","import sys; sys.path.insert(0, 'src'); import profile_builder"],project)
        print_summary(python,project)
        if "--check" in sys.argv:
            print("\nBootstrap check complete.")
            return 0
        print("\nStarting Student Profile Builder...")
        return run([str(python),str(project/"manage.py"),"gui"],project,check=False).returncode
    except (RuntimeError,subprocess.CalledProcessError,OSError) as error:
        print(f"\n{error}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    try: raise SystemExit(main())
    except KeyboardInterrupt: print("\nGUI stopped.")
