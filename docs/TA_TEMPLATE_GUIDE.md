# TA guide: designing Student Profile Builder templates

This guide is for teaching assistants who are assigned to improve an existing template or create
a new one. A template controls presentation only. Student information remains in `profile.md`, and
the builder converts that information into a normalized data object before rendering the site.

## Assignment boundary

Work inside one directory under `templates/`. For example:

```text
templates/modern-academic/
  template.yml
  index.html.j2
  README.md
  static/
    css/style.css
    js/main.js
    images/
```

Do not edit `profile.md`, the profile parser, deployment code, another TA's template, or generated
files in `dist/`. The `dist/` directory is deleted and recreated on every build.

To preserve an existing template, create a new copy with a new ID instead of redesigning the
original in place:

```powershell
python manage.py template-create modern-academic
```

The template folder name and `id` in `template.yml` must match. Use lowercase letters, numbers,
and hyphens.

## What the builder gives a template

Every template engine receives the same normalized object:

```text
schema_version
profile
  name                  required text
  designation           required text
  institute             required text
  department            optional text
  email                 optional text
  photo                  optional relative asset URL
  cv                     optional relative PDF URL
  icon                   optional relative icon URL
  links                  mapping of optional URLs
  research_interests     list of text values
theme
  enabled                boolean
  default                light, dark, or system
sections                 ordered list of visible sections
  id                     safe anchor/page identifier
  title                  display heading
  type                   presentation hint
  visible                boolean
  order                  number
  markdown               original Markdown text
  html                   sanitized rendered HTML
content
  markdown               complete legacy Markdown body
  html                   complete sanitized legacy HTML
site
  icon, template_id, template_name, template_version, generated_at
```

All optional values may be empty. A good template must still look intentional without a photo,
CV, email, social link, research interest, or conventional section such as Publications.

Student files are copied to `assets/user/...`. Files owned by the template are copied to
`assets/template/...`. Always use these relative URLs; never use a drive path or a URL beginning
with `/`.

## Rendering Markdown sections

The builder parses and sanitizes Markdown. Templates should normally render `sections`, not parse
Markdown themselves. This preserves the order selected in the UI and supports arbitrary custom
sections.

In Jinja:

```jinja2
<main>
  {% for section in sections %}
  <section id="{{ section.id }}" class="profile-section section-{{ section.type }}">
    <h2>{{ section.title }}</h2>
    <div class="markdown-body">{{ section.html | safe }}</div>
  </section>
  {% endfor %}
</main>
```

`section.html` and `content.html` are the only values intended for Jinja's `|safe`. Names, titles,
institutes, URLs, and all other ordinary fields must remain autoescaped.

The `type` value is a presentation hint, not a fixed list. It can be used to add layout or icons:

```css
.profile-section { padding-block: 3rem; }
.section-publications .markdown-body > ol { display: grid; gap: 1rem; }
.section-awards .markdown-body > ul { columns: 2; }
```

Always retain `.profile-section` as the generic fallback. Do not assume that Publications,
Projects, Education, Teaching, or Awards exists. Do not hide an unknown custom type.

For a static or external JavaScript template, insert ordinary fields with `textContent`. The
`section.html` value is sanitized by the builder and may be inserted into the designated Markdown
container:

```javascript
for (const section of data.sections) {
  const element = document.createElement('section');
  element.id = section.id;

  const heading = document.createElement('h2');
  heading.textContent = section.title;

  const body = document.createElement('div');
  body.className = 'markdown-body';
  body.innerHTML = section.html; // only builder-sanitized section.html

  element.append(heading, body);
  document.querySelector('main').append(element);
}
```

Never assign an ordinary profile value to `innerHTML` and never use `eval`.

## Choose an implementation stack

### Option 1: Jinja, HTML, CSS, and optional JavaScript

Use this for most templates. It has no Node dependency and renders profile data directly into
HTML. Start from `templates/basic/` or another existing Jinja template.

The essential manifest fields are:

```yaml
id: modern-academic
name: Modern Academic
version: "1.0.0"
author: Your Name
description: Responsive academic profile with a modern content structure.
engine: jinja
entry: index.html.j2
static_directory: static
compatibility:
  profile_schema: ["1.1"]
capabilities:
  profile_photo: true
  research_interests: true
  social_links: true
  markdown_content: true
  theme_switching: false
license: MIT
layout:
  mode: single-page
```

Reference assets from the entry as `./assets/template/css/style.css`. Student asset fields such
as `profile.photo` and `profile.cv` are already normalized and can be used directly.

