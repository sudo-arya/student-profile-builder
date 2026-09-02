# Student Profile Website Builder

Edit Profile uses an isolated live draft. Changes update the right preview automatically, while `profile.md`, deployable `dist/`, and saved managed assets remain unchanged until **Save Changes**. Invalid edits keep the last valid preview, and **Discard Changes** restores saved values.

> `profile.md` is a local working profile and is ignored by Git. The tracked
> `defaults/profile.default.md` is the canonical Aarya Mehta starter used only
> on first run and by the confirmed Restore Default action.

Run `python manage.py git-check` to verify safety. Template authors can work in
ignored `local-templates/`; see `docs/CONTRIBUTING_TEMPLATES.md`.

A lightweight, cross-platform tool that turns one Markdown student profile into a static
academic website. Phase 2 provides profile parsing and validation, dynamic template discovery,
three renderer adapters, template developer tooling, clean static builds, and local preview.
Phase 3 also supports safe IIT Delhi static-site deployment through the operating system's OpenSSH.
Phase 4 supports GitHub Pages through Git and GitHub CLI authentication.
Phase 5 adds flexible sections, theme preferences, multi-page output, and a localhost browser editor.

Profile changes from GUI and CLI are validated before an atomic save, so malformed form values do
not replace `profile.md`. Optional managed photo, CV, and PNG/ICO website-icon imports are shared
across both interfaces. If a manual edit damages the profile, the GUI retains navigation and offers
last-valid-backup recovery.

## Windows: complete installation and startup

Python **3.11.x is the recommended compatibility version** for this project. Python 3.11.9 is the
version used by the reported clean Windows installation and is the baseline this source supports.
Newer supported Python versions may also work, but using 3.11 keeps another-device installations
consistent. Git is needed only to
download/update the source with Git, while GitHub CLI and OpenSSH are optional deployment tools.

### 1. Check Python

Open PowerShell and run:

```powershell
py --version
python --version
```

If neither command reports Python 3.11 or newer, install the current Windows Python release from
<https://www.python.org/downloads/windows/>. Enable **Add python.exe to PATH** in the installer,
finish installation, close PowerShell, and open it again. `winget` users may instead run:

```powershell
winget install --id Python.Python.3.11 -e --source winget
```

After installation, close and reopen PowerShell, then verify and select Python 3.11 explicitly:

```powershell
py -3.11 --version
py -3.11 bootstrap.py
```

Python must be installed by the user; this project never installs Python or changes system PATH.

### 2. Download the project

If Git is installed:

```powershell
git --version
git clone https://github.com/sudo-arya/student-profile-builder.git
cd student-profile-builder
```

If `git` is not recognized, either install Git from <https://git-scm.com/download/win> and reopen
PowerShell, or download **Code → Download ZIP** from the GitHub repository and extract it. Git is
not needed after a ZIP download unless you want updates or GitHub Pages deployment.

### 3. Bootstrap and start

From the extracted/cloned project directory, double-click `START.bat`, or run:

```powershell
py bootstrap.py
```

If `py` is unavailable but `python` works, run `python bootstrap.py`. Bootstrap creates `.venv`,
installs the project dependencies into it, creates the working profile on first run, and launches
the GUI. The first run needs internet access to download Python packages.

### 4. Start it later

Use `START.bat` again. For direct commands, deliberately use the isolated interpreter:

```powershell
.\.venv\Scripts\python.exe manage.py gui
.\.venv\Scripts\python.exe manage.py validate
.\.venv\Scripts\python.exe manage.py build
```

Do not use plain `python manage.py ...` unless `.venv` is activated. Plain `python` can refer to
the system installation and produce errors such as `No module named yaml` even though bootstrap
installed everything correctly inside `.venv`.

### Optional Windows tools

- Missing `git`: affects cloning, updates, and GitHub deployment only.
- Missing `gh`: affects GitHub Pages publishing only. Install from <https://cli.github.com/> and
  run `gh auth login`.
- Missing `ssh`/`scp`: affects IIT Delhi publishing only. In Windows Settings, install the
  **OpenSSH Client** optional feature.
- Missing optional tools never block profile editing, local builds, or preview.

## macOS: complete installation and startup

1. Check Python with `python3 --version`. Python 3.11.x is recommended. Install Python 3.11 from
   <https://www.python.org/downloads/macos/>, or with Homebrew:

   ```bash
   brew install python@3.11
   "$(brew --prefix python@3.11)/bin/python3.11" --version
   ```
2. Check Git with `git --version`. If macOS offers to install Command Line Tools, accept that
   system prompt, or download the repository as a ZIP from GitHub.
3. Clone and enter the project when Git is available:

   ```bash
   git clone https://github.com/sudo-arya/student-profile-builder.git
   cd student-profile-builder
   ```

4. Start the application:

   ```bash
   python3.11 bootstrap.py
   ```

   The first run creates `.venv` and downloads Python dependencies. Later, use the same command or
   `./start.sh`. A direct GUI launch is `.venv/bin/python manage.py gui`.

## Linux: complete installation and startup

1. Check the required commands:

   ```bash
   python3 --version
   git --version
   ```

