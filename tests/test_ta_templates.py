from pathlib import Path
import shutil
import re
import threading
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler, Request

import pytest

from conftest import ROOT, make_project
from profile_builder.builder import build_site, validate_output
from profile_builder.config import Config
from profile_builder.gui import create_server
from profile_builder.templates import TemplateRegistry
from profile_builder.utils import BuilderError


TA_TEMPLATES = (
    "ta-arya-editorial",
    "ta-balaji-tailwind",
    "ta-krishna-sidebar",
    "ta-yamini-research",
)


@pytest.mark.parametrize("template_id", TA_TEMPLATES)
@pytest.mark.parametrize("profile_name", ("minimal.md", "full.md", "stress-test.md"))
def test_imported_ta_templates_build_without_reference_sources(template_id, profile_name, tmp_path):
    root = make_project(tmp_path)
    profile = root / profile_name
    shutil.copy2(ROOT / "examples" / "profiles" / profile_name, profile)
    output = build_site(
        root,
        Config(),
        template_id=template_id,
        profile_path=profile,
        output_directory=root / f"output-{template_id}-{profile.stem}",
    )
    assert (output / "index.html").is_file()
    assert not validate_output(output)
    generated = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in output.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".json"}
    ).lower()
    assert "ta designs" not in generated
    assert "aarya.mehta@example.edu" not in generated


def test_imported_templates_are_discovered_and_reference_folder_is_ignored():
    registry = TemplateRegistry(ROOT / "templates").discover()
    assert set(TA_TEMPLATES) <= set(registry)
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/TA designs/" in ignored
    for template_id in TA_TEMPLATES:
        template = ROOT / "templates" / template_id
        assert template.is_dir()
        runtime_files = [path for path in template.rglob("*")
                         if path.is_file() and path.suffix.lower() in {".j2", ".css", ".js"}]
        assert not any("ta designs" in path.read_text(encoding="utf-8", errors="ignore").lower()
                       for path in runtime_files)


def test_imported_templates_appear_and_render_in_gui_draft_preview(tmp_path):
    root = make_project(tmp_path)
    shutil.copy2(ROOT / "examples" / "profiles" / "full.md", root / "profile.md")
    server = create_server(root, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    opener = build_opener(ProxyHandler({}))
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        gallery = opener.open(base + "/templates").read().decode()
        for template_id in TA_TEMPLATES:
            assert f'value="{template_id}"' in gallery
        csrf = re.search(r'name="csrf" value="([^"]+)', gallery).group(1)
        response = opener.open(Request(base + "/template/preview", data=urlencode({
            "csrf": csrf, "id": "ta-yamini-research"
        }).encode())).read().decode()
        assert "Yamini Research Systems" in response
        assert "/draft-site/" in response
        assert "template: basic" in (root / "config.yml").read_text(encoding="utf-8")
        draft = opener.open(base + "/draft-site/index.html").read().decode()
        assert "Asha Student" in draft and "Yamini Research Systems" not in draft
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("template_id", TA_TEMPLATES)
def test_imported_template_theme_capability_is_enforced(template_id, tmp_path):
    root = make_project(tmp_path)
    (root / "profile.md").write_text(
        "---\nname: Theme Student\ndesignation: Researcher\ninstitute: IIT Delhi\n"
        "theme: {enabled: true, default: dark}\nsections:\n"
        "- {id: custom-work, title: Custom Work, type: custom, content: 'A custom section.'}\n---\n",
        encoding="utf-8",
    )
    if template_id == "ta-arya-editorial":
        with pytest.raises(BuilderError, match="does not support"):
            build_site(root, Config(), template_id=template_id)
    else:
        output = build_site(root, Config(), template_id=template_id)
        html = (output / "index.html").read_text(encoding="utf-8")
        assert "theme" in html.lower() and "Custom Work" in html


@pytest.mark.parametrize("template_id", TA_TEMPLATES)
def test_offline_ta_templates_have_no_external_runtime_dependencies(template_id, tmp_path):
    root = make_project(tmp_path)
    shutil.copy2(ROOT / "examples" / "profiles" / "full.md", root / "profile.md")
    output = build_site(root, Config(), template_id=template_id)
    runtime = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                        for path in output.rglob("*") if path.is_file()
                        and path.suffix.lower() in {".html", ".css", ".js"})
    assert "cdn.tailwindcss.com" not in runtime
    assert "fonts.googleapis.com" not in runtime
    assert "https://" not in runtime.replace("https://github.com/example", "") \
        .replace("https://linkedin.com/in/example", "") \
        .replace("https://scholar.google.com/", "") \
        .replace("https://example.com", "")


