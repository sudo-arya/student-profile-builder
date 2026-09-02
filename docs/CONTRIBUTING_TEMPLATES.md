# Contributing templates

Student profile data is local. Never commit `profile.md`, `profile.md.bak`, personal photos/CVs,
`.runtime/`, `.venv/`, `local-templates/`, or files from `TA designs/`.

1. Create an ignored experiment with `python manage.py template-create my-template --name "My Template" --author "Your Name" --engine jinja --location local`.
2. Develop in `local-templates/my-template/`; tolerate missing optional fields and arbitrary sections.
3. Run `python manage.py template-contribution-check my-template --local`.
4. Test default, minimal, and stress profiles.
5. Promote with `python manage.py template-promote my-template`; existing templates are not overwritten.
6. Run `python manage.py template-check my-template` and the full suite.
7. Commit only reusable files under `templates/my-template/` and open a pull request.

Checks reject local dependencies, personal assets, absolute paths, secret-like files, missing
README files, and missing contributor credit. `TEMPLATE_CONTRACT.md` is normative.
