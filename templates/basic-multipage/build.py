from pathlib import Path
from html import escape
import json

root=Path(__file__).parent
data=json.loads((root/"profile-data.json").read_text(encoding="utf-8"))
out=root/"dist"
out.mkdir()
(out/"assets").mkdir()
profile=data["profile"]
sections=data["sections"]
theme=data.get("theme",{"enabled":False,"default":"system"})
groups={"profile":{"about","education","experience"},"work":{"research","projects"},"writing":{"publications"}}
pages={key:[section for section in sections if section["type"] in kinds] for key,kinds in groups.items()}
used={section["id"] for page in pages.values() for section in page}
for section in sections:
    if section["id"] not in used: pages["sections/"+section["id"]]=[section]
pages={key:value for key,value in pages.items() if value}

css="""
*{box-sizing:border-box}:root{font:17px/1.72 Inter,ui-sans-serif,system-ui,sans-serif;--paper:#f2f0e9;--sheet:#fcfbf7;--ink:#20231f;--muted:#70756e;--line:#d7d4c9;--moss:#315f4d;--moss-soft:#dfe9e2;--orange:#dc653f;--shadow:0 25px 65px rgba(48,45,35,.1)}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink)}a{color:var(--moss);text-underline-offset:.22em}.frame{width:min(100% - 2rem,80rem);margin:auto}.masthead{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:2rem;min-height:4.75rem;border-bottom:1px solid var(--line);background:rgba(242,240,233,.92);backdrop-filter:blur(14px)}.masthead>a{flex:none;color:var(--ink);font-weight:850;letter-spacing:-.03em;text-decoration:none}.masthead nav{display:flex;gap:1.2rem;overflow:auto;scrollbar-width:none}.masthead nav::-webkit-scrollbar{display:none}.masthead nav a{flex:none;color:var(--muted);font-size:.8rem;font-weight:700;text-decoration:none;white-space:nowrap}.masthead nav a:hover{color:var(--moss)}.cover{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(17rem,.55fr);gap:clamp(2rem,7vw,7rem);align-items:center;padding:clamp(2.75rem,6vw,5.5rem) 0}.issue{color:var(--orange);font:750 .72rem ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}.cover h1{max-width:11ch;margin:.8rem 0 1.25rem;font:500 clamp(3.5rem,9vw,8rem)/.9 Georgia,serif;letter-spacing:-.065em}.role{max-width:35rem;margin:0 0 1rem;color:var(--moss);font-size:clamp(1.15rem,2vw,1.5rem);font-weight:700}.affiliation{max-width:36rem;color:var(--muted)}.profile-card{padding:1rem;border:1px solid var(--line);background:var(--sheet);box-shadow:var(--shadow);transform:rotate(1.5deg);transition:transform .3s}.profile-card:hover{transform:rotate(0) translateY(-4px)}.profile-card img{display:block;width:100%;aspect-ratio:4/5;object-fit:cover;filter:saturate(.75) contrast(1.03)}.profile-card .caption{padding:1rem .35rem .35rem;color:var(--muted);font-size:.78rem}.actions{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:1.4rem}.actions a{padding:.55rem .78rem;border:1px solid var(--line);background:var(--sheet);color:var(--ink);font-size:.82rem;font-weight:700;text-decoration:none;transition:background .18s,color .18s,transform .18s}.actions a:hover{transform:translateY(-2px);background:var(--moss);color:#fff}.interests{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:0;margin:0 0 6rem;padding:0;border-block:1px solid var(--line);list-style:none}.interests li{padding:1rem;border-right:1px solid var(--line);color:var(--muted);font:600 .84rem ui-monospace,monospace}.interests li:last-child{border-right:0}.page{padding:clamp(3rem,7vw,7rem) 0}.page-head{display:grid;grid-template-columns:.32fr 1fr;gap:2rem;margin-bottom:3rem}.page-head span{color:var(--orange);font:750 .72rem ui-monospace,monospace;text-transform:uppercase}.page-head h1{max-width:15ch;margin:0;font:500 clamp(3rem,7vw,6.2rem)/.92 Georgia,serif;letter-spacing:-.055em}.articles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2rem}.articles section{min-width:0;padding:clamp(1.3rem,3vw,2.4rem);border:1px solid var(--line);background:var(--sheet);box-shadow:0 8px 26px rgba(48,45,35,.045);transition:transform .22s,border-color .22s,box-shadow .22s}.articles section:hover{transform:translateY(-4px);border-color:#9caf9f;box-shadow:var(--shadow)}.articles section:nth-child(3n){grid-column:1/-1}.articles h2{margin:0 0 1.5rem;font:500 clamp(1.8rem,4vw,3rem)/1.05 Georgia,serif;letter-spacing:-.035em}.articles section>:last-child{margin-bottom:0}.footer{display:flex;justify-content:space-between;gap:1rem;padding:2rem 0 3rem;border-top:1px solid var(--line);color:var(--muted);font-size:.8rem}table{display:block;width:100%;overflow-x:auto;border-collapse:collapse}th,td{padding:.7rem .8rem;border-bottom:1px solid var(--line);text-align:left}th{background:var(--moss-soft);font-size:.75rem;text-transform:uppercase}blockquote{margin-left:0;padding:1rem 1.2rem;border-left:3px solid var(--orange);background:#f6eee8}pre{overflow:auto;padding:1rem;background:#252822;color:#f7f4ed}:focus-visible{outline:3px solid #93b4a5;outline-offset:3px}@media(max-width:760px){.frame{width:min(100% - 1.5rem,80rem)}.masthead{gap:1rem}.cover{grid-template-columns:1fr;min-height:auto;padding:4rem 0}.cover h1{font-size:3.8rem}.profile-card{width:min(82%,20rem);transform:none}.interests{grid-template-columns:1fr}.interests li{border-right:0;border-bottom:1px solid var(--line)}.interests li:last-child{border-bottom:0}.page-head{grid-template-columns:1fr;gap:.75rem}.articles{grid-template-columns:1fr}.articles section:nth-child(3n){grid-column:auto}.footer{display:block}.footer span{display:block;margin-top:.35rem}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
"""
css += """html[data-theme=dark]{--paper:#141713;--sheet:#1d211c;--ink:#f1f3ed;--muted:#a8aea5;--line:#383d36;--moss:#88c7aa;--moss-soft:#29372f;--orange:#ff8a61;--shadow:0 25px 65px rgba(0,0,0,.3)}@media(prefers-color-scheme:dark){html[data-theme=system]{--paper:#141713;--sheet:#1d211c;--ink:#f1f3ed;--muted:#a8aea5;--line:#383d36;--moss:#88c7aa;--moss-soft:#29372f;--orange:#ff8a61;--shadow:0 25px 65px rgba(0,0,0,.3)}}.nav-wrap{position:relative;min-width:0;flex:1}.masthead nav a[aria-current=page]{color:var(--moss);box-shadow:inset 0 -2px var(--orange)}.nav-cue{position:absolute;right:0;top:0;padding-left:1.6rem;color:var(--orange);background:linear-gradient(90deg,transparent,var(--paper) 48%);pointer-events:none}.menu-toggle{display:none}.theme-toggle{flex:none;width:2.45rem;height:2.45rem;border:1px solid var(--line);border-radius:50%;background:var(--sheet);color:var(--ink);cursor:pointer;transition:transform .18s,border-color .18s}.theme-toggle:hover{transform:rotate(12deg);border-color:var(--moss)}.page-head h1{font-size:clamp(2.6rem,6vw,4.8rem)}.articles h2{font-size:clamp(1.45rem,3vw,2.15rem)}.articles .lead-section{grid-column:1/-1}.articles .lead-section>h2{display:none}table{border:1px solid var(--line);border-radius:0;border-collapse:separate;border-spacing:0;background:var(--sheet)}th{background:var(--moss);color:var(--sheet);letter-spacing:.08em}tr:last-child td{border-bottom:0}tbody tr{transition:background .16s}tbody tr:hover{background:var(--moss-soft)}@media(max-width:760px){.masthead{flex-wrap:wrap;padding:.7rem 0}.menu-toggle{display:block;margin-left:auto;border:1px solid var(--line);padding:.45rem .7rem;background:var(--sheet);color:var(--ink);font-weight:700}.nav-wrap{display:none;order:4;flex-basis:100%}.masthead.nav-open .nav-wrap{display:block}.masthead nav{display:grid;gap:0}.masthead nav a{padding:.6rem 0}.nav-cue{display:none}}"""
css += ".masthead{background:color-mix(in srgb,var(--paper) 92%,transparent)}.articles.stacked{grid-template-columns:1fr}.articles.stacked section,.articles.stacked section:nth-child(3n),.articles .lead-section{grid-column:auto}table{display:table!important;width:100%;table-layout:fixed;overflow:visible}th,td{overflow-wrap:anywhere;vertical-align:top}@media(max-width:760px){th,td{padding:.58rem .45rem;font-size:.82rem}}"
(out/"assets/style.css").write_text(css,encoding="utf-8")