def test_imported_templates_keep_distinct_table_designs():
    styles = {
        template_id: "\n".join(path.read_text(encoding="utf-8", errors="replace")
                                 for path in (ROOT / "templates" / template_id / "static").glob("*.css"))
        for template_id in TA_TEMPLATES
    }
    assert "color:var(--red)" in styles["ta-arya-editorial"]
    assert "border-radius:12px" in styles["ta-balaji-tailwind"] and "text-transform:uppercase" in styles["ta-balaji-tailwind"]
    assert "background:transparent" in styles["ta-krishna-sidebar"] and "td:nth-child(2)" in styles["ta-krishna-sidebar"]
    assert "var(--font-mono)" in styles["ta-yamini-research"] and "var(--line-strong)" in styles["ta-yamini-research"]


def test_imported_template_tables_fill_sections_and_project_links_survive_transforms():
    krishna_css = (ROOT / "templates/ta-krishna-sidebar/static/bottom.css").read_text(encoding="utf-8")
    yamini_css = (ROOT / "templates/ta-yamini-research/static/bottom.css").read_text(encoding="utf-8")
    krishna_js = (ROOT / "templates/ta-krishna-sidebar/static/presentation.js").read_text(encoding="utf-8")
    yamini_js = (ROOT / "templates/ta-yamini-research/static/presentation.js").read_text(encoding="utf-8")

    assert '[data-section-type="teaching"] table{display:table;width:100%' in krishna_css
    assert '[data-section-type="teaching"] table{display:table;width:100%' in yamini_css
    for script in (krishna_js, yamini_js):
        assert "textUntilBreak" in script
        assert "link.cloneNode(true)" in script
    assert "project-links" in krishna_js
    assert "proj-links" in yamini_js and "project-card" in yamini_js


def test_yamini_matches_reference_components_and_mobile_treatments():
    css = (ROOT / "templates/ta-yamini-research/static/bottom.css").read_text(encoding="utf-8")
    script = (ROOT / "templates/ta-yamini-research/static/presentation.js").read_text(encoding="utf-8")
    main = (ROOT / "templates/ta-yamini-research/static/main.js").read_text(encoding="utf-8")

    assert '[data-section-type="projects"] .has-entries{grid-auto-rows:1fr;align-items:stretch}' in css
    assert '[data-section-type="projects"] .project-card{margin-top:0!important}' in css
    assert '[data-section-type="teaching"] .section-body{overflow-x:visible}' in css
    assert 'td:nth-child(3)::before{content:"Role"}' in css
    assert '#datasets .dataset-card' in css and '.contact-meta' in css
    assert "classList.add('research-card')" in script
    assert "classList.add('research-card', 'dataset-card')" in script
    assert "period.className = 'period'" in script and "meta.className = 'contact-meta'" in script
    assert "educationEntries[0], ...experienceEntries" in script and "dataset.careerKind = 'experience'" in script
    assert "meta.textContent = strong.textContent.replace" in script and "body.className = 'news-body'" in script
    assert '.career-body .semantic-entry h2::before{content:none!important;display:none!important}' in css
    assert '[data-section-type="news"] .section-body{padding-left:0!important;border-left:0!important}' in css
    assert '.news-rail{border-left:1px solid var(--line)!important}' in css
    assert '.career-body .rail-item{margin-left:0!important;padding:0 0 36px!important' in css
    assert '.career-body .rail-item::before{left:-33px!important;top:6px!important}' in css
    assert '[data-section-type="teaching"] .mentor-list li:hover{transform:none}' in css
    assert '.news-rail .rail-item{position:relative;padding:0 0 36px!important' in css
    assert '.news-rail .rail-item::before{content:""!important;left:-33px!important;top:6px!important}' in css
    assert ".news-rail .news-body{margin:6px 0 0" in css
    assert "setAttribute('aria-pressed'" in main and "mobile.querySelectorAll('a')" in main


