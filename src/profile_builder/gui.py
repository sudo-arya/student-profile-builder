"""Local student-facing GUI; all build work delegates to core services."""
from dataclasses import dataclass, replace
from datetime import datetime
from email.parser import BytesParser
from email.policy import default as email_policy
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib, json, mimetypes, secrets, shutil, socket, sys, threading, traceback, webbrowser, zipfile
from urllib.request import urlopen

from .build_state import build_status
from .builder import build_site
from .config import load_config, save_config
from .profile import Profile, Section, Theme, _render, _slug, parse_profile, serialize_profile
from .templates import TemplateRegistry
from .utils import BuilderError
from .mutations import import_asset_bytes, validate_web_url
from .deployment import DeploymentRequest, IITDDeploymentProvider, IITDTarget
from .deployment import GitHubDeploymentRequest, GitHubPagesDeploymentProvider, GitHubSiteType
from .deployment.iitd import validate_userid
from .deployment.github_pages import deployment_identity
from .deployment_jobs import DeploymentJobStore, TerminalLauncher, worker_command
from .workspace import (ensure_working_profile, restore_default_profile,
                        save_profile_text, validate_profile_text)

GUI_HOST, GUI_PORT = "127.0.0.1", 8765
STARTERS = {"about":"Write a short academic introduction.","education":"### Degree Name\n\n**Institution Name**  \nYear – Year","publications":"1. **Paper title**\n   Authors  \n   Conference or Journal, Year","projects":"### Project Name\n\nShort project description.","research":"Describe your research.","experience":"### Role\n\n**Organization**  \nYear – Year","teaching":"### Course Name\n\nCourse description.","awards":"- Award name, Year","news":"- **Date** — Update","custom":""}


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    content_type: str
    data: bytes


def _basic_profile_fields(profile: Profile) -> str:
    """Render profile inputs without Python 3.12-only f-string expressions."""
    rendered=[]
    for name in ("name","designation","department","institute","email"):
        attributes='type="email" autocomplete="email"' if name == "email" else ""
        label=escape(name.title())
        value=escape(str(profile.data.get(name,"")))
        rendered.append(f'<label>{label}<input {attributes} name="{name}" value="{value}"></label>')
    return "".join(rendered)


def _online_profile_fields(links: dict[str, str]) -> str:
    rendered=[]
    validation=(
        "if(this.value&amp;&amp;!/^[a-z]+:/i.test(this.value)&amp;&amp;"
        "/^(?:[a-z0-9-]+[.])+[a-z]{2,}(?:[/:?#].*)?$/i.test(this.value))"
        "this.value='https://'+this.value;let ok=!this.value;"
        "try{let u=new URL(this.value);ok=ok||((u.protocol==='http:'||"
        "u.protocol==='https:')&amp;&amp;u.host)}catch(e){ok=false}"
        "this.setCustomValidity(ok?'':'Please enter a complete URL starting with http:// or https://');"
        "this.nextElementSibling.textContent=this.validationMessage"
    )
    for name in ("github","linkedin","scholar","website"):
        placeholder="github.com/username" if name == "github" else "example.com"
        label=escape(name.title())
        value=escape(str(links.get(name,"")))
        rendered.append(
            f'<label>{label}<input type="url" inputmode="url" autocomplete="url" '
            f'placeholder="https://{placeholder}" name="link_{name}" value="{value}" '
            f'onblur="{validation}"><small class="field-error" aria-live="polite"></small></label>'
        )
    return "".join(rendered)


def _section_type_options(section: Section) -> str:
    rendered=[]
    for value in dict.fromkeys(tuple(STARTERS)+(section.type,)):
        if value not in STARTERS and value != section.type: continue
        selected=" selected" if value == section.type else ""
        rendered.append(f'<option value="{escape(value)}"{selected}>{escape(value.title())}</option>')
    return "".join(rendered)


def _layout(title: str, body: str, message: str = "") -> bytes:
    notice=f'<p class="notice" role="status">{escape(message)}</p>' if message else ""
    body=body.replace("[link](https://example.com)</pre>","[link](https://example.com)\n\n| Year | Degree |\n|---|---|\n| 2026 | PhD |\n\n```python\nprint('hello')\n```</pre>")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(title)}</title><link rel="icon" href="/favicon.ico"><style>