script="""const h=document.querySelector('.masthead'),m=document.querySelector('[data-menu-toggle]'),n=document.querySelector('#page-nav');if(m&&n){m.addEventListener('click',()=>{const o=h.classList.toggle('nav-open');m.setAttribute('aria-expanded',String(o))});n.addEventListener('click',e=>{if(e.target.closest('a')){h.classList.remove('nav-open');m.setAttribute('aria-expanded','false')}});n.addEventListener('wheel',e=>{if(getComputedStyle(n).display==='flex'&&n.scrollWidth>n.clientWidth&&Math.abs(e.deltaY)>Math.abs(e.deltaX)){e.preventDefault();n.scrollLeft+=e.deltaY}},{passive:false})}const b=document.querySelector('[data-theme-toggle]');if(b){const r=document.documentElement;let v=localStorage.getItem('profile-theme')||r.dataset.theme||'system';const a=x=>{r.dataset.theme=x;const d=x==='dark'||(x==='system'&&matchMedia('(prefers-color-scheme:dark)').matches);b.textContent=d?'☀':'☾';b.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme');b.title=b.getAttribute('aria-label')};a(v);b.addEventListener('click',()=>{const d=r.dataset.theme==='dark'||(r.dataset.theme==='system'&&matchMedia('(prefers-color-scheme:dark)').matches),x=d?'light':'dark';localStorage.setItem('profile-theme',x);a(x)})}"""
(out/"assets/site.js").write_text(script,encoding="utf-8")

