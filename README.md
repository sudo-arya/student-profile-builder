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

## Recommended installation and startup

Install Python 3.11 or newer, then run the source bootstrapper. It creates and manages an isolated
`.venv`; project packages are never installed globally.

```powershell
# Windows
py bootstrap.py
```

```bash
# Linux or macOS
python3 bootstrap.py
```

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