2. If Python is missing, install Python 3.11 and its virtual-environment component when those
   packages are available in your distribution:

   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3-pip
   ```

   On a distribution whose official repository provides Python 3.12 instead of 3.11, the supported
   system packages are also acceptable: `sudo apt install python3 python3-venv python3-pip`.

   If Git is missing and you want to clone the repository, install it separately with
   `sudo apt install git`. Users of Fedora, Arch, or another distribution should use its equivalent
   packages. Alternatively, download and extract the GitHub ZIP without Git.

3. Clone and start:

   ```bash
   git clone https://github.com/sudo-arya/student-profile-builder.git
   cd student-profile-builder
   python3.11 bootstrap.py
   ```

4. For later launches, run `./start.sh` or `.venv/bin/python manage.py gui`. Git, GitHub CLI, and
   OpenSSH remain optional unless their corresponding deployment feature is used.

See [Installation and startup](docs/INSTALLATION.md) for first-run internet requirements, repair,
proxy behavior, convenience launchers, and optional deployment tools.

## Manual development setup

Use Python 3.11 or newer. On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

The editable install enables `python -m profile_builder` and `profile-builder`. Without it,
all commands work as `python manage.py ...` from the repository root.

## For students

Edit `profile.md`; it remains the source of truth. Then launch the menu:

On Windows, use `.\.venv\Scripts\python.exe manage.py`; on Linux/macOS, use
`.venv/bin/python manage.py`. The examples below assume the virtual environment is activated.

```powershell
python manage.py
```

Direct commands are also available:

```powershell
python manage.py validate
python manage.py templates
python manage.py build
python manage.py preview
```

Start the browser editor:

```powershell
python manage.py gui
```

Open `http://127.0.0.1:8765/`. See [the GUI guide](docs/GUI_GUIDE.md). The desktop GUI is a
persistent split workspace: editing stays on the left while the generated site remains visible on
the right and refreshes after successful saves.

The dashboard separates template theme capability from the current setting and reports profile
completeness, build freshness, and publish readiness. GUI preview rebuilds before serving the full
generated tree; GUI and CLI share the same build pipeline.

Preview rebuilds first, serves only `dist/`, opens `http://localhost:8000/`, and stops with
Ctrl+C. Never edit `dist/index.html`: it is replaced by the next build. Select a different
discovered template from the menu without changing profile content.

Students only need to edit `profile.md`, choose a template, build, and preview. Template engines
and build tools are developer concerns; Node is not required for normal Jinja/static templates.

## Deploy to IIT Delhi

```powershell
python manage.py deploy iitd
```

The application asks only for a user ID and explicit public/private target. OpenSSH handles any
password prompt directly; the builder never reads or stores the password. Start with a safe local
check using `python manage.py deploy iitd --target public --userid YOUR_ID --dry-run`.
See [IITD deployment](docs/IITD_DEPLOYMENT.md) for requirements, first-deployment behavior, and
troubleshooting.

## Deploy to GitHub Pages

Guided GUI flow:

1. Install Git and GitHub CLI.
2. Run `gh auth login` once (or complete login in the deployment terminal).
3. Start Student Profile Builder and open **Publish → GitHub Pages**.
4. Choose Personal or Project site and click **Publish in Terminal**.
5. Complete any authentication or safety confirmations in the separate terminal.

The GUI and live preview remain usable while publishing. Only generated static output is managed
on the dedicated `gh-pages` branch.

```powershell
python manage.py deploy github
```

GitHub CLI handles authentication; the builder never requests a GitHub password or token. Sites
publish from the root of a dedicated `gh-pages` branch. Start with
`python manage.py deploy github --site project --repo academic-profile --username YOUR_NAME --dry-run`.
See [GitHub Pages deployment](docs/GITHUB_PAGES_DEPLOYMENT.md).

## For template developers

```powershell
python manage.py template-create modern-research
python manage.py template-info basic
python manage.py template-check basic
python manage.py build --template basic --profile examples/profiles/full.md
```

Read the [developer tutorial](docs/TEMPLATE_DEVELOPMENT.md), normative
[template contract](docs/TEMPLATE_CONTRACT.md), and [submission checklist](docs/TEMPLATE_CHECKLIST.md).
For assigned template/UI work, use the task-oriented [TA template guide](docs/TA_TEMPLATE_GUIDE.md).

## Project structure

```text
profile.md            student content (source of truth)
config.yml            template, output, and preview settings
assets/               student-owned images and files
templates/basic/      reference presentation layer
examples/              developer templates and profile QA fixtures
src/profile_builder/  parser, registry, builder, preview, and CLI
docs/                 profile, architecture, and template guides
tests/                isolated core tests
dist/                 generated output only
```

Read [the profile guide](docs/PROFILE_FORMAT.md) to edit content and
[the template guide](docs/TEMPLATE_DEVELOPMENT.md) to add a template. A normal new template
is one self-contained folder under `templates/`; the registry scans manifests dynamically.

Run the tests with `python -m pytest`.

## Imported TA portfolio templates

Four TA reference designs have been adapted into tracked, selectable Jinja templates:
`ta-arya-editorial`, `ta-balaji-tailwind`, `ta-krishna-sidebar`, and
`ta-yamini-research`. Their production copies live entirely under `templates/`; the ignored
`TA designs/` folder is reference input only and is never needed to build or distribute the
application. Each template README records authorship, external CDN use, theme support, and data
mapping. The root `profile.md` is a comprehensive fictional demo; the profile that preceded the
import is preserved as `profile.before-ta-import.md`.

## Roadmap

- Phase 5: optional improved local GUI.
