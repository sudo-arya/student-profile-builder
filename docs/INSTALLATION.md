# Installation and startup

Bootstrap copies `defaults/profile.default.md` to local `profile.md` only when the
working profile is absent. Existing student data is never overwritten.

Student Profile Builder is distributed as source code and supports Windows 10/11, Linux desktop
systems (including Ubuntu), and macOS. Python 3.11.x is the recommended compatibility version;
Python 3.11.9 is the clean-install baseline. Newer supported versions may also work. Python must
already be installed. iPhone and iPad iOS are not supported runtimes.

## Windows

From the project directory run:

```powershell
py bootstrap.py
```

To install and explicitly use the recommended version:

```powershell
winget install --id Python.Python.3.11 -e --source winget
py -3.11 --version
py -3.11 bootstrap.py
```

If the Python launcher is unavailable, use `python bootstrap.py` or double-click `START.bat`.

After bootstrap, prefer `START.bat` for normal launches. Direct commands should use the isolated
interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe manage.py gui
```

Running plain `python manage.py gui` without activating `.venv` may select the system Python and
report missing packages even though they are correctly installed in the project environment.

## Ubuntu and other Linux desktops

Check `python3 --version` first. Install Python 3.11 or newer and its virtual-environment support
using the distribution package manager. On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

Install Git separately (`sudo apt install git`) only when cloning/updating or using GitHub
deployment. A downloaded GitHub ZIP works without Git. Then, from the project directory:

```bash
python3 bootstrap.py
```

The convenience `start.sh` runs the same command. Direct launches use
`.venv/bin/python manage.py gui`.

## macOS

Check `python3 --version`. Python 3.11.x is recommended. Install it from python.org or with
`brew install python@3.11`. Check `git --version`; macOS may offer
to install Command Line Tools, while downloading the repository ZIP avoids the Git requirement.
Then run:

```bash
python3 bootstrap.py
```

For later launches, use `./start.sh` or `.venv/bin/python manage.py gui`.

## What bootstrap does

`bootstrap.py` checks Python, creates `.venv` when missing, ensures pip inside that environment,
installs `requirements.txt` with the environment's Python, verifies core imports, reports optional
deployment tools, and launches the localhost GUI. It never installs project packages globally and
does not require environment activation.

A dependency fingerprint covers `requirements.txt`, Python major/minor, and the bootstrap dependency
marker. Unchanged later starts skip pip installation. If `.venv` is damaged, bootstrap asks before
removing only that exact project-owned directory.

Initial dependency installation normally requires internet access unless pip already has suitable
packages cached. Existing `HTTP_PROXY`, `HTTPS_PROXY`, lowercase equivalents, and pip configuration
are respected; the project does not store proxy credentials. A future offline distribution could
include a reviewed `wheelhouse/`, but no offline bundle is provided in this phase.

OpenSSH (`ssh` and `scp`) is required before IITD publishing can be configured or used. On Windows,
install it from an Administrator PowerShell with
`Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0`. macOS normally includes it. On
Ubuntu/Debian use `sudo apt install openssh-client`. Verify with `ssh -V` and `scp`, then run
`python bootstrap.py --check` again. Its absence does not block editing, building, or previewing.

Git and GitHub CLI are required only for their corresponding Git/GitHub workflows. Bootstrap
reports system tools but never installs Python, Git, `gh`, OpenSSH, Node, or other system software.

Maintainers can run `python bootstrap.py --check` to verify or update the isolated environment and
tool status without launching the GUI.
