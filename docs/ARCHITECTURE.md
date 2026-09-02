# Architecture

Profile state has three layers: tracked canonical starter
(`defaults/profile.default.md`), ignored saved working copy (`profile.md`), and
ignored GUI draft (`.runtime/drafts/<session>/`). Builds and deployment use only saved
data; live preview reuses `build_site` with isolated input and output paths.

```text
profile.md → Profile Parser → Normalized Profile Model → Template Registry → Manifest
          → Renderer Adapter (Jinja | Static | External Build)
          → Validated Static Output → dist/ → Preview or DeploymentProvider
```

`profile.md` is the durable source of truth so students can switch presentation without
re-entering information. `config.yml` holds non-secret build choices. Templates are isolated
presentation packages; generated `dist/` is disposable and never feeds another build.

The parser/serializer normalizes fixed metadata, theme preference, and arbitrary ordered sections.
Legacy Markdown headings migrate in memory; GUI writes remain deterministic and human-editable.
CLI and localhost GUI share parser, serializer, builder, preview, registry, and deployment core.
The GUI binds to `127.0.0.1` and introduces no database.

The GUI shell is a persistent split workspace. The left route content is replaced through local
same-origin navigation while one right preview endpoint remains mounted. `/site/` maps only to
generated `dist/`; temporary template output is separately confined to `/draft-site/`. GUI rebuilds
use a complete candidate directory and replace `dist/` only after validation, preserving the last
successful preview if parsing or rendering fails.

`bootstrap.py` is the canonical source-distribution launcher. It uses standard-library `venv`,
direct platform-specific environment-Python paths, argument-array subprocesses with `shell=False`,
and a dependency fingerprint. Python packages remain inside `.venv`; optional system tools are
detected but never installed.

The parser safely loads YAML, normalizes optional fields, converts Markdown, and allowlist-
sanitizes HTML. A versioned serialization boundary supplies the same schema 1.0 context to all
renderers. The registry discovers and validates `templates/*/template.yml`; no IDs are hardcoded.

The renderer registry is deliberately small. Jinja renders directly with strict autoescaping.
Static copies prebuilt files and emits JSON. External-build copies trusted template source into a
temporary workspace, writes JSON, and runs an argument-array subprocess without a shell. External
commands cannot mutate installed template sources during normal builds. Every adapter must return
a backend-free site with `index.html`.

Student assets use `assets/user/`; presentation assets use `assets/template/`. All output URLs are
relative. Output validation rejects missing entry files, root-relative local asset URLs, and
obvious source-machine paths. Builds clean only the configured protected local output and preview
serves only that directory.

Build and deployment remain separate so providers consume the same already-validated static
output without coupling SSH behavior to parsing or rendering:

```text
DeploymentProvider
├── IITDDeploymentProvider (OpenSSH; Phase 3)
└── GitHubPagesDeploymentProvider (Git + GitHub CLI; Phase 4)
```

GUI publishing adds an isolation boundary:

```text
GUI request → .runtime/deployments/<random-id>.json → TerminalLauncher
            → separate deployment-worker process → existing provider
            → safe status JSON → GUI polling
```

Jobs contain only provider choices, public identifiers, state, timestamps, PID, URLs, and safe
messages. They never contain passwords, tokens, SSH keys, or authorization data. Worker failure or
terminal closure cannot terminate the GUI. Direct CLI deployment remains independent and first-class.

The IITD provider stages files remotely, installs only generated paths, and records ownership in
`.profile-builder-manifest.json`. A later deployment may remove only safe paths present in the old
valid manifest but absent from the new one. Unmanaged remote files are preserved. Authentication
and host verification remain entirely with OpenSSH; build logic never handles credentials.

GitHub deployment instead owns one dedicated generated-content branch. It copies `dist/` into an
isolated temporary Git repository, adds `.nojekyll` and `.profile-builder-pages.json`, and pushes
only `gh-pages`. An existing unmarked branch or conflicting Pages source requires confirmation.
GitHub CLI owns account authentication and API operations; Git owns commits and pushes. The
provider never changes the source/default branch or embeds credentials in remote URLs.

Templates may generate any static tree, including multiple pages; only `index.html` is mandatory.
Existing output validation and both deployment providers already scan/copy every generated file.

All entry points call one `build_site` service. Ignored `.profile-builder-state.json` stores only a
SHA-256 input fingerprint and build time for freshness reporting. GUI preview rebuilds before
mapping `/site/` to the complete output tree.

Profile mutations validate candidate data, serialize into a same-directory temporary file, reparse
that exact representation, and atomically replace `profile.md`. GUI and CLI use the same mutation
helpers. Invalid submissions cannot replace the source; when a manual edit damages it, the GUI
keeps navigation available and can use a valid `.bak` as its recovery editing model.
Save first validates and prebuilds the complete candidate, checks the saved-file fingerprint for external edits, promotes staged assets, atomically updates `profile.md`, and rebuilds `dist/`. Discard clears only runtime-owned draft data. Invalid candidates retain the most recent valid draft build.
