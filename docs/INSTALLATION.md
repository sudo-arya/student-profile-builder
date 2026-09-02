# Installation and startup

Bootstrap copies `defaults/profile.default.md` to local `profile.md` only when the
working profile is absent. Existing student data is never overwritten.

Student Profile Builder is distributed as source code and supports Windows 10/11, Linux desktop
systems (including Ubuntu), and macOS. Python 3.11 or newer must already be installed. iPhone and
iPad iOS are not supported runtimes.

## Windows

From the project directory run:

```powershell
py bootstrap.py
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
sudo apt install python3 python3-venv python3-pip
```

Install Git separately (`sudo apt install git`) only when cloning/updating or using GitHub
deployment. A downloaded GitHub ZIP works without Git. Then, from the project directory:

```bash
python3 bootstrap.py
```

The convenience `start.sh` runs the same command. Direct launches use
`.venv/bin/python manage.py gui`.

## macOS

Check `python3 --version`. If Python 3.11 or newer is unavailable, install a current Python from
python.org or a trusted package manager such as Homebrew. Check `git --version`; macOS may offer
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

Git, GitHub CLI, and OpenSSH are optional system tools. Their absence does not block editing,
building, or previewing. Bootstrap reports them but never installs Python, Git, `gh`, OpenSSH, Node,
or other system software.

Maintainers can run `python bootstrap.py --check` to verify or update the isolated environment and
tool status without launching the GUI.
