# Local GUI guide

Normally run `py bootstrap.py` on Windows or `python3 bootstrap.py` on Linux/macOS. Developers may
run `python manage.py gui` inside an existing environment. Open `http://127.0.0.1:8765/`, keep the terminal open, and press
Ctrl+C there to stop. The editor is localhost-only and has no database.

## Persistent workspace

The desktop application keeps Dashboard, Edit Profile, Templates, and Publish in a scrollable left
pane and one live generated-site iframe in the right pane. Navigation and form submissions update
the left content in place where possible, so the preview iframe remains logically stable. Desktop,
Tablet, Mobile, Refresh, and Open in New Tab controls sit above it. The divider is resizable and its
position is stored locally in the browser.

Below 760px the workspace becomes Edit/Preview tabs and retains the current editor DOM while
switching panes. Ctrl+S or Cmd+S submits the currently dirty editor form.

Successful profile, section, appearance, asset, template, and manual-build operations rebuild and
refresh the existing preview. A failed candidate cannot replace `dist`; the right pane retains the
last valid build and reports that state.

Use **Edit Profile** for fixed information, links, research interests, asset paths, and generated-
site theme settings. The first GUI save creates `profile.md.bak`; `profile.md` remains the source
of truth. Asset paths must stay inside `assets/`. The profile-photo controls can keep the current
photo, discard an uploaded photo and restore the bundled placeholder, or hide the photo entirely.

Website section cards let you edit/rename, move up/down, hide/show, and delete after confirmation.
You can add any semantic or custom section. Publications, Projects, and Awards are optional.
Content remains Markdown; hidden sections stay stored but are omitted from generated output.

Theme switching may be disabled or use a Light, Dark, or System default. A theme-enabled profile
requires a capable template; Basic supports it. Choose templates dynamically, build, then open the
preview in the permanent right pane.

Deployment credential interaction continues safely in the terminal with
`python manage.py deploy iitd` or `python manage.py deploy github`. The GUI never provides password
or token fields.

## Stabilized workflow

The dashboard distinguishes template theme capability from the profile's theme setting. It shows
profile completeness, build freshness, publish readiness, and recent activity. Sections can be
duplicated and the latest deletion undone; standard types offer starter Markdown.

The right pane serves the complete `dist/` tree, including CSS, scripts, assets, and nested pages.
Temporary template preview uses isolated `/draft-site/` output and does not change `config.yml`.
Use Template saves and rebuilds; Return to Current restores `/site/`. GUI, CLI, preview, and
deployment use the same builder.

Publish forms create a non-secret deployment job and immediately return control to the workspace.
A separate terminal runs the shared provider so OpenSSH or GitHub CLI can authenticate directly.
The left pane polls safe job status while the right preview stays usable. Closing that terminal
interrupts only the job; it does not close or damage the GUI. If no supported terminal can open,
the left pane provides a credential-free manual command. Export ZIP contains only `profile.md`,
`config.yml`, and `assets/`.
# Validation and recovery

URL fields validate after leaving the field and again on save. Domain-like values such as
`github.com/example` normalize to HTTPS; random text is rejected. Invalid submissions do not change
`profile.md`. If an external manual edit makes it invalid, Dashboard and navigation remain available
and Edit Profile uses a valid backup as a repair model when possible. Website icons accept managed
PNG or ICO files up to 2 MB.

## Imported TA templates

Converted TA designs appear in the ordinary Templates gallery and use the same Preview and Use
actions as built-in templates. Preview renders an isolated draft in the persistent right pane and
does not change the saved selection. Use saves the template and rebuilds the main preview. Imported
templates receive the same normalized Markdown data as all templates, so absent optional fields and
custom sections remain supported. The original `TA designs/` reference folder is not used by the
GUI or generated website.
