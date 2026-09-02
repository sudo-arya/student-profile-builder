# Developing a template

Use `--location local` for ignored experiments, `template-contribution-check` for
privacy/portability checks, and `template-promote` for a validated copy into
tracked `templates/`. See `CONTRIBUTING_TEMPLATES.md`.

You are developing only a website template. The profile builder supplies normalized student
data and expects an ordinary static website in return. Do not change `profile.md`, the parser,
CLI, deployment code, or another template unless the maintainers coordinate a contract change.
The normative rules are in [TEMPLATE_CONTRACT.md](TEMPLATE_CONTRACT.md); use the
[submission checklist](TEMPLATE_CHECKLIST.md) before handoff.

## Recommended workflow

```powershell
python manage.py template-create modern-research
python manage.py template-info modern-research
python manage.py build --template modern-research --profile examples/profiles/full.md
python manage.py template-check modern-research --profile examples/profiles/stress-test.md
python manage.py preview --template modern-research
```

`template-create` asks for a name, author, and engine if flags are omitted. It creates a starter,
not a finished design. `--template` is temporary and does not modify `config.yml`. Develop in
`templates/<template-id>/`; submit that directory and its README/build files only.

## Choosing an engine

### Jinja: HTML, CSS, JavaScript, or Bootstrap

Choose `jinja` when Python can render the page directly. The entry receives `schema_version`,
`profile`, `content`, and `site`. Ordinary variables are autoescaped. `content.html` has already
been sanitized by the builder and is the only value intended for `|safe`. Static files declared
by `static_directory` become `assets/template/`.

Bootstrap is fine. Bundle production assets where practical and document CDNs or third-party
assets. Never assume that the site is hosted at `/`.

### Static: prebuilt HTML/CSS/JavaScript

Choose `static` when the template is already a static site. The builder copies `source_directory`
and writes `profile-data.json` beside `index.html`. Load it over the preview HTTP server:

```javascript
fetch('./profile-data.json').then(r => r.json()).then(data => {
  document.querySelector('#name').textContent = data.profile.name;
});
```

`fetch` generally does not work correctly from `file://`; use `python manage.py preview`. Use DOM
text APIs for student strings. `content.html` is sanitized, but do not use arbitrary profile
values with `innerHTML`.

### External build: React, Vite, Tailwind, or other toolchains

Choose `external-build` when the template needs its own compiler. Example:

```yaml
engine: external-build
requirements:
  executables: [node, npm]
build:
  command: [npm, run, build]
  output_directory: dist
  data_file: public/profile-data.json
```

The builder copies the installed template to a temporary workspace, writes normalized JSON,
checks executables, and runs the command with no shell interpolation. It then copies the declared
output. React/Vite should generate a production static single-page site, avoid server-dependent
routing, and configure a relative base such as `base: './'`. Tailwind must emit compiled CSS.
Node/npm is a build dependency for that template only and is never required on IITD hosting.
The builder never installs missing tools automatically.

Installed templates are trusted developer code: manifest commands execute locally. Keep scripts
small, reviewable, and free of unrelated file/network access. Never derive commands from profile
data. See `examples/templates/external-build-example` for a dependency-free demonstration.

## Data and assets

The JSON/Jinja contract is identical for every engine:

```json
{
  "schema_version": "1.0",
  "profile": {
    "name": "Asha Student", "designation": "PhD Scholar",
    "department": "Computer Science", "institute": "IIT Delhi",
    "email": "asha@iitd.ac.in", "photo": "assets/user/photo.jpg",
    "cv": "assets/user/cv.pdf", "links": {"github": "https://github.com/example"},
    "research_interests": ["Machine Learning"]
  },
  "content": {"markdown": "# About...", "html": "<h1>About</h1>..."},
  "site": {
    "generator": "Student Profile Builder 0.1.0", "template_id": "modern-research",
    "template_name": "Modern Research", "template_version": "1.0.0",
    "generated_at": "2026-08-13T12:00:00+00:00"
  }
}
```

Student assets always appear under `assets/user/`; template assets appear under
`assets/template/`. The context never contains local absolute paths. Optional strings may be
empty, mappings may be empty, and lists may be empty. Your page must handle those states.

## Quality expectations

Test the minimal, full, and stress profiles. Support current Chrome, Edge, Firefox, and Safari;
legacy-browser work is not required. Use semantic HTML, meaningful alt text, keyboard-accessible
controls, visible focus states, a sensible heading hierarchy, sufficient contrast, and labels for
any controls. Test desktop, tablet, and mobile layouts.

Keep pages lean: optimize images, avoid massive JavaScript bundles and autoplay video, lazy-load
non-critical images where useful, and avoid unnecessary libraries. All final URLs must be
relative so the site works under IITD `~userid/` and GitHub project subpaths.

Treat every student field as untrusted. Do not use `eval`, unsanitized `innerHTML`, embedded API
keys, authentication, unapproved analytics/tracking, or forms that silently transmit data. Do not
send profile data to third parties unnecessarily. Document external fonts, CDNs, licenses, and
third-party assets in the manifest/README.

Package distribution may later use a zip containing `template.yml`, source, and README. Phase 2
does not download, install, or execute untrusted remote packages.

## Phase 5 sections, themes, and page trees

The current additive profile schema is `1.1`. Every engine receives `theme` (`enabled`, `default`)
and ordered visible `sections`. Each section contains `id`, `title`, semantic `type`, `order`,
`markdown`, and sanitized `html`. Render arbitrary/custom sections with a generic fallback; never
require Publications, Projects, or Awards.

Declare `capabilities.theme_switching: true` only when the template conditionally renders a visible
visitor toggle, respects Light/Dark/System, persists browser choice where practical, and maintains
contrast. Do not render the toggle when disabled.

Templates may emit one page, multiple HTML files/directories, or a static SPA. `index.html` alone
is mandatory. Use relative cross-page links. React should prefer no routes, `HashRouter`, or actual
static pages; `BrowserRouter` usually needs rewrite rules unavailable on simple IITD/GitHub hosting.

Templates MAY add `preview: preview.png` and `layout: {mode: single-page}` or `multi-page` for the
student gallery. These are optional descriptive metadata.

## Reference template architectures

- `basic`: Jinja single page with a linear academic layout and theme switching.
- `basic-multipage`: external-build reference producing grouped pages plus a page for every custom section.
- `basic-hybrid`: external-build landing page with one detail page per section.
- `examples/templates/static-example`: static HTML/JS loading normalized `profile-data.json`.
- `examples/templates/external-build-example`: stand-in for React/Vite, Tailwind, or another static compiler.

TAs may use HTML/CSS, Bootstrap, Tailwind, React/Vite, or another reviewed static framework. A
template may be a single page, multi-page tree, SPA, or hybrid. Final output must contain
`index.html`, remain entirely below `dist/`, use relative and subpath-safe links, retain arbitrary
custom sections, tolerate missing optional fields, and honor its declared theme capability. The
builder does not install Node or any other dependency.

## Imported TA Reference Designs

TA static mockups may be used as read-only visual references, but production adaptations belong in
`templates/<id>/` and must satisfy the same manifest, normalized-data, output, and security contract
as every other template. Modify the tracked converted template rather than relying on the ignored
`TA designs/` source folder. A converted template should retain the source design language while
replacing hardcoded identity/content with normalized profile fields and ordered sections. It must
omit missing optional data, render unknown/custom types, avoid dead navigation, style sanitized
Markdown (including responsive tables), and contain every required runtime asset. Compiled frontend
output without its source project should normally be adapted to Jinja or static output instead of
inventing an external build pipeline.