def href(current,target):
    depth=len(Path(current).parts)-1
    prefix="../"*depth
    return prefix+("index.html" if target=="index" else target+".html")

def actions(prefix=""):
    values=[]
    if profile.get("email"): values.append(("Email",f'mailto:{profile["email"]}'))
    values.extend((label.replace("_"," ").title(),url) for label,url in profile.get("links",{}).items() if url)
    if profile.get("cv"): values.append(("Resume",prefix+profile["cv"]))
    return "".join(f'<a href="{escape(url)}">{escape(label)}</a>' for label,url in values)

def render(current,title,body):
    links=[]
    for key,items in pages.items():
        current_attribute=' aria-current="page"' if current==key+".html" else ""
        links.append(f'<a href="{href(current,key)}"{current_attribute}>{escape(items[0]["title"])}</a>')
    nav="".join(links)
    asset=("../"*(len(Path(current).parts)-1))+"assets/style.css"
    script_asset=("../"*(len(Path(current).parts)-1))+"assets/site.js"
    theme_button='<button class="theme-toggle" type="button" data-theme-toggle aria-label="Switch color theme">☾</button>' if theme.get("enabled") else ""
    return f'''<!doctype html><html lang="en" data-theme="{escape(theme.get("default","system"))}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta name="description" content="{escape(profile["designation"])} — {escape(profile["name"])}"><title>{escape(title)}</title><link rel="stylesheet" href="{asset}"></head><body><div class="frame"><header class="masthead"><a href="{href(current,"index")}">{escape(profile["name"])}</a><button class="menu-toggle" type="button" data-menu-toggle aria-expanded="false" aria-controls="page-nav">Menu</button><div class="nav-wrap"><nav id="page-nav" aria-label="Pages">{nav}</nav><span class="nav-cue" aria-hidden="true">→</span></div>{theme_button}</header>{body}<footer class="footer"><strong>{escape(profile["name"])}</strong><span>{escape(profile["designation"])}</span></footer></div><script src="{script_asset}"></script></body></html>'''

photo=(f'<aside class="profile-card"><img src="{escape(profile["photo"])}" alt="Portrait of {escape(profile["name"])}"><p class="caption">{escape(profile.get("institute", ""))}</p></aside>' if profile.get("photo") else "")
interest_items="".join(f"<li>{escape(item)}</li>" for item in profile.get("research_interests",[]))
interest_list=f'<ul class="interests">{interest_items}</ul>' if interest_items else ""
cover=f'''<main><section class="cover"><div><p class="issue">{escape(profile.get("institute", ""))}</p><h1>{escape(profile["name"])}</h1><p class="role">{escape(profile["designation"])}</p><p class="affiliation">{escape(profile.get("department", ""))}</p><div class="actions">{actions()}</div></div>{photo}</section>{interest_list}</main>'''
(out/"index.html").write_text(render("index.html",profile["name"],cover),encoding="utf-8")

for page_number,(key,items) in enumerate(pages.items(),1):
    file=out/(key+".html")
    file.parent.mkdir(parents=True,exist_ok=True)
    cards=[]
    for card_index,section in enumerate(items):
        card_class="lead-section" if card_index==0 else ""
        cards.append(f'<section class="{card_class}" id="{escape(section["id"])}"><h2>{escape(section["title"])}</h2>{section["html"]}</section>')
    cards="".join(cards)
    layout_class=" stacked" if key in {"profile","work"} else ""
    content=f'''<main class="page"><header class="page-head"><span>{page_number:02d} / {len(pages):02d}</span><h1>{escape(items[0]["title"])}</h1></header><div class="articles{layout_class}">{cards}</div></main>'''
    file.write_text(render(key+".html",items[0]["title"],content),encoding="utf-8")
