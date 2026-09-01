# Agent instructions

These rules apply throughout this repository.

- Inspect and preserve user/manual modifications before broad changes; the current filesystem is authoritative when Git metadata is unavailable.
- The GUI uses a persistent split workspace with preview permanently available on desktop and Edit/Preview switching on narrow screens.
- Normal successful saves rebuild and refresh the existing preview; they must not open another preview. Invalid edits preserve the last valid generated preview.
- `bootstrap.py` is the canonical environment bootstrap. Install core Python packages only inside project `.venv`, never globally, and never install Python itself.
- Never automatically install Git, GitHub CLI, OpenSSH, Node, or other system software. Optional tool absence must not block core editing and preview.
- Windows 10/11, desktop Linux, and macOS are supported. iPhone/iPad iOS is not a supported runtime.
- Platform convenience launchers must delegate to `bootstrap.py` and must not duplicate setup logic.
- GUI deployment must create a non-secret runtime job and launch `deployment-worker` in a separate terminal; never run interactive SSH/GitHub deployment inside an HTTP request.
- Deployment failures and closed terminals must not stop the GUI or damage profile/preview state. Job JSON and terminal arguments must never contain passwords or tokens.
- Cross-platform terminal launching belongs only in `TerminalLauncher`; missing terminals must produce a safe manual command fallback.

- Preserve `profile.md` as the content source of truth; never derive future source from `dist/`.
- Do not introduce a database, web framework, GUI, or deployment implementation without explicit instruction.
- Do not couple the core builder to one frontend framework. Normal new templates must not need core changes.
- Put generated output only in `dist/`; keep it disposable and never delete remote files from build code.
- Never collect, store, log, or commit credentials or passwords. Keep deployment providers separate from build logic.
- Keep Python and documentation cross-platform. Use `pathlib`, not hardcoded separators or shell assumptions.
- Validate all user-controlled paths and retain safe YAML loading, field escaping, and Markdown sanitization.
- Add or update isolated tests when parser, validation, registry, adapter, or build behavior changes.
- Keep the basic reference template intentionally simple; it documents the contract rather than setting a design direction.
- Preserve documented profile and template contracts where practical. Update all relevant documentation when they change.
- Supported engines are `jinja`, `static`, and `external-build`; every engine must produce static output with `index.html`.
- The normative contract is `docs/TEMPLATE_CONTRACT.md`. Normal templates must not modify core code.
- External commands come only from trusted manifests. Use argument arrays with `subprocess`, `shell=False`; never auto-install dependencies.
- Keep profile schema 1.0 and normalized context backwards-compatible where practical. Contract changes require documentation and tests.
- Run template conformance checks before finishing.
- IITD deployment uses the local OpenSSH client only. Never collect/store passwords, add password flags, use password automation, or disable host verification.
- `public_html` and `private_html` are explicit user choices; never infer the target from a degree or program.
- Never use broad destructive remote commands or recursively chmod unrelated content. Remove only safe paths in the previous valid builder manifest.
- The sole recursive remote-delete exception is `$HOME/.student-profile-builder-upload-<32 lowercase hex>`, generated internally for the current deployment. It may be removed with `rm -rf -- "$stage"` after install verification; never apply this to public_html, private_html, `$HOME`, or a user-provided path. Cleanup failure after verification is a warning, not deployment failure.
- Automated tests must never contact IITD infrastructure; mock SSH/SCP. Keep deployment separate from builders/renderers.
- A future GitHub provider must use the same provider boundary and supported authentication tooling.
- GitHub authentication belongs to `gh`; never collect/store GitHub passwords or tokens, retrieve tokens, or inspect credential stores.
- GitHub deployment uses only `git` and `gh`; do not add a separate authenticated API client without explicit instruction.
- GitHub Pages publishes from `gh-pages` root with `.nojekyll` and a builder ownership marker.
- Never overwrite main/master or another source branch. An unmanaged `gh-pages` branch requires confirmation.
- Keep temporary deployment Git workspaces outside the project and `dist`; never embed credentials in remote URLs.
- GitHub tests must fake Git/GitHub CLI and never modify real repositories. Preserve IITD provider behavior.
- `profile.md` remains source of truth; the GUI must not introduce database persistence.
- Keep fixed metadata separate from arbitrary ordered sections; never require Publications, Projects, or Awards.
- Theme controls require both user enablement and declared template capability; capable templates expose a visitor toggle.
- Multi-page static templates are supported; only `index.html` is mandatory.
- CLI and GUI share core services. GUI binds to `127.0.0.1` and never collects deployment credentials.

Verify changes from the repository root:

```text
python -m pytest
python manage.py validate
python manage.py templates
python manage.py build
python manage.py template-check basic
python manage.py deploy iitd --target public --userid test-user --dry-run
python manage.py deploy github --site project --repo test-profile --username test-user --dry-run
python -m compileall -q src tests manage.py
```

Then inspect `dist/index.html`, confirm referenced assets exist and paths remain relative, and
briefly serve `dist/` when preview behavior changes. Never perform a real deployment during automated verification.

All build entry points must call `build_site`; GUI preview rebuilds and serves the full output tree.
UI wording distinguishes template theme capability from user configuration. Build-state metadata
is generated and non-sensitive. GUI deployment reuses providers and keeps authentication in the
starting terminal.

- Never persist an invalid profile. Validate candidate state and its serialized temporary file before atomically replacing `profile.md`; GUI and CLI mutations must use shared services.
- User-data and validation errors are not HTTP 500 errors and must never make GUI navigation or recovery actions inaccessible.
- Validate social/site URLs before save. Empty values remain valid; normal social/site URLs use HTTP or HTTPS.
- IITD privateweb URLs use `http://`. Public IITD guidance identifies Faculty and PhD eligibility; IITD-only hosting is the alternative for IITD users with CSC home space. Never infer a student's program.
- OpenSSH owns credentials and prompt-level retries. Never capture passwords; any high-level connection retry must be bounded.
- Markdown tables are supported content and must remain permitted by sanitization. A website icon is optional and must use validated managed PNG/ICO assets.
- `TA designs/` is read-only reference/import input: preserve it, do not commit it, and never make production code or generated sites depend on it.
- Converted TA designs belong under `templates/`; replace hardcoded sample-person data with normalized profile context and ordered sanitized sections.
- Imported templates must tolerate missing optional profile fields, render arbitrary/custom sections, and preserve the original TA visual design where practical.
- Before replacing the root demo profile with imported sample content, create a dedicated backup; keep the resulting demo coherent, representative, and valid.