def test_arya_project_cards_use_reference_semantics_without_horizontal_overflow():
    css = (ROOT / "templates/ta-arya-editorial/static/bottom.css").read_text(encoding="utf-8")
    script = (ROOT / "templates/ta-arya-editorial/static/presentation.js").read_text(encoding="utf-8")
    template = (ROOT / "templates/ta-arya-editorial/index.html.j2").read_text(encoding="utf-8")

    assert "repeat(auto-fit,minmax(250px,1fr))" in css
    assert '[data-section-type="projects"] .markdown-body{overflow:visible}' in css
    assert '.semantic-entry:nth-child(2){background:#fff}' in css
    assert ".project-actions a" in css and ".news-copy" in css
    assert 'a[href^="mailto:"]:hover' in css
    assert "project-tag" in script and "open source" in script and "prototype" in script
    assert "classList.add('news')" in script and "classList.add('award-list')" in script
    assert "project-actions" in script and "time.nextSibling" in script
    assert "presentation.js" in template


def test_balaji_uses_reference_navigation_and_grouped_layout(tmp_path):
    root = make_project(tmp_path)
    shutil.copy2(ROOT / "profile.md", root / "profile.md")
    output = build_site(root, Config(), template_id="ta-balaji-tailwind")
    html = (output / "index.html").read_text(encoding="utf-8")
    css = "\n".join(path.read_text(encoding="utf-8") for path in
                    (output / "assets" / "template").glob("*.css"))
    assert '<details class="more-nav">' not in html
    assert '<div class="about-news">' in html
    assert 'id="education-experience" class="two-column feature-pair"' in html
    assert '<div class="misc-grid">' in html
    assert "Recent News" in html and "Contact" in html
    assert ".desktop-nav{overflow:visible" in css
    assert ".reference-main{margin:auto;padding:64px 24px" in css


def test_balaji_normalizes_projects_and_themes_teaching_table():
    css = (ROOT / "templates/ta-balaji-tailwind/static/layout.css").read_text(encoding="utf-8")
    script = (ROOT / "templates/ta-balaji-tailwind/static/presentation.js").read_text(encoding="utf-8")
    template = (ROOT / "templates/ta-balaji-tailwind/index.html.j2").read_text(encoding="utf-8")

    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in css
    assert '.semantic-entry:nth-child(3){grid-column' not in css
    assert ".project-subtitle" in css and ".project-technologies" in css
    assert ".project-actions .secondary-action" in css
    assert '[data-section-type="teaching"] .markdown-body table{display:table;width:100%' in css
    assert "tbody tr:hover td" in css and "prefers-reduced-motion:reduce" in css
    assert "splitProjectTitle" in script and "technologyNames" in script
    assert "primary-action" in script and "secondary-action" in script
    assert "presentation.js" in template


def test_balaji_has_local_dynamic_icons_and_dark_theme_colors():
    icon_script = (ROOT / "templates/ta-balaji-tailwind/static/icons.js").read_text(encoding="utf-8")
    css = (ROOT / "templates/ta-balaji-tailwind/static/layout.css").read_text(encoding="utf-8")
    base_css = (ROOT / "templates/ta-balaji-tailwind/static/style.css").read_text(encoding="utf-8")
    template = (ROOT / "templates/ta-balaji-tailwind/index.html.j2").read_text(encoding="utf-8")

    for section_type in ("about", "news", "research", "publication", "project", "education",
                         "experience", "teaching", "skill", "award"):
        assert f"['{section_type}'" in icon_script
    for action_icon in ("email", "github", "linkedin", "scholar", "globe", "file", "database"):
        assert f"{action_icon}:" in icon_script
    assert "section.dataset.sectionType" in icon_script
    assert "section.querySelector(':scope > h2, :scope > h3')" in icon_script
    assert "element.classList.add('has-ui-icon')" in icon_script
    assert "button.classList.add('has-ui-icon', 'icon-only')" in icon_script
    assert "icons.js" in template
    assert ".dark .section-icon" in css
    assert "a.has-ui-icon{display:inline-flex!important;align-items:center;gap:.45rem!important" in css
    assert ".control.icon-only:not(.menu-toggle){display:inline-grid;place-items:center" in css
    assert ".mobile-nav{display:none" in base_css
    assert ".menu-toggle{display:none}" in base_css
    assert "@media(max-width:767px){.desktop-nav{display:none}.menu-toggle{display:inline-grid" in base_css
    assert ".dark{" in base_css and "--surface:#172033" in base_css


