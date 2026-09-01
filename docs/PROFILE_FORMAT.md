# Writing your profile

`profile.md` is the only source of truth for your academic information. The builder separates
the YAML front matter between the two `---` lines from the Markdown below it.

Legacy `# About`, `# Education`, and similar body headings remain valid and automatically become
ordered sections. A GUI save writes an explicit, human-readable `sections` list. Each section has
a unique lowercase/hyphen ID, independently editable title, semantic type, visibility, order, and
Markdown `content`. Types are presentation hints; `custom` always works. Hidden sections remain
stored but are omitted from output, and Publications/Projects/Awards are not required.

Generated-site theme settings are optional:

```yaml
theme:
  enabled: true
  default: system  # system, light, or dark
sections:
  - id: teaching
    title: Teaching and Mentoring
    type: teaching
    visible: true
    order: 10
    content: |
      ## Current courses
      Add Markdown here.
```

## Front matter

These text fields are required: `name`, `designation`, and `institute`. Optional fields are
`department`, `email`, `photo`, `cv`, `links`, and `research_interests`. Keep indentation with
spaces, not tabs.

```yaml
---
name: "Asha Student"
designation: "PhD Scholar"
department: "Computer Science and Engineering"
institute: "Indian Institute of Technology Delhi"
email: "asha@iitd.ac.in"
photo: "assets/asha.jpg"
cv: "assets/cv.pdf"
links:
  github: "https://github.com/asha"
  linkedin: ""
  scholar: "https://scholar.google.com/example"
  website: ""
research_interests:
  - Machine Learning
  - Responsible AI
---
```

Research interests use one `-` item per line. Links are indented key/value pairs; leave an
optional URL empty to hide it. Put images and documents in `assets/` and use an `assets/...`
relative path. Files outside the project cannot be referenced. Common image formats such as
JPEG, PNG, WebP, and SVG work in modern browsers.

## Markdown content

Below the second `---`, use `#` for major sections and `##` for entries. For example:

```markdown
# About

I study reliable learning systems.

# Education

## PhD in Computer Science

**IIT Delhi**  
2026 – Present

# Publications

1. A. Student, “Paper title,” *Venue*, 2026.

# Projects

## Project name

A short description and [project link](https://example.com).

# Awards

- Institute fellowship, 2026
```

Headings, bold, italic, links, ordered and unordered nested lists, tables, fenced code, inline code,
blockquotes, and horizontal rules are supported. Raw HTML is sanitized for safety; use Markdown
instead. Frequent mistakes include omitting one of the `---` boundaries, using tabs in YAML,
forgetting the space after `-`, misaligning link values, or referencing an image that was not
copied into `assets/`. Run `python manage.py validate` for a friendly diagnosis.

An optional `icon` field may point to a PNG or ICO inside `assets/`. GUI and CLI imports place it
under `assets/managed/`; generated pages use it as the browser icon. Without one, the builder's
default favicon is generated automatically.