### Option 2: prebuilt static HTML, CSS, and JavaScript

Use `engine: static` when the site needs no compilation. The builder copies the declared directory
and adds `profile-data.json` beside `index.html`.

```yaml
engine: static
source_directory: site
```

Load the data through HTTP:

```javascript
const data = await fetch('./profile-data.json').then(response => response.json());
document.querySelector('#student-name').textContent = data.profile.name;
```

Test through the builder preview; browser security normally prevents `fetch` from working when
`index.html` is opened directly through `file://`.

### Option 3: React, Vue, Svelte, Vite, Tailwind, or another build system

Use `engine: external-build`. The builder copies the template into a temporary directory, writes
the normalized data file, runs the declared command, and copies the compiled static result.

```yaml
engine: external-build
requirements:
  executables: [node, npm]
build:
  command: [npm, run, build]
  output_directory: dist
  data_file: public/profile-data.json
```

The final build must be static. It cannot require a Node server, Python server, PHP, database, API
route, server-side rendering service, or rewrite rules. Configure Vite or similar tools with a
relative base such as `./`. Prefer actual generated pages, no router, or a hash router. A browser
history router usually fails on IIT Delhi hosting and GitHub Pages.

Dependencies are not installed by Student Profile Builder. Include `package.json` and a lock file,
document the setup in the template README, and never commit `node_modules`.

## Structure and customization patterns

A single-page template can provide:

- a profile hero with name, designation, institute, photo, email, and Resume link;
- an optional navigation menu generated from `sections`;
- research-interest chips generated from `profile.research_interests`;
- one semantic `<section>` per Markdown section;
- optional social links rendered only when their URL exists;
- responsive typography and spacing rather than fixed desktop dimensions.

A multi-page template can group content or create one page per section. It must still generate an
`index.html`. Links from nested pages must account for their location, for example `../index.html`
and `../assets/template/css/style.css`. Test every nested page rather than only the home page.

Render optional data conditionally. A Jinja header might use:

```jinja2
{% if profile.photo %}
  <img src="{{ profile.photo }}" alt="Portrait of {{ profile.name }}">
{% endif %}

{% if profile.email %}<a href="mailto:{{ profile.email }}">Email</a>{% endif %}
{% if profile.cv %}<a href="{{ profile.cv }}" target="_blank" rel="noopener">Resume</a>{% endif %}

{% for label, url in profile.links.items() if url %}
  <a href="{{ url }}" rel="noopener">{{ label | replace('_', ' ') | title }}</a>
{% endfor %}
```

If `capabilities.theme_switching` is `true`, the template must implement a visible Light, Dark,
and System control when `theme.enabled` is true, apply `theme.default`, preserve readable contrast,
and hide the control when switching is disabled. Otherwise declare the capability as `false`.

## Development workflow

Run commands from the repository root:

```powershell
python manage.py template-info modern-academic
python manage.py build --template modern-academic --profile examples/profiles/full.md
python manage.py template-check modern-academic --profile examples/profiles/stress-test.md
python manage.py preview --template modern-academic
python -m pytest -q
```

Also test a minimal profile with every optional value empty. Check desktop, tablet, and mobile;
keyboard navigation; visible focus; heading order; color contrast; long names; Unicode text;
large section lists; portrait and landscape images; a CV link; and unknown custom section types.

The GUI Templates page can be used for visual comparison. **Preview** creates an isolated draft.
**Use** is the only action that saves the chosen template and rebuilds the main website.

For a complete approved set of fictional content, use
[`examples/profiles/ta-portfolio-dummy.md`](../examples/profiles/ta-portfolio-dummy.md). It includes
all common academic sections plus an unknown custom section and a hidden section for fallback and
conditional-layout testing.

## Required handoff

Submit the template directory with:

- a valid `template.yml`;
- source HTML/components, CSS, JavaScript, and local assets;
- a README naming the stack, setup/build command, supported features, and design decisions;
- licenses and attribution for fonts, libraries, icons, and other third-party assets;
- no generated `dist`, `node_modules`, credentials, analytics, or unrelated repository changes.

Before handoff, complete [TEMPLATE_CHECKLIST.md](TEMPLATE_CHECKLIST.md). The authoritative technical
rules remain in [TEMPLATE_CONTRACT.md](TEMPLATE_CONTRACT.md), with more examples in
[TEMPLATE_DEVELOPMENT.md](TEMPLATE_DEVELOPMENT.md).