:root{{--bg:#eef1f5;--surface:#fff;--surface-muted:#f1f3f6;--text:#172033;--text-muted:#5f6b7a;--border:#d8dee7;--primary:#244f86;--primary-hover:#193f70;--danger:#a12a2a;--radius-sm:.4rem;--radius-md:.7rem;--shadow-sm:0 2px 10px #17203312;--space-xs:.35rem;--space-sm:.65rem;--space-md:1rem;--space-lg:1.35rem}}*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}body{{font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--text);overflow:hidden}}.app-header{{height:64px;display:flex;align-items:center;gap:1rem;padding:.65rem 1rem;background:var(--surface);border-bottom:1px solid var(--border)}}.app-header h1{{font-size:1.05rem;margin:0;white-space:nowrap}}.workspace-nav{{display:flex;gap:.2rem;flex-wrap:wrap}}.workspace-nav a{{position:relative}}.workspace-nav a[aria-current=page]{{background:var(--surface-muted);font-weight:700}}.global-status{{margin-left:auto;font-size:.86rem;color:var(--text-muted);white-space:nowrap}}.workspace{{height:calc(100vh - 64px);display:grid;grid-template-columns:minmax(340px,var(--split,45%)) 6px minmax(360px,1fr)}}.editor-pane,.preview-pane{{min-width:0;overflow:auto}}.editor-pane{{padding:0 1rem 3rem;background:var(--bg)}}.divider{{background:var(--border);cursor:col-resize}}.divider:hover{{background:var(--primary)}}.preview-pane{{display:flex;flex-direction:column;background:#dfe4eb}}.preview-toolbar{{display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;padding:.55rem .7rem;background:var(--surface);border-bottom:1px solid var(--border)}}.preview-toolbar strong{{margin-right:auto}}#preview-status{{font-size:.82rem;color:var(--text-muted)}}.preview-actions{{display:none;width:100%;padding-top:.35rem;border-top:1px solid var(--border)}}.preview-actions.show{{display:flex;align-items:center;gap:.4rem}}.preview-stage{{flex:1;overflow:auto;padding:12px;text-align:center}}#site-preview{{display:block;width:100%;max-width:100%;height:100%;min-height:500px;margin:auto;border:1px solid #bcc5d0;background:#fff;box-shadow:0 2px 12px #17203320}}.pane-tabs{{display:none}}section,.card{{background:var(--surface);padding:var(--space-lg);margin:var(--space-md) 0;border:1px solid var(--border);border-radius:var(--radius-md);box-shadow:var(--shadow-sm)}}h2{{font-size:1.15rem}}label{{display:block;margin:.75rem 0;color:var(--text-muted);font-weight:600}}input,textarea,select{{width:100%;padding:.62rem .7rem;border:1px solid #aeb8c5;border-radius:var(--radius-sm);background:#fff;color:var(--text);font:inherit}}textarea{{min-height:9rem;font-family:ui-monospace,monospace}}button,.button{{display:inline-block;padding:.48rem .72rem;margin:.1rem;border:1px solid #9ca8b7;border-radius:var(--radius-sm);background:var(--surface);color:var(--text);font:inherit;font-weight:600;text-decoration:none;cursor:pointer}}button:hover,.button:hover{{background:var(--surface-muted);border-color:#738195}}.primary{{background:var(--primary);border-color:var(--primary);color:#fff}}.primary:hover{{background:var(--primary-hover)}}.secondary{{background:var(--surface-muted)}}.ghost{{border-color:transparent;background:transparent}}.danger{{color:var(--danger);border-color:#e3b9b9;background:#fffafa}}button:disabled,[aria-disabled=true]{{opacity:.48;cursor:not-allowed}}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{{outline:3px solid #79a9df;outline-offset:2px}}.notice{{padding:.75rem 1rem;background:#e9f6ec;border:1px solid #b9ddc1;border-radius:var(--radius-sm)}}.grid,.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:var(--space-md)}}.cards .card{{margin:0;min-height:0}}.status,.badge{{font-weight:700}}.badge{{display:inline-block;padding:.16rem .48rem;border-radius:999px;background:var(--surface-muted);font-size:.78rem}}small,.muted{{color:var(--text-muted)}}details>summary{{cursor:pointer;padding:.45rem;border-radius:var(--radius-sm)}}.sticky-save{{position:fixed;left:22%;bottom:1rem;z-index:10;background:#172033;color:#fff;padding:.6rem .8rem;border-radius:var(--radius-md);box-shadow:0 5px 20px #0003;display:none}}.sticky-save.show{{display:flex;align-items:center;gap:.8rem}}.file-input::file-selector-button{{padding:.45rem .65rem;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-muted);cursor:pointer}}
@media(max-width:760px){{body{{overflow:auto}}.app-header{{height:auto;min-height:64px;flex-wrap:wrap}}.global-status{{margin-left:0}}.pane-tabs{{display:flex;margin-left:auto}}.workspace{{height:calc(100vh - 112px);display:block}}.divider{{display:none}}.editor-pane,.preview-pane{{height:100%}}.workspace[data-mobile-pane="edit"] .preview-pane,.workspace[data-mobile-pane="preview"] .editor-pane{{display:none}}.sticky-save{{left:50%;transform:translateX(-50%)}}}}
</style></head><body><header class="app-header"><h1>Student Profile Builder</h1><nav class="workspace-nav"><a class="button ghost" href="/">Dashboard</a><a class="button ghost" href="/profile">Edit Profile</a><a class="button ghost" href="/templates">Templates</a><a class="button ghost" href="/publish">Publish</a></nav><span class="global-status">Saved ✓ · <span id="global-preview-state">Checking preview…</span></span><div class="pane-tabs" role="group" aria-label="Workspace pane"><button data-pane="edit">Edit</button><button data-pane="preview">Preview</button></div></header><div class="workspace" data-mobile-pane="edit"><section class="editor-pane" aria-label="Builder"><main id="workspace-content">{notice}{body}</main></section><div class="divider" role="separator" aria-label="Resize workspace panes" tabindex="0"></div><aside class="preview-pane" aria-label="Responsive Preview"><div class="preview-toolbar"><strong>Live Site Preview</strong><span id="preview-status">Checking…</span><button data-width="100%">Desktop</button><button data-width="768px">Tablet</button><button data-width="390px">Mobile</button><button id="preview-refresh">Refresh</button><a class="button" target="_blank" href="/site/">Open in New Tab</a><div class="preview-actions" id="preview-actions"><span id="draft-label"></span><button class="primary" id="use-draft">Use Template</button><button id="return-current">Return to Current</button></div></div><div class="preview-stage"><iframe id="site-preview" title="Generated website live preview" src="/site/"></iframe></div></aside></div><div class="sticky-save" role="status"><span>Unsaved changes</span><button class="primary" type="button" data-save-draft>Save</button><button type="button" data-discard-draft>Discard</button></div><dialog id="unsaved-dialog"><h2>You have unsaved changes</h2><p>Your preview includes changes that are not saved to profile.md.</p><button value="stay">Stay</button><button value="discard">Discard Changes</button><button class="primary" value="save">Save &amp; Continue</button></dialog><script>
const workspace=document.querySelector('.workspace'),pane=document.querySelector('.editor-pane'),frame=document.getElementById('site-preview'),status=document.getElementById('preview-status'),globalState=document.getElementById('global-preview-state'),bar=document.querySelector('.sticky-save');let dirtyForm=null,lastFingerprint='',lastPreview='/site/',draftActive=false,draftTimer=null,livePreviewPending=false,previewDebounce=450,previewRequest=0,previewController=null;
const stateStyle=document.createElement('style');stateStyle.textContent='.state-pill{{display:inline-flex;align-items:center;min-height:1.55rem;padding:.18rem .58rem;border:1px solid transparent;border-radius:999px;font-size:.78rem;font-weight:750;line-height:1.1;white-space:nowrap}}.state-neutral{{color:#526174;background:#edf1f5;border-color:#d8dee7}}.state-success{{color:#17643a;background:#e8f6ed;border-color:#b7dfc5}}.state-warning{{color:#7a5200;background:#fff3cd;border-color:#ead28a}}.state-danger{{color:#922c2c;background:#fdeaea;border-color:#efbaba}}';document.head.appendChild(stateStyle);status.classList.add('state-pill','state-neutral');globalState.classList.add('state-pill','state-neutral');const savedLabel=document.querySelector('.global-status');if(savedLabel){{savedLabel.childNodes[0].remove();const saved=document.createElement('span');saved.className='state-pill state-success';saved.textContent='Saved ✓';savedLabel.prepend(saved,' ')}}
const openPreview=document.querySelector('.preview-toolbar a[target="_blank"]');openPreview.href='/preview-window';
function setState(el,text,tone){{el.textContent=text;el.classList.remove('state-neutral','state-success','state-warning','state-danger');el.classList.add('state-pill','state-'+tone)}}
function activeNav(){{document.querySelectorAll('.workspace-nav a').forEach(a=>{{a.removeAttribute('aria-current');const p=new URL(a.href).pathname;if(p===location.pathname||(p!=='/'&&location.pathname.startsWith(p)))a.setAttribute('aria-current','page')}})}}
async function guardUnsaved(){{if(!draftActive&&dirtyForm?.dataset.liveKind)await previewStructured(dirtyForm);if(!draftActive&&!dirtyForm)return true;const d=document.getElementById('unsaved-dialog');return new Promise(resolve=>{{d.showModal();d.onclick=async e=>{{if(!e.target.value)return;d.close();if(e.target.value==='stay')return resolve(false);if(e.target.value==='discard'){{await draftAction('/profile/draft-discard');return resolve(true)}}resolve(await draftAction('/profile/draft-save'))}}}})}}
async function loadLeft(url,push=true){{if(!await guardUnsaved())return;const scroll=pane.scrollTop,r=await fetch(url,{{headers:{{'X-Workspace':'1'}}}}),text=await r.text(),doc=new DOMParser().parseFromString(text,'text/html'),next=doc.querySelector('#workspace-content');if(!next){{location.href=url;return}}document.querySelector('#workspace-content').replaceWith(next);if(push)history.pushState({{}},'',r.url);document.title=doc.title;dirtyForm=null;bar.classList.remove('show');activeNav();pane.scrollTop=push?0:scroll;await syncPreview(true)}}
document.addEventListener('click',e=>{{const tab=e.target.closest('[data-pane]');if(tab){{workspace.dataset.mobilePane=tab.dataset.pane;return}}const a=e.target.closest('a');if(!a||a.target||a.hasAttribute('download'))return;const u=new URL(a.href);if(u.origin===location.origin&&!u.pathname.startsWith('/site/')&&!u.pathname.startsWith('/asset/')&&!u.pathname.startsWith('/draft-site/')){{e.preventDefault();loadLeft(u.href)}}}});
document.addEventListener('click',async e=>{{const tab=e.target.closest('[data-editor-tab]');if(tab){{if(tab.dataset.editorTab==='structured'&&draftActive){{const r=await fetch('/profile?draft=1',{{headers:{{'X-Workspace':'1'}}}}),text=await r.text(),doc=new DOMParser().parseFromString(text,'text/html'),next=doc.querySelector('#workspace-content');if(next)document.querySelector('#workspace-content').replaceWith(next);return}}document.querySelectorAll('[data-editor-panel]').forEach(p=>p.hidden=p.dataset.editorPanel!==tab.dataset.editorTab);document.querySelectorAll('[data-editor-tab]').forEach(b=>b.classList.toggle('primary',b===tab));return}}const save=e.target.closest('[data-save-draft]'),discard=e.target.closest('[data-discard-draft]');if(save)await saveCurrentDraft();if(discard)draftAction('/profile/draft-discard',true)}});
function scheduleStructuredPreview(form){{dirtyForm=form;livePreviewPending=!!form.dataset.liveKind;bar.classList.add('show');if(form.dataset.liveKind){{setState(status,'Updating preview…','warning');setState(globalState,'Unsaved changes','warning');clearTimeout(draftTimer);draftTimer=setTimeout(()=>previewStructured(form),previewDebounce)}}}}
document.addEventListener('input',e=>{{const raw=e.target.closest('[data-raw-draft]');if(raw){{draftActive=true;bar.classList.add('show');clearTimeout(draftTimer);draftTimer=setTimeout(()=>previewRaw(raw.value),500);return}}const f=e.target.closest('form[data-dirty]');if(f)scheduleStructuredPreview(f)}});document.addEventListener('change',e=>{{const f=e.target.closest('form[data-dirty]');if(f)scheduleStructuredPreview(f)}});
async function previewRaw(markdown){{status.textContent='Updating preview…';const data=new URLSearchParams({{csrf:window.workspaceCsrf,markdown}}),s=await fetch('/profile/raw-preview',{{method:'POST',body:data}}).then(r=>r.json());draftActive=s.unsaved;bar.classList.toggle('show',draftActive);const error=document.querySelector('[data-draft-error]');if(error){{error.hidden=s.valid;error.textContent=s.valid?'':'Markdown has errors. Preview shows last valid content. '+s.error}}await syncPreview(true)}}
async function previewStructured(form){{if(!form.isConnected||!form.reportValidity()){{livePreviewPending=false;return}}const request=++previewRequest;if(previewController)previewController.abort();previewController=new AbortController();setState(status,'Updating preview…','warning');setState(globalState,'Unsaved changes','warning');const data=new FormData(form);data.set('csrf',window.workspaceCsrf);data.set('draft_kind',form.dataset.liveKind);try{{const r=await fetch('/profile/structured-preview',{{method:'POST',body:data,signal:previewController.signal}}),s=await r.json();if(request!==previewRequest)return;if(!r.ok)throw new Error(s.error||'Draft validation failed');draftActive=!!s.unsaved;livePreviewPending=false;if(!draftActive)dirtyForm=null;const raw=document.querySelector('[data-raw-draft]');if(raw&&s.markdown)raw.value=s.markdown;await syncPreview(true)}}catch(e){{if(e.name==='AbortError'||request!==previewRequest)return;livePreviewPending=false;setState(status,'Preview paused — '+(e.message||'invalid draft'),'danger')}}}}
async function saveCurrentDraft(){{if(dirtyForm){{const edit=dirtyForm.querySelector('button[name="action"][value="edit"]');dirtyForm.requestSubmit(edit||undefined);return}}const raw=document.querySelector('[data-raw-draft]');if(raw){{clearTimeout(draftTimer);await previewRaw(raw.value)}}if(draftActive)await draftAction('/profile/draft-save',true)}}
async function draftAction(path,reload=false){{const data=new URLSearchParams({{csrf:window.workspaceCsrf}}),r=await fetch(path,{{method:'POST',body:data}});if(!r.ok)return false;draftActive=false;dirtyForm=null;bar.classList.remove('show');if(reload){{const u=new URL('/profile',location.origin);const text=await r.text();location.href=r.url;return true}}await syncPreview(true);return true}}
document.addEventListener('submit',async e=>{{const f=e.target;if(!f.matches('form'))return;e.preventDefault();const destination=f.getAttribute('action')||location.pathname;if((destination==='/template/select'||destination==='/profile/restore-default')&&!await guardUnsaved())return;status.textContent='Updating…';globalState.textContent='Updating…';const data=new FormData(f);if(e.submitter?.name)data.set(e.submitter.name,e.submitter.value);const r=await fetch(destination,{{method:(f.method||'post').toUpperCase(),body:data}}),text=await r.text(),doc=new DOMParser().parseFromString(text,'text/html'),next=doc.querySelector('#workspace-content');if(next){{document.querySelector('#workspace-content').replaceWith(next);history.replaceState({{}},'',r.url);document.title=doc.title;dirtyForm=null;bar.classList.remove('show');activeNav();await syncPreview(true)}}else location.href=r.url}});
async function postAction(path,id){{const data=new URLSearchParams({{csrf:window.workspaceCsrf,id:id||''}});await fetch(path,{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:data}});await loadLeft('/templates',false)}}
async function syncPreview(force=false){{try{{const s=await fetch('/api/build-status',{{cache:'no-store'}}).then(r=>r.json()),url=s.preview_url||'/site/';draftActive=!!s.live_active;bar.classList.toggle('show',draftActive||!!dirtyForm||livePreviewPending);if(force||url!==lastPreview||s.fingerprint!==lastFingerprint){{frame.src=url+'?build='+encodeURIComponent(s.fingerprint||Date.now());lastPreview=url;lastFingerprint=s.fingerprint}}const pendingDirty=!!dirtyForm&&!s.live_active&&!s.live_error;if(s.live_error)setState(status,'Preview paused — invalid draft','danger');else if(s.live_active)setState(status,'Unsaved preview','warning');else if(pendingDirty||livePreviewPending)setState(status,'Updating preview…','warning');else if(s.previewing)setState(status,'Temporary preview','neutral');else setState(status,'Synced ✓','success');if(s.live_active||pendingDirty||livePreviewPending)setState(globalState,'Unsaved changes','warning');else if(s.current)setState(globalState,'Ready ✓','success');else setState(globalState,'Preview shows last valid build','danger');window.workspaceCsrf=s.csrf;const actions=document.getElementById('preview-actions');actions.classList.toggle('show',!!s.previewing);document.getElementById('draft-label').textContent=s.previewing?'Previewing '+s.previewing:'';document.getElementById('use-draft').onclick=()=>postAction('/template/select',s.preview_template);document.getElementById('return-current').onclick=()=>postAction('/template/return')}}catch(e){{setState(status,'Preview unavailable','danger');setState(globalState,'Needs attention','danger')}}}}
async function syncDeployment(){{const box=document.querySelector('[data-deployment-job]');if(!box)return;try{{const job=await fetch('/api/deployments/'+box.dataset.deploymentJob,{{cache:'no-store'}}).then(r=>r.json());box.querySelector('[data-job-state]').textContent=job.state==='running'?'Publishing…':job.state;box.querySelector('[data-job-message]').textContent=job.message||'';const result=box.querySelector('[data-job-result]');if(['success','warning'].includes(job.state))result.innerHTML='<p><strong>Published successfully</strong></p><p><a class="button primary" target="_blank" href="'+job.url+'">Open Website</a> '+(job.repository_url?'<a class="button" target="_blank" href="'+job.repository_url+'">Open Repository</a> ':'')+'<button type="button" data-copy-url>Copy URL</button></p>';if(['failed','interrupted','cancelled'].includes(job.state))result.innerHTML='<p class="notice"><strong>Publishing did not complete.</strong><br>Your local profile and preview are unchanged.<br>Review the deployment terminal for details.</p>';result.querySelector('[data-copy-url]')?.addEventListener('click',()=>navigator.clipboard.writeText(job.url))}}catch(e){{}}}}
document.querySelectorAll('[data-width]').forEach(b=>b.onclick=()=>{{frame.style.width=b.dataset.width;localStorage.setItem('profile-preview-mode',b.dataset.width)}});frame.style.width=localStorage.getItem('profile-preview-mode')||'100%';document.getElementById('preview-refresh').onclick=()=>{{frame.src=lastPreview+'?refresh='+Date.now()}};addEventListener('keydown',e=>{{if((e.ctrlKey||e.metaKey)&&e.key==='s'&&(dirtyForm||draftActive)){{e.preventDefault();saveCurrentDraft()}}}});addEventListener('beforeunload',e=>{{if(draftActive||dirtyForm){{e.preventDefault();e.returnValue=''}}}});addEventListener('popstate',()=>loadLeft(location.href,false));activeNav();syncPreview();syncDeployment();setInterval(()=>syncPreview(),1200);setInterval(()=>syncDeployment(),1500);
const divider=document.querySelector('.divider');let resizing=false;divider.onpointerdown=e=>{{resizing=true;divider.setPointerCapture(e.pointerId)}};divider.onpointermove=e=>{{if(!resizing)return;const pct=Math.max(25,Math.min(70,e.clientX/innerWidth*100));workspace.style.setProperty('--split',pct+'%');localStorage.setItem('profile-workspace-split',pct)}};divider.onpointerup=()=>resizing=false;const savedSplit=localStorage.getItem('profile-workspace-split');if(savedSplit)workspace.style.setProperty('--split',savedSplit+'%');
</script></body></html>'''.encode()


def _human_time(value: str | None) -> str | None:
    if not value: return None
    try: return datetime.fromisoformat(value).astimezone().strftime("%d %b %Y, %I:%M %p").replace(", 0",", ")
    except ValueError: return value


def create_server(root: Path, port: int = GUI_PORT, open_browser: bool = False, terminal_launcher=None) -> ThreadingHTTPServer:
    if port:
        with socket.socket() as probe:
            probe.settimeout(.2)
            if probe.connect_ex((GUI_HOST,port)) == 0: raise OSError(f"Port {port} is already in use")
    root=root.resolve(); ensure_working_profile(root); token=secrets.token_urlsafe(24); deleted:list[Section]=[]; activity:list[str]=[]
    jobs=DeploymentJobStore(root); launcher=terminal_launcher or TerminalLauncher()
    state={"preview_open":False,"preview_template":None,"draft_active":False,
           "live_active":False,"live_valid":False,"live_error":"","live_text":"",
           "live_profile":None,"live_revision":0,"live_output":root/".runtime/live-preview-0","live_building":False,
           "draft_base_revision":"","draft_assets":{},"draft_deleted":[]}; flashes:list[str]=[]
    # A build replaces an output tree while preview requests read from it.  On
    # Windows an open file handle prevents that replacement, so serialize the
    # short filesystem read with promotion of both saved and draft previews.
    output_lock=threading.RLock()
    def rebuild_saved():
        """Keep the previous generated site until its replacement is fully valid."""
        config=load_config(root/"config.yml"); target=(root/config.output_directory).resolve()
        with output_lock:
            return build_site(root,config,output_directory=target)
    try: rebuild_saved()
    except BuilderError: pass
    def safe_profile():
        try: return parse_profile(root/"profile.md",root),None
        except BuilderError as error:
            try: return parse_profile(root/"profile.md.bak",root),str(error)
            except BuilderError: return None,str(error)
    def saved_text():
        return (root/"profile.md").read_text(encoding="utf-8")
    def profile_revision(text=None):
        return hashlib.sha256((saved_text() if text is None else text).encode("utf-8")).hexdigest()
    def initialize_draft(force=False):
        """Start one canonical editor draft without changing profile.md or dist/."""
        if force or not state["live_text"]:
            text=saved_text(); next_revision=state["live_revision"]
            try:
                candidate=validate_profile_text(root,text,directory=root/".runtime/drafts/current")
                draft_profile=parse_profile(candidate,root); repair_error=""; dirty=False
            except BuilderError as error:
                draft_profile,problem=safe_profile()
                if draft_profile is None: raise
                candidate=root/".runtime/drafts/current/profile.md"
                serialize_profile(draft_profile,candidate,backup=False,project_root=root)
                text=candidate.read_text(encoding="utf-8"); repair_error=problem or str(error); dirty=True
            live_output=root/".runtime"/"drafts"/"current"/f"site-{next_revision}"
            with output_lock: build_site(root,profile_path=candidate,output_directory=live_output)
            state.update({"live_text":text,"live_profile":draft_profile,
                "live_active":dirty,"live_valid":True,"live_error":repair_error,"draft_base_revision":profile_revision(),
                "draft_assets":{},"draft_deleted":[],"live_revision":next_revision,"live_output":live_output})
        return state["live_profile"]
    def clear_draft():
        stage=(root/"assets/.drafts"/token).resolve(); owned=(root/"assets/.drafts").resolve()
        if stage.is_dir() and owned in stage.parents: shutil.rmtree(stage,ignore_errors=True)
        if owned.is_dir() and not any(owned.iterdir()): owned.rmdir()
        runtime=(root/".runtime").resolve()
        for generated in tuple(runtime.glob("live-preview-*")) if runtime.is_dir() else ():
            if generated.parent==runtime and generated.is_dir(): shutil.rmtree(generated,ignore_errors=True)
        draft_root=(runtime/"drafts").resolve()
        if draft_root.parent==runtime and draft_root.is_dir(): shutil.rmtree(draft_root,ignore_errors=True)
        state.update({"live_active":False,"live_valid":False,"live_error":"","live_text":"","live_profile":None,
                      "draft_base_revision":"","draft_assets":{},"draft_deleted":[]})
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def send(self,body:bytes,status=200,kind="text/html; charset=utf-8"):
            if status==200 and kind.startswith("text/html") and flashes:
                extra=f'<p class="notice" role="status">{escape(flashes.pop(0))}</p>'
                if state["draft_deleted"]: extra+=f'<form method="post" action="/section/undo"><input type="hidden" name="csrf" value="{token}"><button>Undo delete</button></form>'
                marker=b'<main id="workspace-content">'
                body=body.replace(marker,marker+extra.encode(),1)
            try:
                self.send_response(status); self.send_header("Content-Type",kind); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
                # Navigation commonly cancels polling and iframe requests mid-response.
                self.close_connection=True
        def form(self):
            n=int(self.headers.get("Content-Length","0"))
            if n>20*1024*1024: raise BuilderError("Upload is too large (20 MB request limit).")
            data=self.rfile.read(n); content_type=self.headers.get("Content-Type","")
            if not content_type.lower().startswith("multipart/form-data"):
                return {k:v[-1] for k,v in parse_qs(data.decode(),keep_blank_values=True).items()}
            msg=BytesParser(policy=email_policy).parsebytes(b"Content-Type: "+content_type.encode()+b"\r\nMIME-Version: 1.0\r\n\r\n"+data)
            result={}
            for part in msg.iter_parts():
                name=part.get_param("name",header="content-disposition")
                if not name: continue
                filename=part.get_filename(); payload=part.get_payload(decode=True) or b""
                result[name]=UploadedFile(filename or "",part.get_content_type(),payload) if filename else payload.decode("utf-8")
            return result
        def csrf(self,f):
            if f.get("csrf")!=token: raise BuilderError("Invalid local form token. Reload and try again.")
        def do_GET(self):
            try:
                path=urlparse(self.path).path
                if path=="/": return self.home()
                if path=="/profile": return self.profile_page()
                if path=="/templates": return self.templates_page()
                if path=="/preview": return self.preview_page()
                if path=="/preview-window": return self.preview_window()
                if path=="/publish": return self.publish_page()
                if path=="/export": return self.export_profile()
                if path=="/favicon.ico": return self.send(b"",kind="image/x-icon")
                if path=="/api/health": return self.send(json.dumps({"application":"student-profile-builder","status":"ok"}).encode(),kind="application/json")
                if path=="/api/build-status": return self.build_status_api()
                if path=="/api/draft": return self.draft_api()
                if path.startswith("/api/deployments/"): return self.deployment_status(path.rsplit("/",1)[-1])
                if path.startswith("/asset/"): return self.asset_file(path[7:])
                if path.startswith("/draft-site/"): return self.output_file(root/"preview-draft",path[12:])
                if path.startswith("/live-site/"): return self.output_file(state.get("live_output",root/".runtime/live-preview-0"),path[11:])
                if path.startswith("/site/"): return self.site_file(path[6:])
                self.send(b"Not found",404,"text/plain")
            except BuilderError as e: self.send(_layout("Error","<h2>Needs attention</h2>",str(e)),400)
            except Exception:
                traceback.print_exc(); self.send(_layout("Something went wrong",'<section><h2>Something went wrong while processing this page.</h2><p>Your profile files were not intentionally changed.</p><a class="button" href="/">Return to Dashboard</a><a class="button" href="/profile">Edit Profile</a></section>'),500)
        def redirect(self,location,message=""):
            if message: flashes.append(message)
            self.send_response(303); self.send_header("Location",location); self.send_header("Content-Length","0"); self.end_headers()
        def sync_preview(self):
            rebuild_saved(); state.update({"preview_template":None,"draft_active":False,"live_active":False,
                                           "live_valid":False,"live_error":"","live_text":"","live_profile":None})
        def do_POST(self):
            try:
                f=self.form(); self.csrf(f); path=urlparse(self.path).path
                {"/profile/save":self.save_profile,"/profile/raw-preview":self.raw_preview,
                 "/profile/structured-preview":self.structured_preview,
                 "/profile/draft-save":lambda _:self.save_draft(),"/profile/draft-discard":lambda _:self.discard_draft(),
                 "/profile/restore-default":lambda _:self.restore_default(),
                 "/section/add":self.add_section,"/section/action":self.section_action,"/section/undo":lambda _:self.undo(),"/template/select":self.select_template,"/template/preview":self.preview_template,"/template/return":lambda _:self.return_template(),"/appearance":self.appearance,"/build":lambda _:self.build(),"/deploy/iitd":self.deploy_iitd,"/deploy/github":self.deploy_github}[path](f)
            except KeyError: self.send(b"Not found",404,"text/plain")
            except BuilderError as e:
                path=urlparse(self.path).path
                if path in {"/profile/raw-preview","/profile/structured-preview"}:
                    state["live_valid"]=False; state["live_error"]=str(e)
                    return self.send(json.dumps({"valid":False,"unsaved":True,"error":str(e),"revision":state["live_revision"]}).encode(),400,"application/json")
                if path=="/profile/save": return self.redirect("/profile#profile-details",str(e))
                self.send(_layout("Error","<h2>Please correct the problem</h2>",str(e)),400)
            except Exception:
                path=urlparse(self.path).path
                traceback.print_exc()
                if path in {"/profile/raw-preview","/profile/structured-preview"}:
                    state["live_valid"]=False; state["live_error"]="The generated preview is temporarily in use. Please try again."
                    return self.send(json.dumps({"valid":False,"unsaved":True,"error":state["live_error"],"revision":state["live_revision"]}).encode(),500,"application/json")
                self.send(_layout("Something went wrong",'<section><h2>Something went wrong while processing this request.</h2><p>Your profile files were not intentionally changed.</p><a class="button" href="/">Return to Dashboard</a><a class="button" href="/profile">Edit Profile</a></section>'),500)
        def home(self):
            c=load_config(root/"config.yml"); p,problem=safe_profile(); t=TemplateRegistry(root/"templates").get(c.template)
            if p is None: return self.send(_layout("Dashboard",f'<section><h2>Profile needs attention</h2><p>Some values in profile.md are invalid.</p><pre>{escape(problem or "Unknown profile error")}</pre><p><a class="button primary" href="/profile">Fix Profile</a> <a class="button secondary" href="/templates">View Templates</a></p><p class="muted">File: {escape(str(root/"profile.md"))}</p></section>'))
            supports=bool(t.capabilities.get("theme_switching")); current,last=build_status(root,t.id,root/c.output_directory); last=_human_time(last)
            checks=[bool(p.data.get(k)) for k in ("name","designation","institute","photo","email","cv")]+[bool(p.data["research_interests"]),any(p.data["links"].values()),any(s.visible for s in p.sections)]; completeness=round(100*sum(checks)/len(checks)); missing=[label for key,label in (("photo","profile photo"),("email","email"),("cv","CV")) if not p.data.get(key)]
            appearance=(f'<p class="notice"><strong>Profile needs attention.</strong> Showing the last valid backup. Use Edit Profile to repair it.<br><small>{escape(problem)}</small></p>' if problem else '')+f"<p>Template supports theme switching: <strong>{'Yes' if supports else 'No'}</strong></p><p>Visitor theme control: <strong>{'On' if p.theme.enabled else 'Off'}</strong></p><p>{'Initial appearance' if p.theme.enabled else 'Site appearance'}: <strong>{escape(p.theme.default.title())}</strong></p>"
            options=''.join(f'<option {"selected" if p.theme.default==v else ""}>{v}</option>' for v in ("system","light","dark")); recent=''.join(f'<li>{escape(x)}</li>' for x in activity[-5:]) or '<li>No activity this session.</li>'
            tools={name:bool(shutil.which(name)) for name in ("ssh","scp","git","gh")}; environment=f'''<section><h2>Environment</h2><p>Python {escape(sys.version.split()[0])} · Isolated interpreter: <code>{escape(sys.executable)}</code></p><div class="grid"><div><strong>Core application</strong><br><span class="status">Ready ✓</span></div><div><strong>IITD deployment</strong><br>{'Ready ✓' if tools['ssh'] and tools['scp'] else 'Unavailable — OpenSSH client missing'}</div><div><strong>GitHub Pages</strong><br>{'Ready ✓' if tools['git'] and tools['gh'] else ('Git ready; GitHub CLI missing' if tools['git'] else 'Git and/or GitHub CLI missing')}</div></div><small>System deployment tools are checked but never installed automatically.</small></section>'''
            body=f'''<div class="cards"><div class="card"><h2>Profile</h2><h3>{escape(p.data['name'])}</h3><p>{escape(p.data['designation'])}</p><p class="status">Completeness: {completeness}%</p><p class="muted">{'Recommended: '+', '.join(missing) if missing else 'Profile looks complete.'}</p><a class="button" href="/profile">Edit Profile</a><a class="button" href="/export">Export</a></div><div class="card"><h2>Template</h2><h3>{escape(t.name)}</h3><p>Theme support: {'Yes' if supports else 'No'} · Layout: {escape(t.layout_mode.replace('-',' ').title())}</p><a class="button" href="/templates">Change</a></div><div class="card"><h2>Appearance</h2>{appearance}<form method="post" action="/appearance"><input type="hidden" name="csrf" value="{token}"><label><input style="width:auto" type="checkbox" name="enabled" {'checked' if p.theme.enabled else ''} {'disabled' if not supports else ''}> Allow visitor theme switching</label><label>Default<select name="default" {'disabled' if not supports else ''}>{options}</select></label><button {'disabled' if not supports else ''}>Configure Appearance</button></form>{'<a href="/templates">Choose a theme-capable template</a>' if not supports else ''}</div><div class="card"><h2>Website</h2><p class="status">Status: {'Up to date' if current else 'Needs rebuild'}</p><p>Last build: {escape(last or 'Not built yet')}</p><form method="post" action="/build"><input type="hidden" name="csrf" value="{token}"><button class="secondary">Build now</button></form><p>{'Ready to publish' if current else 'Needs attention: build before publishing'}</p></div><div class="card"><h2>Publish</h2><p>Use existing secure deployment providers.</p><a class="button" href="/publish">Publish Website</a><p><small>No passwords or tokens are collected.</small></p></div></div><section><h2>Recent activity</h2><ul>{recent}</ul></section>{environment}'''; self.send(_layout("Dashboard",body))
        def profile_page(self):
            if not state["live_text"]: initialize_draft()
            p,problem=(state["live_profile"],state["live_error"] or None) if state["live_profile"] is not None else safe_profile()
            if p is None: return self.send(_layout("Edit Profile",f'<section><h2>Profile recovery</h2><p>The profile and backup cannot be parsed safely.</p><pre>{escape(problem or "Unknown error")}</pre><p>Edit this file and reload:</p><code>{escape(str(root/"profile.md"))}</code></section>'))
            if problem: flashes.append("Repair mode: showing the last valid backup. A valid save will repair profile.md.")
            links=p.data["links"]
            fields=_basic_profile_fields(p)
            link_fields=_online_profile_fields(links)
            selected_template=TemplateRegistry(root/"templates").get(load_config(root/"config.yml").template); supports_theme=bool(selected_template.capabilities.get("theme_switching"))
            theme_options=''.join(f'<option value="{v}" {"selected" if p.theme.default==v else ""}>{v.title()}</option>' for v in ("system","light","dark"))
            fields+=f'''<div><h3>Draft appearance</h3><label><input style="width:auto" type="checkbox" name="theme_enabled" {'checked' if p.theme.enabled else ''} {'disabled' if not supports_theme else ''}> Allow visitor theme switching</label><label>Default appearance<select name="theme_default" {'disabled' if not supports_theme else ''}>{theme_options}</select></label><small>{'Updates the draft preview; saved only with Save Changes.' if supports_theme else 'The selected template does not support theme switching.'}</small></div>'''
            icon=p.data.get("icon",""); icon_url="/asset/"+icon.removeprefix("assets/") if icon else ""
            icon_display=f'<img src="{escape(icon_url)}" alt="Current website icon" style="width:4rem;height:4rem;object-fit:contain">' if icon else '<p class="muted">Using default Student Profile Builder icon</p>'
            fields+=f'''<div><h3>Website icon</h3>{icon_display}<label class="button secondary">Choose Icon<input style="position:absolute;opacity:0;width:1px" type="file" name="icon_file" accept="image/png,image/x-icon,.ico" onchange="this.form.enctype='multipart/form-data'"></label><label><input style="width:auto" type="checkbox" name="remove_icon"> Remove custom icon</label><small>PNG or ICO, maximum 2 MB.</small></div>'''
            photo=p.data.get("photo",""); photo_url="/asset/"+photo.removeprefix("assets/") if photo else ""; cv=p.data.get("cv","")
            photo_display=f'<img src="{escape(photo_url)}" alt="Current profile photo" style="width:8rem;height:8rem;object-fit:cover;border-radius:.5rem">' if photo else '<p class="muted">Photo is hidden</p>'
            cv_status='PDF uploaded' if cv else 'No CV added'
            cv_link=f'<a class="button ghost" target="_blank" href="/asset/{escape(cv.removeprefix("assets/"))}">Open CV</a>' if cv else ''
            media=f'''<section><h3>Profile Media</h3><div class="grid"><div><h4>Profile photo</h4>{photo_display}<label class="button secondary">Choose Photo<input class="file-input" style="position:absolute;opacity:0;width:1px" type="file" name="photo_file" accept="image/jpeg,image/png,image/webp" onchange="this.form.enctype='multipart/form-data';document.getElementById('photo-keep').checked=true;let i=document.getElementById('photo-preview');i.src=URL.createObjectURL(this.files[0]);i.hidden=false"></label><img id="photo-preview" alt="Selected photo preview" hidden style="max-width:8rem"><fieldset><legend>Photo display</legend><label><input id="photo-keep" style="width:auto" type="radio" name="photo_action" value="keep" checked> Keep current photo</label><label><input style="width:auto" type="radio" name="photo_action" value="placeholder"> Remove upload and use default placeholder</label><label><input style="width:auto" type="radio" name="photo_action" value="remove"> Hide photo entirely</label></fieldset></div><div><h4>CV / Resume</h4><p>{cv_status}</p>{cv_link}<label class="button secondary">Choose PDF<input class="file-input" style="position:absolute;opacity:0;width:1px" type="file" name="cv_file" accept="application/pdf" onchange="this.form.enctype='multipart/form-data'"></label><label><input style="width:auto" type="checkbox" name="remove_cv"> Remove current CV</label></div></div><small>JPG/PNG/WebP up to 8 MB; PDF up to 15 MB.</small></section>'''
            cards=''.join(f'''<section id="section-{escape(s.id)}"><details><summary><strong>≡ {escape(s.title)}</strong> <span class="badge">{'Visible' if s.visible else 'Hidden'}</span> <small>{escape(s.type.title())}</small></summary><form data-dirty method="post" action="/section/action"><input type="hidden" name="csrf" value="{token}"><input type="hidden" name="id" value="{escape(s.id)}"><label>Title<input name="title" value="{escape(s.title)}"></label><label>Type<select name="type">{_section_type_options(s)}</select></label><label>Markdown<textarea name="content">{escape(s.markdown)}</textarea></label><details><summary>Markdown help</summary><pre>## Heading\n**bold**  *italic*\n- list\n[link](https://example.com)</pre></details><button class="primary" name="action" value="edit">Save</button><button class="secondary" name="action" value="duplicate">Duplicate</button><button class="ghost" name="action" value="up">Move Up</button><button class="ghost" name="action" value="down">Move Down</button><button class="ghost" name="action" value="toggle">{'Hide' if s.visible else 'Show'}</button><button class="danger" name="action" value="delete" onclick="return confirm('Delete {escape(s.title)}?')">Delete</button></form></details></section>''' for s in p.sections)
            cards=cards.replace('<form data-dirty method="post" action="/section/action">','<form data-dirty data-live-kind="section" method="post" action="/section/action">')
            types=''.join(f'<option>{x}</option>' for x in STARTERS); recommendations=sum(not bool(p.data.get(k)) for k in ("photo","cv")); raw=state["live_text"] if state["live_active"] else (root/"profile.md").read_text(encoding="utf-8"); body=f'''<p><span class="badge">Profile valid</span> <span class="muted">{recommendations} recommendations</span></p><div role="tablist"><button type="button" data-editor-tab="structured" class="primary">Structured Editor</button><button type="button" data-editor-tab="raw">Raw Markdown</button></div><div data-editor-panel="structured"><form data-dirty data-live-kind="profile" method="post" action="/profile/save"><input type="hidden" name="csrf" value="{token}"><section id="profile-details"><h2>Basic Information</h2><div class="grid">{fields}</div></section>{media}<section><h3>Online Profiles</h3><div class="grid">{link_fields}</div></section><section><h3>Research Interests</h3><label>One per line<textarea name="interests">{escape(chr(10).join(map(str,p.data['research_interests'])))}</textarea></label><button class="primary">Save Profile</button></section></form><h2>Website Sections</h2>{cards}<section><h3>+ Add Section</h3><form method="post" action="/section/add"><input type="hidden" name="csrf" value="{token}"><label>Title<input name="title" required></label><label>Type<select name="type">{types}</select></label><label><input style="width:auto" type="checkbox" name="visible" checked> Visible</label><label>Markdown (leave blank for starter text)<textarea name="content"></textarea></label><button class="primary">Add Section</button></form></section></div><div data-editor-panel="raw" hidden><section><h2>Complete profile.md</h2><p class="muted">Replace the entire document here to update the complete portfolio in one operation. Keep valid YAML front matter followed by Markdown headings and content. Changes render in an isolated preview; profile.md is replaced atomically only after you select Save Markdown.</p><label for="raw-markdown">Raw Markdown</label><textarea id="raw-markdown" data-raw-draft spellcheck="false" style="min-height:70vh;tab-size:2">{escape(raw)}</textarea><p data-draft-error class="notice" hidden></p><button type="button" class="primary" data-save-draft>Save Markdown</button><button type="button" data-discard-draft>Discard</button></section></div><section><h2>Restore Default</h2><p>Replace the local profile with the tracked Aarya Mehta starter. A bounded backup is created first.</p><form method="post" action="/profile/restore-default" onsubmit="return confirm('Restore Aarya Mehta default profile? Your current local data will be backed up and replaced.')"><input type="hidden" name="csrf" value="{token}"><button class="danger">Restore Default Profile</button></form></section>'''; self.send(_layout("Edit Profile",body))

        def raw_preview(self,f):
            initialize_draft()
            text=f.get("markdown",""); state["live_text"]=text; state["live_active"]=text!=(root/"profile.md").read_text(encoding="utf-8")
            try:
                candidate=validate_profile_text(root,text,directory=root/".runtime/live-candidate")
                next_revision=state["live_revision"]+1; live_output=root/".runtime"/f"live-preview-{next_revision}"
                state["live_building"]=True
                try:
                    with output_lock: build_site(root,profile_path=candidate,output_directory=live_output)
                finally: state["live_building"]=False
                state["live_profile"]=parse_profile(candidate,root); state["live_valid"]=True; state["live_error"]=""; state["live_revision"]=next_revision; state["live_output"]=live_output
                payload={"valid":True,"unsaved":state["live_active"],"revision":state["live_revision"]}
            except BuilderError as error:
                state["live_valid"]=False; state["live_error"]=str(error); payload={"valid":False,"unsaved":state["live_active"],"error":str(error),"revision":state["live_revision"]}
            self.send(json.dumps(payload).encode(),kind="application/json")

        def commit_draft_profile(self,profile):
            """Serialize and render one draft mutation without touching saved state."""
            initialize_draft(); candidate=root/".runtime/live-candidate/profile.md"
            serialize_profile(profile,candidate,backup=False,project_root=root)
            next_revision=state["live_revision"]+1; live_output=root/".runtime"/f"live-preview-{next_revision}"
            state["live_building"]=True
            try:
                with output_lock: build_site(root,profile_path=candidate,output_directory=live_output)
            finally: state["live_building"]=False
            text=candidate.read_text(encoding="utf-8")
            state.update({"live_text":text,"live_active":text!=saved_text(),"live_valid":True,"live_error":"",
                          "live_profile":parse_profile(candidate,root),"live_revision":next_revision,"live_output":live_output})

        def structured_preview(self,f):
            initialize_draft()
            base=state["live_profile"]
            draft_kind=f.get("draft_kind")
            if draft_kind=="profile":
                d=dict(base.data)
                for key in ("name","designation","department","institute","email"): d[key]=f.get(key,str(d.get(key,""))).strip()
                d["links"]={key:validate_web_url(key,f.get("link_"+key,"")) for key in ("github","linkedin","scholar","website")}
                d["research_interests"]=[x.strip() for x in f.get("interests","").splitlines() if x.strip()]
                photo_action=f.get("photo_action","keep")
                if photo_action not in {"keep","placeholder","remove"}: raise BuilderError("Unknown profile photo action.")
                if photo_action=="placeholder": d["photo"]="assets/profile-placeholder.svg"
                elif photo_action=="remove": d["photo"]=""
                if "remove_cv" in f: d["cv"]=""
                if "remove_icon" in f: d["icon"]=""
                for field,kind in (("photo_file","photo"),("cv_file","cv"),("icon_file","icon")):
                    upload=f.get(field)
                    if isinstance(upload,UploadedFile) and upload.data: d[kind]=self.import_upload(upload,kind)
                theme=base.theme
                if "theme_default" in f:
                    default=f.get("theme_default","system")
                    if default not in {"light","dark","system"}: raise BuilderError("Appearance must be light, dark, or system.")
                    theme=Theme("theme_enabled" in f,default)
                candidate_profile=Profile(d,base.markdown,base.html,base.sections,theme)
            elif draft_kind=="appearance":
                default=f.get("default","system")
                if default not in {"light","dark","system"}: raise BuilderError("Appearance must be light, dark, or system.")
                candidate_profile=Profile(base.data,base.markdown,base.html,base.sections,Theme("enabled" in f,default))
            else:
                items=list(base.sections); index=next((i for i,s in enumerate(items) if s.id==f.get("id")),None)
                if index is None: raise BuilderError("Section not found in live draft.")
                title=f.get("title","").strip()
                if not title: raise BuilderError("Section title is required.")
                content=f.get("content",""); items[index]=replace(items[index],title=title,type=f.get("type",items[index].type),markdown=content,html=_render(content))
                candidate_profile=Profile(base.data,base.markdown,base.html,tuple(items),base.theme)
            candidate=root/".runtime/live-candidate/profile.md"; candidate.parent.mkdir(parents=True,exist_ok=True); serialize_profile(candidate_profile,candidate,backup=False,project_root=root)
            next_revision=state["live_revision"]+1; live_output=root/".runtime"/f"live-preview-{next_revision}"
            state["live_building"]=True
            try:
                with output_lock: build_site(root,profile_path=candidate,output_directory=live_output)
            finally: state["live_building"]=False
            text=candidate.read_text(encoding="utf-8"); dirty=text!=saved_text()
            state.update({"live_text":text,"live_active":dirty,"live_valid":True,"live_error":"","live_profile":parse_profile(candidate,root),"live_revision":next_revision,"live_output":live_output})
            self.send(json.dumps({"valid":True,"unsaved":dirty,"revision":state["live_revision"],"markdown":state["live_text"]}).encode(),kind="application/json")

        def save_draft(self):
            if not state["live_active"]: return self.redirect("/profile","No unsaved changes")
            if not state["live_valid"]: raise BuilderError("Markdown has errors. Fix the draft before saving.")
            if state["draft_base_revision"] and profile_revision()!=state["draft_base_revision"]:
                raise BuilderError("The saved profile changed while you were editing. Reload the latest profile before saving; your draft was kept.")
            old_profile=parse_profile(root/"profile.md",root); draft=state["live_profile"]
            promoted=dict(draft.data); newly_promoted=[]
            for kind in ("photo","cv","icon"):
                value=promoted.get(kind,"")
                if value.startswith(f"assets/.drafts/{token}/"):
                    promoted[kind]=import_asset_bytes(root,kind,(root/value).read_bytes()); newly_promoted.append(root/promoted[kind])
            if promoted!=draft.data:
                promoted_profile=Profile(promoted,draft.markdown,draft.html,draft.sections,draft.theme)
                candidate_path=root/".runtime/save-candidate/profile.md"
                serialize_profile(promoted_profile,candidate_path,backup=False,project_root=root)
                state["live_text"]=candidate_path.read_text(encoding="utf-8"); state["live_profile"]=promoted_profile
            committed=False
            try:
                candidate=validate_profile_text(root,state["live_text"],directory=root/".runtime/save-candidate")
                with output_lock: build_site(root,profile_path=candidate,output_directory=root/".runtime/save-site")
                save_profile_text(root,state["live_text"]); committed=True; rebuild_saved(); clear_draft()
            except Exception:
                if not committed:
                    for path in newly_promoted:
                        if path.is_file(): path.unlink()
                raise
            for kind in ("photo","cv","icon"):
                old=old_profile.data.get(kind,""); new=promoted.get(kind,"")
                if old and old!=new and old.startswith("assets/managed/"):
                    path=(root/old).resolve(); managed=(root/"assets/managed").resolve()
                    if managed in path.parents and path.is_file(): path.unlink()
            self.redirect("/profile","Profile saved ✓ · Preview synced ✓")

        def discard_draft(self,rebuild=True,message="Unsaved changes discarded"):
            clear_draft()
            self.redirect("/profile",message)

        def restore_default(self):
            restore_default_profile(root); state.update({"live_active":False,"live_valid":False,"live_error":"","live_text":"","live_profile":None}); rebuild_saved(); activity.append("Default profile restored"); self.redirect("/profile","Default profile restored ✓")

        def draft_api(self):
            self.send(json.dumps({"active":state["live_active"],"valid":state["live_valid"],"error":state["live_error"],"markdown":state["live_text"] if state["live_active"] else (root/"profile.md").read_text(encoding="utf-8")}).encode(),kind="application/json")
        def save_profile(self,f):
            p=initialize_draft()
            if p is None: raise BuilderError("Profile cannot be repaired automatically because no valid backup is available.")
            submitted_links={x:validate_web_url(x,f.get("link_"+x,"")) for x in ("github","linkedin","scholar","website")}
            d=dict(p.data)
            for x in ("name","designation","department","institute","email"): d[x]=f.get(x,"").strip()
            if any(not d[x] for x in ("name","designation","institute")): raise BuilderError("Name, designation, and institute are required.")
            old_photo,old_cv,old_icon=d.get("photo",""),d.get("cv",""),d.get("icon","")
            photo_action=f.get("photo_action","keep")
            if photo_action not in {"keep","placeholder","remove"}: raise BuilderError("Unknown profile photo action.")
            if photo_action=="placeholder": d["photo"]="assets/profile-placeholder.svg"
            elif photo_action=="remove": d["photo"]=""
            if "remove_cv" in f: d["cv"]=""
            if "remove_icon" in f: d["icon"]=""
            if isinstance(f.get("photo_file"),UploadedFile) and f["photo_file"].data: d["photo"]=self.import_upload(f["photo_file"],"photo")
            if isinstance(f.get("cv_file"),UploadedFile) and f["cv_file"].data: d["cv"]=self.import_upload(f["cv_file"],"cv")
            if isinstance(f.get("icon_file"),UploadedFile) and f["icon_file"].data: d["icon"]=self.import_upload(f["icon_file"],"icon")
            d["links"]=submitted_links; d["research_interests"]=[x.strip() for x in f.get("interests","").splitlines() if x.strip()]; theme=Theme("theme_enabled" in f,f.get("theme_default","system")) if "theme_enabled" in f or "theme_default" in f else p.theme; self.commit_draft_profile(Profile(d,p.markdown,p.html,p.sections,theme))
            activity.append("Profile saved"); self.save_draft()
        def import_upload(self,upload,kind):
            staging_root=root/".runtime/drafts"/token/"asset-import"
            temporary=import_asset_bytes(staging_root,kind,upload.data)
            source=staging_root/temporary; target=root/"assets/.drafts"/token/source.name
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
            state["draft_assets"][kind]=target
            return target.relative_to(root).as_posix()
        def add_section(self,f):
            p=initialize_draft(); title=f.get("title","").strip()
            if not title: raise BuilderError("Section title is required.")
            if len(title)>120: raise BuilderError("Section title must be at most 120 characters.")
            kind=f.get("type","custom"); content=f.get("content","") or STARTERS.get(kind,""); sid=_slug(title,{s.id for s in p.sections}); item=Section(sid,title,kind,"visible" in f,len(p.sections)*10+10,content,_render(content)); self.commit_draft_profile(Profile(p.data,p.markdown,p.html,p.sections+(item,),p.theme)); activity.append("Draft section added"); self.redirect("/profile#section-"+sid,f"{title} added to draft")
        def section_action(self,f):
            p=initialize_draft(); items=list(p.sections); i=next((n for n,s in enumerate(items) if s.id==f.get("id")),None)
            if i is None: raise BuilderError("Section not found.")
            action=f.get("action"); moved_id=items[i].id
            if action=="delete": state["draft_deleted"][:]=[items.pop(i)]
            elif action=="toggle": items[i]=replace(items[i],visible=not items[i].visible)
            elif action=="duplicate":
                s=items[i]; items.insert(i+1,replace(s,id=_slug(s.id,{x.id for x in items}),title=s.title+" Copy"))
            elif action=="edit":
                title=f.get("title","").strip()
                if not title: raise BuilderError("Section title is required.")
                if len(title)>120: raise BuilderError("Section title must be at most 120 characters.")
                content=f.get("content",""); items[i]=replace(items[i],title=title,type=f.get("type","custom"),markdown=content,html=_render(content))
            elif action=="up" and i>0: items[i-1],items[i]=items[i],items[i-1]
            elif action=="down" and i<len(items)-1: items[i+1],items[i]=items[i],items[i+1]
            self.commit_draft_profile(Profile(p.data,p.markdown,p.html,tuple(items),p.theme)); activity.append(f"Draft section {action}"); self.redirect("/profile"+("" if action=="delete" else "#section-"+moved_id),"Draft section updated")
        def undo(self):
            if not state["draft_deleted"]: raise BuilderError("Nothing to restore.")
            p=initialize_draft(); restored=state["draft_deleted"].pop(); self.commit_draft_profile(Profile(p.data,p.markdown,p.html,p.sections+(restored,),p.theme)); self.redirect("/profile#section-"+restored.id,"Section restored to draft")
        def appearance(self,f):
            p,_=safe_profile()
            if p is None: raise BuilderError("Repair profile.md before changing appearance.")
            t=TemplateRegistry(root/"templates").get(load_config(root/"config.yml").template); enabled="enabled" in f
            if enabled and not t.capabilities.get("theme_switching"): raise BuilderError("This template does not support theme switching.")
            default=f.get("default","system")
            if default not in {"light","dark","system"}: raise BuilderError("Appearance must be light, dark, or system.")
            serialize_profile(Profile(p.data,p.markdown,p.html,p.sections,Theme(enabled,default)),root/"profile.md"); activity.append("Appearance saved"); self.sync_preview(); self.redirect("/","Appearance saved")
        def templates_page(self):
            query=parse_qs(urlparse(self.path).query)
            if "draft" not in query:
                rebuild_saved(); state["preview_template"]=None; state["draft_active"]=False
            state["preview_open"]=True; self.template_workspace()
        def template_selector(self):
            c=load_config(root/"config.yml"); items=TemplateRegistry(root/"templates").discover(); previewing=state["preview_template"] or c.template
            choices=[]
            for template in items.values():
                badge="Previewing" if template.id == previewing else ("Saved" if template.id == c.template else "Available")
                preview_class="primary" if template.id == previewing else "ghost"
                theme_support="Yes" if template.capabilities.get("theme_switching") else "No"
                use_form=""
                if template.id != c.template:
                    use_form=(f'<form style="display:inline" method="post" action="/template/select">'
                              f'<input type="hidden" name="csrf" value="{token}">'
                              f'<button class="secondary" name="id" value="{escape(template.id)}">Use</button></form>')
                choices.append(
                    f'<div class="card" style="padding:1rem;margin:0"><strong>{escape(template.name)}</strong> '
                    f'<span class="badge">{badge}</span><dl style="display:grid;grid-template-columns:auto 1fr;gap:.2rem .6rem;margin:.75rem 0">'
                    f'<dt class="muted">Designed by</dt><dd style="margin:0">{escape(template.author or "Student Profile Builder")}</dd>'
                    f'<dt class="muted">Type</dt><dd style="margin:0">{escape(template.layout_mode.replace("-"," ").title())}</dd>'
                    f'<dt class="muted">Theme switching</dt><dd style="margin:0">{theme_support}</dd></dl>'
                    f'<form style="display:inline" method="post" action="/template/preview"><input type="hidden" name="csrf" value="{token}">'
                    f'<button class="{preview_class}" name="id" value="{escape(template.id)}">Preview</button></form>{use_form}</div>'
                )
            choices="".join(choices)
            return '<section><h2>Choose a template</h2><p class="muted">Preview any available template below. “Use” saves it and rebuilds the website.</p><div class="grid">'+choices+'</div></section>'
        def select_template(self,f):
            c=load_config(root/"config.yml"); chosen=TemplateRegistry(root/"templates").get(f.get("id","")); saved_profile=parse_profile(root/"profile.md",root); theme_changed=saved_profile.theme.enabled and not chosen.capabilities.get("theme_switching")
            save_config(root/"config.yml",replace(c,template=f["id"]))
            if theme_changed: serialize_profile(Profile(saved_profile.data,saved_profile.markdown,saved_profile.html,saved_profile.sections,Theme(False,saved_profile.theme.default)),root/"profile.md")
            try: rebuild_saved()
            except Exception:
                save_config(root/"config.yml",c); serialize_profile(saved_profile,root/"profile.md")
                raise
            state["preview_template"]=None; state["draft_active"]=False; state["preview_open"]=True; activity.append("Template selected and website rebuilt"); self.redirect("/templates","Template selected; visitor theme switching was turned off for this template" if theme_changed else "Template selected and website rebuilt")
        def preview_template(self,f):
            template=f.get("id",""); chosen=TemplateRegistry(root/"templates").get(template)
            profile_path=(root/".runtime/live-candidate/profile.md") if state["live_active"] and state["live_valid"] else None
            source=parse_profile(profile_path or root/"profile.md",root)
            if source.theme.enabled and not chosen.capabilities.get("theme_switching"):
                profile_path=root/".runtime/template-preview/profile.md"; serialize_profile(Profile(source.data,source.markdown,source.html,source.sections,Theme(False,source.theme.default)),profile_path,backup=False,project_root=root)
            with output_lock: build_site(root,template_id=template,profile_path=profile_path,output_directory=root/"preview-draft")
            state["preview_template"]=template; state["draft_active"]=True; activity.append("Template draft previewed"); self.redirect("/templates?draft=1","Draft preview updated; saved website unchanged")
        def return_template(self):
            state["preview_template"]=None; state["draft_active"]=False; activity.append("Returned to current template"); self.redirect("/templates","Current template restored")
        def build(self): rebuild_saved(); state["preview_template"]=None; state["draft_active"]=False; activity.append("Website built"); self.redirect("/","Website built")
        def preview_page(self):
            rebuild_saved(); state["preview_template"]=None; state["draft_active"]=False; state["preview_open"]=True; activity.append("Preview opened"); self.redirect("/?preview=1","Saved website rebuilt; live preview focused")
        def preview_window(self):
            """Serve a stable browser tab that follows whichever preview is active."""
            body=b'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Live Profile Preview</title><style>*{box-sizing:border-box}html,body,iframe{width:100%;height:100%;margin:0;border:0}body{background:#111827}#state{position:fixed;right:12px;top:10px;z-index:2;padding:5px 10px;border-radius:999px;background:#172033;color:#fff;font:12px system-ui;opacity:.82}iframe{display:block;background:#fff}</style></head><body><span id="state">Connecting...</span><iframe title="Live profile preview"></iframe><script>const frame=document.querySelector('iframe'),label=document.getElementById('state');let fingerprint='',url='';async function sync(){try{const s=await fetch('/api/build-status',{cache:'no-store'}).then(r=>r.json()),next=s.preview_url||'/site/',mark=(s.fingerprint||'none')+'|'+next;if(mark!==fingerprint){fingerprint=mark;url=next;frame.src=next+'?window='+encodeURIComponent(mark)}label.textContent=s.live_error?'Invalid draft - last valid preview':(s.live_active?'Live unsaved preview':(s.previewing?'Template preview':'Saved preview'));label.style.background=s.live_error?'#922c2c':(s.live_active?'#8a5b00':'#17643a')}catch(e){label.textContent='Preview unavailable';label.style.background='#922c2c'}}sync();setInterval(sync,700)</script></body></html>'''
            self.send(body)
        def template_workspace(self):
            body=self.template_selector()+'''<section><h2>Draft Template Preview</h2><p class="muted">Preview renders temporarily in the persistent pane. Use Template saves it; Return to Current restores the selected site.</p></section>'''; self.send(_layout("Templates",body,"Template preview uses the live workspace pane"))
        def build_status_api(self):
            c=load_config(root/"config.yml"); current,last=build_status(root,c.template,root/c.output_directory); preview_id=state["preview_template"]; preview_name=TemplateRegistry(root/"templates").get(preview_id).name if preview_id else None
            # An invalid candidate must retain the last successfully rendered
            # draft rather than falling back to or blanking the main preview.
            live_shown=state["live_active"] and state["live_output"].is_dir() and not state["draft_active"]
            preview_url="/draft-site/" if state["draft_active"] else ("/live-site/" if live_shown else "/site/")
            fingerprint=(f"template-{preview_id}-live-{state['live_revision']}" if state["draft_active"] else (f"live-{state['live_revision']}" if live_shown else (last or "none")))
            mode="building" if state["live_building"] else ("invalid-draft" if state["live_active"] and not state["live_valid"] else ("draft" if state["live_active"] else "saved"))
            selected=TemplateRegistry(root/"templates").get(c.template)
            payload=json.dumps({"mode":mode,"dirty":state["live_active"],"current":current,"built_at":last,"updated_at":last,"fingerprint":fingerprint,"revision":state["live_revision"],"debounce_ms":900 if selected.engine=="external-build" else 450,"previewing":preview_name,"preview_template":preview_id,"preview_url":preview_url,"live_active":state["live_active"],"live_valid":state["live_valid"],"live_error":state["live_error"],"csrf":token}).encode(); self.send(payload,kind="application/json")
        def asset_file(self,relative):
            assets=(root/"assets").resolve(); file=(assets/relative).resolve()
            if assets not in file.parents or not file.is_file(): return self.send(b"Not found",404,"text/plain")
            self.send(file.read_bytes(),kind=mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        def site_file(self,relative):
            self.output_file(root/"dist",relative)
        def output_file(self,directory,relative):
            with output_lock:
                out=directory.resolve(); file=(out/(relative or "index.html")).resolve()
                if file!=out and out not in file.parents: return self.send(b"Not found",404,"text/plain")
                if file.is_dir(): file=file/"index.html"
                if not file.is_file(): return self.send(b"Not found",404,"text/plain")
                body=file.read_bytes(); kind=mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            self.send(body,kind=kind)
        def publish_page(self):
            tools={name:bool(shutil.which(name)) for name in ("ssh","scp","git","gh")}; recent=jobs.recent(5); recent_html=''.join(f'<li>{escape(j["provider"].title())}: <strong>{escape(j["state"])}</strong> {escape(j.get("message", ""))}</li>' for j in recent) or '<li>No deployment jobs yet.</li>'
            github_ready=tools["git"] and tools["gh"]
            body=f'''<section><h2>Deploy to IIT Delhi</h2><p><strong>IIT Delhi authentication is handled directly by OpenSSH.</strong></p><p>A separate terminal will open. You may be asked for your IIT Delhi password multiple times because deployment uses separate SSH/SCP connections. Student Profile Builder never reads or stores your password.</p><p>OpenSSH: <strong>{'Ready ✓' if tools['ssh'] and tools['scp'] else 'Missing'}</strong></p><div class="grid"><label class="card"><input style="width:auto" type="radio" form="iitd" name="target" value="public" checked><strong> Public website</strong><br><small>Faculty and PhD students · public_html<br>https://web.iitd.ac.in/~userid/</small></label><label class="card"><input style="width:auto" type="radio" form="iitd" name="target" value="private"><strong> IITD-only website</strong><br><small>IITD users with CSC home space · private_html<br>http://privateweb.iitd.ac.in/~userid/</small></label></div><form id="iitd" method="post" action="/deploy/iitd"><input type="hidden" name="csrf" value="{token}"><label>IITD User ID<input name="userid" required></label><button class="secondary" name="mode" value="dry">Dry Run in Terminal</button><button class="primary" name="mode" value="deploy" {'disabled' if not tools['ssh'] or not tools['scp'] else ''}>Publish in Terminal</button></form></section><section><h2>GitHub Pages</h2><h3>Requirements</h3><p>Git <strong>{'✓' if tools['git'] else 'Missing'}</strong><br>GitHub CLI (gh) <strong>{'✓' if tools['gh'] else 'Missing'}</strong><br>GitHub login <strong>Not checked — handled in terminal</strong></p>{'' if github_ready else '<p class="notice">GitHub CLI is required for automatic publishing. Install it, then restart or recheck Student Profile Builder. Your profile and local website are unaffected.</p><p><a class="button" target="_blank" href="https://cli.github.com/">Installation Guide</a> <a class="button" href="/publish">Recheck</a></p>'}<form method="post" action="/deploy/github"><input type="hidden" name="csrf" value="{token}"><label>Expected GitHub username<input name="username" required placeholder="alice"></label><label>Site type<select name="site"><option value="personal">Personal — username.github.io</option><option value="project">Project — username.github.io/repository</option></select></label><label>Repository name (project sites)<input name="repo" placeholder="academic-profile"></label><p class="muted">Personal is your main GitHub website. Project is useful if username.github.io already hosts something else.</p><button name="mode" value="dry" {'disabled' if not github_ready else ''}>Dry Run in Terminal</button><button class="primary" name="mode" value="deploy" {'disabled' if not github_ready else ''}>Publish in Terminal</button></form><details><summary>How GitHub publishing works</summary><p>The website is built locally. Only generated static files are published to <code>gh-pages</code> from <code>/(root)</code>. Your profile source, Python environment, and application files are not published. Main/master is never overwritten.</p></details></section><section><h2>Recent deployment activity</h2><ul>{recent_html}</ul></section><p>This page never asks for a password, PAT, OAuth token, or SSH key.</p>'''; self.send(_layout("Publish",body))
        def deploy_iitd(self,f):
            if state["live_active"] and f.get("draft_choice")!="saved": raise BuilderError("You have unsaved profile changes. Save or discard them before publishing, or explicitly publish the saved version.")
            if not shutil.which("ssh") or not shutil.which("scp"): raise BuilderError("IIT Delhi deployment requires the OpenSSH Client (ssh and scp). Install or enable OpenSSH, restart Student Profile Builder, and try again.")
            userid=validate_userid(f.get("userid","")); target=IITDTarget.parse(f.get("target","")).value; dry=f.get("mode")=="dry"; rebuild_saved(); job=jobs.create("iitd",target=target,userid=userid,dry_run=dry); self.launch_deployment(job,"IIT Delhi Deployment")
        def deploy_github(self,f):
            if state["live_active"] and f.get("draft_choice")!="saved": raise BuilderError("You have unsaved profile changes. Save or discard them before publishing, or explicitly publish the saved version.")
            if not shutil.which("git") or not shutil.which("gh"): raise BuilderError("GitHub CLI is required for automatic GitHub Pages publishing. Install Git and GitHub CLI, then recheck. Your profile and local website are unaffected.")
            site=GitHubSiteType.parse(f.get("site","")); repo=f.get("repo","") or None; username=f.get("username","").strip(); deployment_identity(username,site,repo); dry=f.get("mode")=="dry"; rebuild_saved(); job=jobs.create("github",target=f"{site.value}:{repo or username+'.github.io'}",site=site.value,repository=repo,username=username,dry_run=dry); self.launch_deployment(job,"GitHub Pages Deployment")
        def launch_deployment(self,job,title):
            command=worker_command(root,job["id"]); result=launcher.launch(command,title,root/".runtime")
            if result.started: jobs.update(job["id"],message=f"Deployment started in {result.terminal}.")
            else: jobs.update(job["id"],state="failed",message=result.message or "Unable to open a separate terminal automatically.")
            manual=escape(result.manual_command); message="A terminal window has been opened for secure authentication. You may continue using Student Profile Builder while publishing runs." if result.started else "Unable to start deployment terminal. Copy and run the safe command manually."
            status="waiting" if result.started else "failed"
            manual_control=""
            if not result.started:
                copy_script="navigator.clipboard.writeText(this.previousElementSibling.querySelector('input').value)"
                manual_control=(f'<label>Manual command<input readonly value="{manual}"></label>'
                                f'<button type="button" onclick="{copy_script}">Copy Manual Command</button>')
            job_id=escape(job["id"])
            body=(f'<section data-deployment-job="{job_id}"><h2>Deployment started</h2>'
                  f'<p>{escape(message)}</p><p>Status: <strong data-job-state>{status}</strong></p>'
                  f'<p data-job-message>{escape(result.message)}</p><div data-job-result></div>{manual_control}'
                  '<p><a class="button" href="/publish">Back to Publish</a></p></section>')
            self.send(_layout("Deployment",body))
        def deployment_status(self,job_id):
            payload=json.dumps(jobs.read(job_id)).encode(); self.send(payload,kind="application/json")
        def export_profile(self):
            dest=root/"student-profile-backup.zip"
            with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
                for name in ("profile.md","config.yml"): z.write(root/name,name)
                for file in (root/"assets").rglob("*"):
                    if file.is_file() and not file.is_symlink(): z.write(file,file.relative_to(root).as_posix())
            data=dest.read_bytes(); self.send_response(200); self.send_header("Content-Type","application/zip"); self.send_header("Content-Disposition",'attachment; filename="student-profile-backup.zip"'); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    server=ThreadingHTTPServer((GUI_HOST,port),Handler)
    if open_browser: threading.Timer(.3,lambda:webbrowser.open(f"http://{GUI_HOST}:{server.server_port}/")).start()
    return server


def run_gui(root: Path, port: int = GUI_PORT, open_browser: bool = True) -> None:
    try: server=create_server(root,port,open_browser)
    except OSError as e:
        url=f"http://{GUI_HOST}:{port}"
        try: identity=json.loads(urlopen(url+"/api/health",timeout=.5).read())
        except Exception: identity={}
        if identity.get("application")=="student-profile-builder":
            raise BuilderError(f"Student Profile Builder is already running:\n{url}/") from e
        raise BuilderError(f"Port {port} is already in use.\n\nAnother application is using this port. Start on another port with:\npython manage.py gui --port {port-1}") from e
    print(f"Student Profile Builder GUI\n\nRunning at:\nhttp://{GUI_HOST}:{server.server_port}/\n\nPress Ctrl+C to stop.")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nGUI stopped.")
    finally: server.server_close()
