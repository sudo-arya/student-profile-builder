from pathlib import Path
from html import escape
import json
r=Path(__file__).parent; d=json.loads((r/'profile-data.json').read_text(encoding='utf-8')); o=r/'dist'; (o/'details').mkdir(parents=True); p=d['profile']; sections=d['sections']; css='body{font:16px/1.6 system-ui;max-width:55rem;margin:auto;padding:2rem;color:#172033}a{color:#244f86}.links{display:grid;gap:.7rem}section{margin:2rem 0}table{width:100%;border-collapse:collapse;display:block;overflow-x:auto}th,td{border:1px solid #ccd5df;padding:.45rem;text-align:left}'
(o/'style.css').write_text(css,encoding='utf-8')
links=''.join(f'<a href="details/{s["id"]}.html">{escape(s["title"])}</a>' for s in sections)
(o/'index.html').write_text(f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="style.css"><title>{escape(p["name"])}</title></head><body><h1>{escape(p["name"])}</h1><p>{escape(p["designation"])}</p><p>{escape(p["institute"])}</p><h2>Details</h2><div class="links">{links}</div></body></html>',encoding='utf-8')
for s in sections:
    (o/'details'/f'{s["id"]}.html').write_text(f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="../style.css"><title>{escape(s["title"])}</title></head><body><a href="../index.html">← Profile</a><section><h1>{escape(s["title"])}</h1>{s["html"]}</section></body></html>',encoding='utf-8')
