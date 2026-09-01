from pathlib import Path
from html import escape
import json

root=Path(__file__).parent; data=json.loads((root/'profile-data.json').read_text(encoding='utf-8')); out=root/'dist'; out.mkdir()
p=data['profile']; sections=data['sections']; groups={'about':{'about','education','experience'},'research':{'research','projects'},'publications':{'publications'}}
pages={key:[s for s in sections if s['type'] in kinds] for key,kinds in groups.items()}; used={s['id'] for values in pages.values() for s in values}
for s in sections:
    if s['id'] not in used: pages['sections/'+s['id']]=[s]
pages={k:v for k,v in pages.items() if v}
css='body{font:16px/1.6 system-ui;max-width:54rem;margin:auto;padding:2rem;color:#172033}nav{display:flex;gap:1rem;flex-wrap:wrap;border-bottom:1px solid #ccd5df;padding-bottom:1rem}a{color:#244f86}section{margin:2rem 0}table{width:100%;border-collapse:collapse;display:block;overflow-x:auto}th,td{border:1px solid #ccd5df;padding:.45rem;text-align:left}@media(max-width:600px){body{padding:1rem}}'
(out/'assets').mkdir(); (out/'assets/style.css').write_text(css,encoding='utf-8')
def href(current,target):
    depth=len(Path(current).parts)-1; prefix='../'*depth
    return prefix+('index.html' if target=='index' else target+'.html')
def render(current,title,content):
    nav='<nav><a href="'+href(current,'index')+'">Home</a>'+''.join(f'<a href="{href(current,k)}">{escape(k.split("/")[-1].title())}</a>' for k in pages)+'</nav>'
    asset=('../'*(len(Path(current).parts)-1))+'assets/style.css'
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(title)}</title><link rel="stylesheet" href="{asset}"></head><body>{nav}{content}</body></html>'
summary=f'<h1>{escape(p["name"])}</h1><p>{escape(p["designation"])}, {escape(p["institute"])}</p>'+('<h2>Research interests</h2><ul>'+''.join(f'<li>{escape(x)}</li>' for x in p.get('research_interests',[]))+'</ul>' if p.get('research_interests') else '')
(out/'index.html').write_text(render('index.html',p['name'],summary),encoding='utf-8')
for key,items in pages.items():
    file=out/(key+'.html'); file.parent.mkdir(parents=True,exist_ok=True); content=''.join(f'<section id="{escape(s["id"])}"><h1>{escape(s["title"])}</h1>{s["html"]}</section>' for s in items); file.write_text(render(key+'.html',items[0]['title'],content),encoding='utf-8')