def test_balaji_dark_build_keeps_local_icons_for_readded_named_sections(tmp_path):
    root = make_project(tmp_path)
    profile = (ROOT / "profile.md").read_text(encoding="utf-8")
    profile = profile.replace("default: light", "default: dark", 1)
    (root / "profile.md").write_text(profile, encoding="utf-8")
    output = build_site(root, Config(), template_id="ta-balaji-tailwind")
    html = (output / "index.html").read_text(encoding="utf-8")
    icons = output / "assets/template/icons.js"
    assert '<html lang="en" class="dark">' in html
    assert 'data-section-type="awards"' in html
    assert "icons.js" in html and icons.is_file()
    assert "section.dataset.sectionType" in icons.read_text(encoding="utf-8")
    assert "cdn" not in html.lower()


def test_imported_template_bottoms_and_list_markers_match_design_contract(tmp_path):
    root = make_project(tmp_path)
    profile_text = (ROOT / "profile.md").read_text(encoding="utf-8")
    (root / "profile.md").write_text(profile_text.replace("enabled: true", "enabled: false", 1), encoding="utf-8")
    expected = {
        "ta-arya-editorial": "Indian Institute of Technology Delhi</footer>",
        "ta-balaji-tailwind": "Contact &amp; References",
        "ta-krishna-sidebar": "Dr. Aarya Mehta</footer>",
        "ta-yamini-research": "Built as a portfolio template",
    }
    for template_id, footer_text in expected.items():
        output = build_site(root, Config(), template_id=template_id,
                            output_directory=root / f"bottom-{template_id}")
        html = (output / "index.html").read_text(encoding="utf-8")
        css = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                        for path in (output / "assets/template").glob("*.css"))
        assert footer_text in html
        assert ".markdown-body li::before{content:none}" in css


def test_imported_templates_preserve_source_layout_signatures():
    arya = (ROOT / "templates/ta-arya-editorial/index.html.j2").read_text(encoding="utf-8")
    balaji = (ROOT / "templates/ta-balaji-tailwind/index.html.j2").read_text(encoding="utf-8")
    krishna = (ROOT / "templates/ta-krishna-sidebar/index.html.j2").read_text(encoding="utf-8")
    yamini = (ROOT / "templates/ta-yamini-research/index.html.j2").read_text(encoding="utf-8")
    assert "Researching AI that is" in arya and "reliable, understandable, useful" in arya
    assert 'class="about-news"' in balaji and 'class="misc-grid"' in balaji
    assert 'class="mobile-header"' in krishna and "Let’s connect" in krishna
    assert 'id="hero-stats"' in yamini and "Career Trajectory" in yamini


def test_krishna_matches_reference_section_treatments_and_interactions():
    template = (ROOT / "templates/ta-krishna-sidebar/index.html.j2").read_text(encoding="utf-8")
    css = (ROOT / "templates/ta-krishna-sidebar/static/bottom.css").read_text(encoding="utf-8")
    script = (ROOT / "templates/ta-krishna-sidebar/static/presentation.js").read_text(encoding="utf-8")
    main = (ROOT / "templates/ta-krishna-sidebar/static/main.js").read_text(encoding="utf-8")
    assert 'id="theme-icon"' in template and "🌙" in template
    assert '[data-section-type="experience"] .has-entries{gap:32px;padding-left:0;border-left:0}' in css
    assert '[data-section-type="talks"] .semantic-entry' in css and 'border-left:2px solid var(--border)' in css
    assert '[data-section-type="projects"] .has-entries{grid-auto-rows:1fr;align-items:stretch}' in css
    assert '[data-section-type="projects"] .semantic-entry{display:flex;height:100%;min-height:270px;margin-top:0!important' in css
    assert '.section-anchor#datasets .markdown-body a{display:inline-flex' in css
    assert '.contact-details{display:grid;grid-template-columns:repeat(2' in css
    assert '.dark .section-anchor[data-section-type="contact"] .markdown-body{border:1px solid #3a3a3a;background:#171717' in css
    assert "contact.querySelectorAll(':scope > p')" in script and "metadata.replaceWith(details)" in script
    assert "headingPlace && strongText" in script and "\\d{4}|present|current" in script
    assert "email\\s*[,.]?\\s*$" in script
    assert "IntersectionObserver" in main and "aria-current" in main
    assert "page.scrollHeight - 12" in main and "activate(lastSection.id)" in main
    assert '.profile-card .theme-toggle{position:absolute;top:20px;right:20px;bottom:auto' in css
    assert '[data-section-type="awards"] li::before{content:"★"}' in css
    assert '[data-section-type="teaching"] .markdown-body{overflow-x:visible}' in css
    assert 'td:nth-child(3)::before{content:"Role"}' in css
    assert "prefers-reduced-motion:reduce" in css
