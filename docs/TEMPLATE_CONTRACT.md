# Template contract 1.0

This document is normative. “MUST”, “MUST NOT”, “SHOULD”, and “MAY” indicate requirement levels.

## Manifest

Every installed template MUST occupy `templates/<id>/` and contain `template.yml`. IDs MUST match
their directory and `^[a-z0-9]+(?:-[a-z0-9]+)*$`. The supported manifest version is `1.0`.

```yaml
manifest_version: "1.0"             # optional; defaults to 1.0
id: modern-research                  # required
name: Modern Research                # required
version: "1.0.0"                    # required
author: Developer Name               # recommended
description: Responsive profile.     # required
engine: jinja                         # required: jinja | static | external-build
compatibility:
  profile_schema: ["1.0"]            # optional; defaults to current 1.0
capabilities:                         # optional, descriptive booleans
  profile_photo: true
  research_interests: true
  social_links: true
  markdown_content: true
license: MIT                          # optional
third_party:                          # optional documentation
  - name: Bootstrap
    version: "5.3.x"
    source: bundled
```

Jinja MUST provide `entry` and MAY provide `static_directory`. Static MUST provide
`source_directory`. External-build MUST provide `build.command` as a YAML string array and MAY
provide `requirements.executables`, `build.output_directory` (default `dist`), and
`build.data_file` (default `profile-data.json`). Paths MUST be relative and remain within the
template. Unknown engines/versions are errors.

## Normalized data

Profile schema `1.0` has top-level `schema_version`, `profile`, `content`, and `site`. Exact fields
and types are documented in `TEMPLATE_DEVELOPMENT.md`. `profile.name`, `designation`, and
`institute` are non-empty strings. Optional strings can be empty; `links` is a mapping and
`research_interests` is a list. `content.markdown` is untrusted source text;
`content.html` is builder-sanitized HTML. Jinja MUST escape ordinary values and MAY mark only
`content.html` safe. New compatible fields MAY be added within schema 1.0; templates SHOULD ignore
unknown fields.

User asset URLs MUST use `assets/user/...`; template assets MUST use `assets/template/...`.
Contexts MUST NOT contain source-machine absolute paths.

### Profile schema 1.1 additions

Schema 1.1 additively exposes top-level `theme` and `sections`; all 1.0 fields remain. Templates
declaring 1.0 remain accepted during transition. `sections` is an ordered list of visible objects
with `id`, `title`, `type`, `visible`, `order`, `markdown`, and sanitized `html`. Templates MUST
provide a generic renderer for arbitrary types and MUST NOT require named conventional sections.

`theme` contains `enabled` and `default` (`light`, `dark`, or `system`). A template declaring
`capabilities.theme_switching: true` MUST show a visitor control only when enabled, respect the
default, and provide readable light/dark styling. A requested theme with an incapable template is
a build error.

## Engine behavior

- `jinja`: the adapter renders the entry with autoescaping and copies declared static assets.
- `static`: the adapter copies `source_directory` and emits `profile-data.json` at output root.
- `external-build`: the adapter copies source into an isolated temporary workspace, writes the
  data file, then runs the command with `subprocess`, argument arrays, `shell=False`. A zero exit
  code is required. Missing executables or output are errors. Commands originate only from trusted
  installed manifests; the builder MUST NOT auto-install dependencies.

## Output and security

Every engine MUST produce `index.html` and every runtime file MUST be below the final output.

Normalized `site.icon` is empty or a relative `assets/user/...` path to the optional managed PNG/ICO
website icon. Templates may use it directly; the builder also injects the selected icon, or its safe
fallback SVG, into generated HTML pages with page-relative paths.
Additional HTML pages and nested static trees MAY exist. Cross-page and asset links MUST remain
relative so every page works under IITD and GitHub Pages subpaths.
Output MUST be static and MUST NOT require a backend, database, PHP, Python server, or Node server.
URLs MUST be relative and work under arbitrary subpaths. Root-relative local asset URLs and local
filesystem paths are conformance errors.

Templates MUST treat student strings as untrusted, MUST NOT use `eval`, embed credentials, add
authentication, or transmit data without approval. External scripts SHOULD be minimal and
understandable. A build failure MUST return non-zero; successful external output MUST be in the
declared directory and contain `index.html`.

Manifests MAY specify `preview: preview.png` and `layout.mode` (`single-page` or `multi-page`) for
the gallery. These optional descriptive fields do not constrain output.

## Imported reference designs

An untracked/reference design directory is never part of the production template contract.
Converted templates MUST be self-contained below their installed `templates/<id>/` directory and
MUST NOT read or link to the import source at build time or runtime. Hardcoded sample-person content
MUST be replaced with normalized profile data or ordered sections. Imported designs MUST preserve a
generic fallback for every visible custom/unknown section type and MUST omit navigation for absent
sections and controls for absent optional assets.
