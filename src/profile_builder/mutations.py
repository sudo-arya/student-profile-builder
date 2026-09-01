"""Shared validation and mutation helpers for GUI and CLI."""
from dataclasses import replace
from pathlib import Path
import re
import secrets
from urllib.parse import urlparse

from .profile import Profile, Theme, parse_profile, serialize_profile
from .utils import BuilderError

SOCIAL_FIELDS={"github","linkedin","scholar","website"}
DOMAIN_LIKE=re.compile(r"^(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[/:?#].*)?$",re.I)


def normalize_web_url(value: str) -> str:
    value=value.strip()
    if value and not urlparse(value).scheme and DOMAIN_LIKE.fullmatch(value): return "https://"+value
    return value


def validate_web_url(field: str,value: str) -> str:
    value=normalize_web_url(value)
    if not value: return ""
    parsed=urlparse(value)
    if parsed.scheme not in {"http","https"} or not parsed.netloc:
        raise BuilderError(f'Invalid {field.title()} URL. Enter a complete http:// or https:// URL.')
    return value


def update_profile_fields(root: Path, changes: dict[str,str]) -> Profile:
    path=root/"profile.md"; current=parse_profile(path,root); data=dict(current.data)
    links=dict(data.get("links",{}))
    for key,value in changes.items():
        if key in SOCIAL_FIELDS: links[key]=validate_web_url(key,value)
        elif key in data: data[key]=value.strip()
        else: raise BuilderError(f"Unknown profile field: {key}")
    data["links"]=links; candidate=Profile(data,current.markdown,current.html,current.sections,current.theme)
    serialize_profile(candidate,path); return parse_profile(path,root)


def update_appearance(root: Path,enabled: bool,default: str) -> Profile:
    if default not in {"light","dark","system"}: raise BuilderError('Appearance must be light, dark, or system.')
    path=root/"profile.md"; current=parse_profile(path,root)
    serialize_profile(Profile(current.data,current.markdown,current.html,current.sections,Theme(enabled,default)),path)
    return parse_profile(path,root)


def import_asset_bytes(root: Path,kind: str,data: bytes) -> str:
    if kind=="photo":
        if len(data)>8*1024*1024: raise BuilderError("Photo must be no larger than 8 MB.")
        ext=next((e for sig,e in ((b"\xff\xd8\xff","jpg"),(b"\x89PNG\r\n\x1a\n","png")) if data.startswith(sig)),None)
        if data.startswith(b"RIFF") and len(data)>=12 and data[8:12]==b"WEBP": ext="webp"
        if not ext: raise BuilderError("Photo must be a valid JPG, PNG, or WebP image.")
    elif kind=="cv":
        if len(data)>15*1024*1024 or not data.startswith(b"%PDF-"): raise BuilderError("CV must be a valid PDF no larger than 15 MB.")
        ext="pdf"
    elif kind=="icon":
        if len(data)>2*1024*1024: raise BuilderError("Website icon must be no larger than 2 MB.")
        if data.startswith(b"\x89PNG\r\n\x1a\n"): ext="png"
        elif data.startswith(b"\x00\x00\x01\x00"): ext="ico"
        else: raise BuilderError("Website icon must be a valid PNG or ICO file.")
    else: raise BuilderError("Unknown managed asset type.")
    managed=root/"assets/managed"; managed.mkdir(parents=True,exist_ok=True)
    name=f"{'site-icon' if kind=='icon' else kind}-{secrets.token_hex(8)}.{ext}"; (managed/name).write_bytes(data)
    return f"assets/managed/{name}"


def set_asset(root: Path,kind: str,source: Path | None) -> Profile:
    path=root/"profile.md"; current=parse_profile(path,root); data=dict(current.data); old=data.get(kind,"")
    new="" if source is None else import_asset_bytes(root,kind,source.read_bytes())
    data[kind]=new
    try: serialize_profile(Profile(data,current.markdown,current.html,current.sections,current.theme),path)
    except Exception:
        if new and (root/new).is_file(): (root/new).unlink()
        raise
    if old and old.startswith("assets/managed/") and old!=new and (root/old).is_file(): (root/old).unlink()
    return parse_profile(path,root)
