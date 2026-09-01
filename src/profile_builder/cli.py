from dataclasses import replace
from pathlib import Path
import argparse
import sys
import yaml
from .builder import build_site
from .config import load_config, save_config
from .preview import preview
from .profile import Profile, Section, _render, _slug, parse_profile, serialize_profile
from .mutations import set_asset, update_appearance, update_profile_fields
from .template_tools import check_template, create_template, format_info
from .templates import TemplateRegistry
from .utils import BuilderError
from .deployment import DeploymentRequest, IITDDeploymentProvider, IITDTarget
from .deployment import GitHubDeploymentRequest, GitHubPagesDeploymentProvider, GitHubSiteType


def list_templates(root: Path) -> dict:
    items = TemplateRegistry(root / "templates").discover()
    print("Available templates\n")
    for number, item in enumerate(items.values(), 1):
        print(f"{number}. {item.name}\n   ID: {item.id}\n   Engine: {item.engine}\n   Version: {item.version}")
        if item.executables: print(f"   Requirements: {', '.join(item.executables)}")
        print()
    return items


def mutate_section(root: Path,action: str,section_id: str | None=None,*,title: str="",kind: str | None="custom",content: str | None="") -> Profile:
    path=root/"profile.md"; profile=parse_profile(path,root); items=list(profile.sections)
    if action=="add":
        if not title.strip() or len(title)>120: raise BuilderError("Section title is required and must be at most 120 characters.")
        sid=_slug(title,{s.id for s in items}); items.append(Section(sid,title.strip(),kind,True,(len(items)+1)*10,content,_render(content)))
    else:
        index=next((i for i,s in enumerate(items) if s.id==section_id),None)
        if index is None: raise BuilderError("Section not found.")
        if action in {"hide","show"}: items[index]=replace(items[index],visible=action=="show")
        elif action=="edit":
            new_title=title.strip() or items[index].title
            if len(new_title)>120: raise BuilderError("Section title must be at most 120 characters.")
            new_content=items[index].markdown if content is None else content
            items[index]=replace(items[index],title=new_title,type=kind or items[index].type,markdown=new_content,html=_render(new_content))
        elif action=="delete": items.pop(index)
        elif action=="duplicate":
            item=items[index]; items.insert(index+1,replace(item,id=_slug(item.id,{s.id for s in items}),title=item.title+" Copy"))
        elif action=="move-up" and index>0: items[index-1],items[index]=items[index],items[index-1]
        elif action=="move-down" and index<len(items)-1: items[index+1],items[index]=items[index],items[index+1]
    serialize_profile(Profile(profile.data,profile.markdown,profile.html,tuple(items),profile.theme),path); return parse_profile(path,root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a student profile website.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate"); sub.add_parser("templates")
    profile_cmd=sub.add_parser("profile",help="Show or safely update profile fields").add_subparsers(dest="profile_action",required=True)
    profile_cmd.add_parser("show"); profile_set=profile_cmd.add_parser("set"); profile_set.add_argument("field"); profile_set.add_argument("value")
    appearance_cmd=sub.add_parser("appearance",help="Show or update website appearance").add_subparsers(dest="appearance_action",required=True)
    appearance_cmd.add_parser("show"); appearance_set=appearance_cmd.add_parser("set"); appearance_set.add_argument("--visitor-switching",choices=["on","off"],required=True); appearance_set.add_argument("--default",choices=["light","dark","system"],required=True)
    sections=sub.add_parser("sections",help="Manage profile sections").add_subparsers(dest="section_action",required=True)
    sections.add_parser("list"); section_add=sections.add_parser("add"); section_add.add_argument("title"); section_add.add_argument("--type",default="custom"); section_add.add_argument("--content",default="")
    section_edit=sections.add_parser("edit"); section_edit.add_argument("id"); section_edit.add_argument("--title"); section_edit.add_argument("--type"); section_edit.add_argument("--content")
    for action in ("hide","show","move-up","move-down","duplicate","delete"):
        item=sections.add_parser(action); item.add_argument("id")
    assets=sub.add_parser("assets",help="Manage photo, CV, and website icon").add_subparsers(dest="asset_kind",required=True)
    for kind in ("photo","cv","icon"):
        action=assets.add_parser(kind).add_subparsers(dest="asset_action",required=True); setter=action.add_parser("set"); setter.add_argument("path",type=Path); action.add_parser("remove")
    gui = sub.add_parser("gui", help="Start the local browser editor"); gui.add_argument("--port", type=int, default=8765); gui.add_argument("--no-browser", action="store_true")
    worker=sub.add_parser("deployment-worker",help=argparse.SUPPRESS); worker.add_argument("job_id"); worker.add_argument("--project-root",type=Path)
    for command in ("build", "preview"):
        child = sub.add_parser(command); child.add_argument("--template"); child.add_argument("--profile", type=Path)
    info = sub.add_parser("template-info"); info.add_argument("template_id")
    check = sub.add_parser("template-check"); check.add_argument("template_id"); check.add_argument("--profile", type=Path)
    create = sub.add_parser("template-create"); create.add_argument("template_id", nargs="?")
    create.add_argument("--name"); create.add_argument("--author"); create.add_argument("--engine", choices=["jinja", "static", "external-build"])
    deploy = sub.add_parser("deploy", help="Deploy a built static website")
    providers = deploy.add_subparsers(dest="provider", required=True)
    iitd = providers.add_parser("iitd", help="IITD public (Faculty/PhD) or IITD-network-only hosting",description="Public hosting is for IIT Delhi faculty and PhD students. Private hosting is available to IITD users with CSC home space and is accessible only from the IIT Delhi network.")
    iitd.add_argument("--target", choices=["public", "private"]); iitd.add_argument("--userid")
    iitd.add_argument("--template"); iitd.add_argument("--profile", type=Path)
    iitd.add_argument("--dry-run", action="store_true"); iitd.add_argument("--yes", action="store_true",
        help="confirm first-deployment overwrite risk")
    iitd.add_argument("--retries",type=int,choices=range(0,3),default=0,help="bounded high-level SSH retries after connection failure (0-2)")
    github = providers.add_parser("github", help="Deploy to GitHub Pages using git and GitHub CLI")
    github.add_argument("--site", choices=["personal", "project"]); github.add_argument("--repo")
    github.add_argument("--username", help="expected GitHub account; enables zero-network dry-run planning")
    github.add_argument("--template"); github.add_argument("--profile", type=Path)
    github.add_argument("--dry-run", action="store_true"); github.add_argument("--yes", action="store_true",
        help="confirm repository creation or replacement risks")
    return parser


def interactive(root: Path) -> int:
    while True:
        config = load_config(root / "config.yml"); registry = TemplateRegistry(root / "templates")
        current = registry.get(config.template)
        print("\n========================================\n       Student Profile Builder\n========================================")
        print(f"\nProfile: profile.md\nCurrent template: {current.name}")
        print("\n1. Validate profile\n2. List templates\n3. View template details\n4. Select template\n5. Build website")
        print("6. Preview website\n7. Deploy website\n8. Check template\n9. Create template skeleton\n10. Show configuration\n0. Exit")
        choice = input("\nSelect an option: ").strip()
        if choice == "1": parse_profile(root / "profile.md", root); print("Profile is valid.")
        elif choice == "2": list_templates(root)
        elif choice in {"3", "8"}:
            template_id = input("Template ID: ").strip()
            print(format_info(registry.get(template_id)) if choice == "3" else "\n".join(check_template(root, template_id)))
        elif choice == "4":
            items = list(list_templates(root).values()); answer = input("Choose template number: ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(items):
                selected = registry.get(items[int(answer)-1].id)
                save_config(root / "config.yml", replace(config, template=selected.id)); print("Template selected.")
            else: print("Invalid selection.")
        elif choice == "5": print(f"Website built in {build_site(root, config)}")
        elif choice == "6": preview(build_site(root, config), config.preview_port)
        elif choice == "7": _deployment_menu(root, config)
        elif choice == "9": _create_interactive(root)
        elif choice == "10": print(yaml.safe_dump(config.as_dict, sort_keys=False))
        elif choice == "0": return 0
        else: print("Please select a listed option.")


def _create_interactive(root: Path, template_id: str | None = None, name: str | None = None,
                        author: str | None = None, engine: str | None = None) -> Path:
    print("Create Template")
    template_id = template_id or input("Template ID: ").strip()
    name = name or input("Template name: ").strip()
    author = author or input("Author: ").strip()
    engine = engine or input("Engine (jinja/static/external-build): ").strip()
    return create_template(root, template_id, name, author, engine)


def _confirm_first() -> bool:
    print("\nThis appears to be the first Student Profile Builder deployment to this target.\n"
          "Generated files may replace files with the same names, including index.html.\n"
          "Files not managed by this tool will not be deleted.")
    return input("Continue? [y/N]: ").strip().lower() in {"y", "yes"}


def _deploy(root: Path, config, *, userid: str, target: str, template: str | None = None,
            profile: Path | None = None, dry_run: bool = False, assume_yes: bool = False,retries: int=0):
    print("Preparing deployment...")
    output = build_site(root, config, template_id=template, profile_path=profile)
    print("[OK] Static website built and validated")
    selected = IITDTarget.parse(target)
    provider = IITDDeploymentProvider(confirm_first=(lambda: True) if assume_yes else _confirm_first,retries=retries)
    result = provider.deploy(DeploymentRequest(output, userid, selected, dry_run))
    size = f"{result.total_bytes / 1024:.1f} KB"
    print(f"Deployment package: {result.file_count} files, {size}")
    if result.dry_run: print("Dry run completed successfully.")
    else: print("Website published successfully.")
    print(f"Expected website URL:\n{result.url}")
    return result


def _deployment_menu(root: Path, config) -> None:
    print("\nDeploy Website\n\n1. IIT Delhi\n2. GitHub Pages\n0. Back")
    choice = input("Selection: ").strip()
    if choice == "1": _deploy_interactive(root, config)
    elif choice == "2": _github_interactive(root, config)
    elif choice != "0": raise BuilderError("Invalid deployment provider selection.")


def _deploy_interactive(root: Path, config) -> None:
    print("\nIIT Delhi Deployment\n\n1. Public website (~/public_html)\n   Faculty and PhD students; publicly accessible.\n2. IITD-only website (~/private_html)\n   IITD users with CSC home space; IITD network only.\n0. Cancel")
    selection = input("Selection: ").strip()
    if selection == "0": return
    if selection not in {"1", "2"}: raise BuilderError("Invalid deployment target selection.")
    userid = input("IIT Delhi LDAP/User ID: ").strip()
    print("\nIIT Delhi authentication is handled directly by OpenSSH. You may be prompted multiple times during manifest check, secure upload, and install verification. Student Profile Builder never reads or stores your password.")
    _deploy(root, config, userid=userid, target="public" if selection == "1" else "private")


def _github_confirm(message: str, default: bool) -> bool:
    prompt = "[Y/n]" if default else "[y/N]"
    answer = input(f"{message} {prompt}: ").strip().lower()
    return default if not answer else answer in {"y", "yes"}


def _github_deploy(root: Path, config, *, site: str, repo: str | None, username: str | None,
                   template: str | None = None, profile: Path | None = None,
                   dry_run: bool = False, assume_yes: bool = False, allow_login: bool = False):
    print("Preparing GitHub Pages deployment...")
    output = build_site(root, config, template_id=template, profile_path=profile)
    print("[OK] Static website built and validated")
    provider = GitHubPagesDeploymentProvider(confirm=_github_confirm)
    result = provider.deploy(GitHubDeploymentRequest(output, GitHubSiteType.parse(site), repo, username,
                                                       dry_run, assume_yes, allow_login))
    print("\nGitHub deployment plan" if dry_run else "\nGitHub Pages deployment")
    print(f"Account: {result.username}\nRepository: {result.username}/{result.repository}\n"
          f"Site type: {site}\nPublishing branch: gh-pages\nFiles: {result.file_count}\n"
          f"Size: {result.total_bytes / 1024:.1f} KB\nExpected URL: {result.url}")
    if dry_run: print("\nDry run completed successfully.")
    elif not result.changed: print("\nWebsite is already up to date. No GitHub changes were required.")
    else: print("\nWebsite published successfully. GitHub Pages may take a few minutes to update.")
    return result


def _github_interactive(root: Path, config) -> None:
    print("\nGitHub Pages Deployment\n\nAuthentication is handled directly by GitHub CLI.\n"
          "The application never receives or stores your GitHub password or token.")
    site_choice = input("\n1. Personal site\n2. Project site\n0. Cancel\nSelection: ").strip()
    if site_choice == "0": return
    if site_choice not in {"1", "2"}: raise BuilderError("Invalid GitHub site type selection.")
    site = "personal" if site_choice == "1" else "project"
    repo = input("Repository name: ").strip() if site == "project" else None
    _github_deploy(root, config, site=site, repo=repo, username=None, allow_login=True)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv); root = Path.cwd()
    try:
        if not args.command: return interactive(root)
        if args.command=="deployment-worker":
            from .deployment_worker import run_worker
            worker_root=(args.project_root or root).resolve()
            if not (worker_root/"manage.py").is_file(): raise BuilderError("Deployment project root is invalid.")
            return run_worker(worker_root,args.job_id)
        config = load_config(root / "config.yml"); registry = TemplateRegistry(root / "templates")
        if args.command == "validate":
            profile=parse_profile(root/"profile.md",root); print("Profile valid.")
            starters=sum(any(marker in s.markdown for marker in ("Write your","Degree Name","Project Name","Course Name")) for s in profile.sections)
            if starters: print(f"\nWarnings:\n- {starters} section(s) contain starter text.")
            recommendations=[]
            if not profile.data.get("cv"): recommendations.append("Add a CV.")
            if not profile.data.get("photo"): recommendations.append("Add a profile photo.")
            if recommendations: print("\nRecommendations:\n"+"\n".join("- "+item for item in recommendations))
        elif args.command=="profile":
            if args.profile_action=="show": print(yaml.safe_dump(parse_profile(root/"profile.md",root).data,sort_keys=False,allow_unicode=True))
            else: update_profile_fields(root,{args.field:args.value}); print("Profile updated.")
        elif args.command=="appearance":
            if args.appearance_action=="show":
                theme=parse_profile(root/"profile.md",root).theme; print(f"Visitor switching: {'on' if theme.enabled else 'off'}\nDefault: {theme.default}")
            else: update_appearance(root,args.visitor_switching=="on",args.default); print("Appearance updated.")
        elif args.command=="sections":
            if args.section_action=="list":
                for section in parse_profile(root/"profile.md",root).sections: print(f"{section.id}\t{'visible' if section.visible else 'hidden'}\t{section.title}")
            else: mutate_section(root,args.section_action,getattr(args,"id",None),title=getattr(args,"title","") or "",kind=getattr(args,"type",None),content=getattr(args,"content",None)); print("Sections updated.")
        elif args.command=="assets":
            source=args.path if args.asset_action=="set" else None
            if source is not None and not source.is_file(): raise BuilderError(f"Asset file not found: {source}")
            set_asset(root,args.asset_kind,source); print(f"{args.asset_kind.title()} updated.")
        elif args.command == "templates": list_templates(root)
        elif args.command == "template-info": print(format_info(registry.get(args.template_id)))
        elif args.command == "template-check":
            item = registry.get(args.template_id, compatible=False); print(format_info(item), "\n")
            print("\n".join(check_template(root, args.template_id, args.profile))); print("\nTemplate check passed.")
        elif args.command == "template-create":
            path = _create_interactive(root, args.template_id, args.name, args.author, args.engine); print(f"Created {path}")
        elif args.command in {"build", "preview"}:
            output = build_site(root, config, template_id=args.template, profile_path=args.profile)
            if args.command == "build": print(f"Website built in {output}")
            else: preview(output, config.preview_port)
        elif args.command == "deploy" and args.provider == "iitd":
            userid = args.userid or input("IIT Delhi LDAP/User ID: ").strip()
            target = args.target
            if not target:
                choice = input("Target (public/private): ").strip(); target = choice
            _deploy(root, config, userid=userid, target=target, template=args.template,
                    profile=args.profile, dry_run=args.dry_run, assume_yes=args.yes,retries=args.retries)
        elif args.command == "deploy" and args.provider == "github":
            site = args.site or input("Site type (personal/project): ").strip()
            repo = args.repo
            if site == "project" and not repo: repo = input("Repository name: ").strip()
            _github_deploy(root, config, site=site, repo=repo, username=args.username,
                           template=args.template, profile=args.profile, dry_run=args.dry_run,
                           assume_yes=args.yes, allow_login=not args.dry_run)
        elif args.command == "gui":
            from .gui import run_gui
            run_gui(root, args.port, not args.no_browser)
        return 0
    except BuilderError as exc:
        print(f"Unable to complete the request.\n\n{exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
