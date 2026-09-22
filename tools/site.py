#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""site.py — build/api → build/site. A static, bilingual, offline-capable site.

Every reader-facing page exists twice: English at its path, Thai at /th/<same path>. The
two are the same build function called with a different language, so a page cannot exist
in one language and silently not the other; where a record has no Thai text the Thai page
says so rather than showing machine translation.

    python3 tools/site.py
    SITE_URL=https://example.org python3 tools/site.py
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fleet  # noqa: E402
from common import BUILD, ROOT, TIER_LABEL, TYPES, jload  # noqa: E402
from css import CSS  # noqa: E402

API = BUILD / "api"
SITE = BUILD / "site"
SITE_URL = os.environ.get("SITE_URL", "https://nanobotco.github.io/hand-poke").rstrip("/")
# The repository copy is the canonical one. A companion page on wichaa.net links here
# rather than duplicating the site; CANONICAL_URL exists so that can change without a
# rebuild of the argument.
CANONICAL_URL = os.environ.get("CANONICAL_URL", SITE_URL).rstrip("/")
# Internal links are root-relative. The site is published under a path, and a host that
# serves /hand-poke with a 200 instead of redirecting to /hand-poke/ makes the browser
# resolve "./images/x.jpg" against the site root. BASE_PATH comes from SITE_URL and can be
# overridden for a local preview served at the root.
BASE_PATH = os.environ.get("BASE_PATH")
if BASE_PATH is None:
    _p = urllib.parse.urlparse(SITE_URL).path.strip("/")
    BASE_PATH = f"/{_p}/" if _p else "/"
if not BASE_PATH.endswith("/"):
    BASE_PATH += "/"

SELF = "hand-poke"
LANGS = ("en", "th")
NAME = {"en": "Hand Poke", "th": "สักด้วยมือ"}
AUTHOR = {"@type": "Person", "name": "NaN", "url": "https://wichaa.net"}
MAKER = {"@type": "Organization", "name": "wichaa.net", "url": "https://wichaa.net/",
         "description": "A manuscript corpus and knowledge hub in Chiang Mai"}
BYLINE = {"en": 'A companion to <a href="https://wichaa.net/" rel="noopener">wichaa.net</a>, '
                'where the northern manuscript corpus behind the Lanna pages is held.',
          "th": 'เว็บคู่กับ <a href="https://wichaa.net/" rel="noopener">wichaa.net</a> '
                'ที่เก็บคลังเอกสารล้านนาซึ่งเป็นที่มาของหน้าล้านนา'}
DATA_LICENSE = "https://creativecommons.org/licenses/by/4.0/"


def E(x) -> str:
    return html.escape(str(x), quote=True)


def T(d: dict, key: str, lang: str, fallback=True):
    """A field in `lang`, from text_th/names.th where the record carries it."""
    parts = key.split(".")
    if lang == "th":
        if parts[0] == "text":
            v = (d.get("text_th") or {}).get(parts[1])
            if v:
                return v
        elif parts[0] == "names":
            k = {"name": "th", "said": "said_th"}.get(parts[1])
            if k and (d.get("names") or {}).get(k):
                return d["names"][k]
        if not fallback:
            return None
    node = d
    for p in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(p)
    return node


V = jload(API / "vocab.json")
TYPE_INFO = {e["key"]: e for e in V["types"]["entries"]}
FACETS = V["facets"]["facets"]
REGIONS = {e["key"]: e for e in V["regions"]["entries"]}
TAGS = V["tags"]["tags"]
PATH_OF = {t: TYPE_INFO[t]["path"] for t in TYPE_INFO}
NODES = jload(API / "nodes.json")["nodes"]
BY_ID = {r["id"]: r for r in NODES}
SOURCES = {s["id"]: s for s in jload(API / "sources.json")["sources"]}
COV = jload(API / "coverage.json")
CH = jload(API / "charts.json")
LANGCOV = jload(API / "coverage-langs.json")
CORPUS = jload(API / "corpus.json")
FLEET = fleet.load(ROOT / "data" / "fleet.json")

TAG = {"en": f"{CH['traditions']} traditions of marking skin by hand — who is marked, "
             f"who does the marking, and where on the body",
       "th": f"ธรรมเนียมการสักด้วยมือ {CH['traditions']} ธรรมเนียม ใครถูกสัก ใครเป็นคนสัก "
             f"และสักตรงไหนของร่างกาย"}

DIR_OF = {"tradition": "traditions", "method": "methods", "tool": "tools", "ink": "inks",
          "motif": "designs", "rite": "rites", "person": "people", "place": "places",
          "term": "terms", "story": "stories", "find": "evidence", "art": "depictions",
          "org": "keepers", "issue": "questions"}

METHOD_LABEL = {
    "en": {"poke": "Poked", "tap": "Tapped", "stitch": "Stitched", "cut": "Cut",
           "mixed": "More than one", "machine": "Machine"},
    "th": {"poke": "แทง", "tap": "ตอก", "stitch": "ร้อยด้าย", "cut": "กรีด",
           "mixed": "หลายวิธี", "machine": "เครื่อง"},
}
STATUS_LABEL = {
    "en": {"living": "Living", "revived": "Revived", "thinning": "Thinning",
           "dormant": "Dormant", "historical": "Historical"},
    "th": {"living": "ยังมีอยู่", "revived": "รื้อฟื้น", "thinning": "เหลือน้อย",
           "dormant": "หยุดไป", "historical": "เป็นประวัติศาสตร์"},
}
ZONE_LABEL = {
    "en": {"face": "face", "chin": "chin", "neck": "neck", "chest": "chest", "back": "back",
           "belly": "belly", "arms": "arms", "hands": "hands", "fingers": "fingers",
           "thighs": "thighs", "legs": "legs", "knees": "knees", "feet": "feet",
           "waist-to-knee": "waist to knee", "waist-to-ankle": "waist to ankle",
           "whole-body": "whole body", "buttocks": "buttocks", "mouth": "mouth",
           "forehead": "forehead", "tongue": "tongue"},
    "th": {"face": "ใบหน้า", "chin": "คาง", "neck": "คอ", "chest": "อก", "back": "หลัง",
           "belly": "ท้อง", "arms": "แขน", "hands": "มือ", "fingers": "นิ้ว",
           "thighs": "ต้นขา", "legs": "ขา", "knees": "เข่า", "feet": "เท้า",
           "waist-to-knee": "เอวถึงเข่า", "waist-to-ankle": "เอวถึงข้อเท้า",
           "whole-body": "ทั้งตัว", "buttocks": "สะโพก", "mouth": "ปาก",
           "forehead": "หน้าผาก", "tongue": "ลิ้น"},
}

UI = {
 "en": {"home": "Hand Poke", "traditions": "Traditions", "legs": "The leg zone",
        "methods": "Four hands", "map": "Map", "timeline": "Timeline", "body": "Where",
        "words": "Words", "coverage": "Who is written about", "clothing": "Clothing",
        "counted": "Counted", "people": "People",
        "all": "Everything", "about": "How this was made",
        "kin": "Connected to", "said_here": "Named here by", "sources": "Sources",
        "prov": "Where each claim comes from", "back": "Back",
        "what": "What it is", "story": "The long version", "how": "How", "today": "Now",
        "notes": "Notes", "share": "Share", "copy": "Copy link", "print": "Print",
        "no_th": "This section has not been written in Thai yet. The English is below.",
        "unverified": "Parts of this record are marked as needing verification.",
        "more": "More", "measured": "Counted for this site", "th_name": "In Thai",
        "method": "Method", "marked": "Whose skin", "marks": "Who marks it",
        "status": "Still done?", "placement": "Where it goes", "sessions": "How long",
        "tool": "Tool", "ink": "Ink", "root": "Root", "ban": "Stopped by",
        "gap": "Years between", "n": "No."},
 "th": {"home": "สักด้วยมือ", "traditions": "ธรรมเนียม", "legs": "เขตลายขา",
        "methods": "สี่มือ", "map": "แผนที่", "timeline": "ลำดับเวลา", "body": "ตรงไหน",
        "words": "คำ", "coverage": "ใครถูกเขียนถึง", "clothing": "เครื่องนุ่งห่ม",
        "counted": "ตัวเลข", "people": "บุคคล",
        "all": "ทั้งหมด", "about": "ทำขึ้นอย่างไร",
        "kin": "เกี่ยวข้องกับ", "said_here": "ถูกอ้างถึงโดย", "sources": "แหล่งอ้างอิง",
        "prov": "แต่ละข้อความมาจากไหน", "back": "ย้อนกลับ",
        "what": "คืออะไร", "story": "ฉบับยาว", "how": "วิธี", "today": "ตอนนี้",
        "notes": "หมายเหตุ", "share": "แบ่งปัน", "copy": "คัดลอกลิงก์", "print": "พิมพ์",
        "no_th": "ส่วนนี้ยังไม่ได้เขียนเป็นภาษาไทย ด้านล่างเป็นภาษาอังกฤษ",
        "unverified": "บางส่วนของบันทึกนี้ยังต้องการการตรวจสอบ",
        "more": "เพิ่มเติม", "measured": "นับขึ้นเพื่อเว็บนี้", "th_name": "ภาษาไทย",
        "method": "วิธี", "marked": "สักบนใคร", "marks": "ใครเป็นคนสัก",
        "status": "ยังทำอยู่ไหม", "placement": "ลงตรงไหน", "sessions": "ใช้เวลาเท่าไร",
        "tool": "เครื่องมือ", "ink": "หมึก", "root": "รากศัพท์", "ban": "หยุดเพราะ",
        "gap": "ห่างกันกี่ปี", "n": "ลำดับ"},
}

NAV = [("", "home"), ("traditions/", "traditions"), ("legs/", "legs"), ("methods/", "methods"),
       ("map/", "map"), ("timeline/", "timeline"), ("body/", "body"), ("clothing/", "clothing"),
       ("words/", "words"), ("coverage/", "coverage"), ("counted/", "counted")]


def rel(depth: int = 0) -> str:
    """The site root, as a root-relative path. `depth` is ignored and kept so the call
    sites read the same; see BASE_PATH above for why this is not "../" * depth."""
    return BASE_PATH


def lroot(lang: str) -> str:
    return f"{BASE_PATH}th/" if lang == "th" else BASE_PATH


def url_of(r: dict, lang="en") -> str:
    return f"{PATH_OF[r['type']]}/{r['id']}/"


def page(title, body, depth, lang, desc="", jsonld=None, head="", cur="", path="", card=""):
    """`depth` is the page's depth below its LANGUAGE root, which is what the body's own
    links are built against. A Thai page sits one level deeper than that below the site
    root, so assets and the language switch need the site root."""
    rin = BASE_PATH + ("th/" if lang == "th" else "")
    r = BASE_PATH
    ui = UI[lang]
    en_url = f"{BASE_PATH}{path}"
    th_url = f"{BASE_PATH}th/{path}"
    bilingual = path != "api/"
    og_title = title.split(" — ")[0] if " — " in title else title
    og_desc = desc or TAG[lang]
    if og_desc.strip() == og_title.strip():
        og_desc = TAG[lang]
    og_url = f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}{path}"
    card_url = f"{CANONICAL_URL}/cards/{card or 'index'}.jpg"
    card_meta = (f'<meta property="og:image" content="{E(card_url)}">'
                 f'<meta property="og:image:secure_url" content="{E(card_url)}">'
                 f'<meta property="og:image:type" content="image/jpeg">'
                 f'<meta property="og:image:width" content="1200">'
                 f'<meta property="og:image:height" content="630">'
                 f'<meta property="og:image:alt" content="{E(og_title)}">'
                 f'<meta name="twitter:image" content="{E(card_url)}">')
    CURATTR = ' aria-current="page"'
    nav = "".join(f'<a href="{rin}{p}"{CURATTR if k == cur else ""}>{E(ui[k])}</a>'
                  for p, k in NAV)
    ld = json.dumps(jsonld or [], ensure_ascii=False)
    THATTR = ' aria-current="true"'
    thsw = (f'<a href="{th_url}"{THATTR if lang == "th" else ""} '
            f'hreflang="th">ไทย</a>') if bilingual else ""
    return f"""<!doctype html>
<html lang="{lang}"{' class="th"' if lang == 'th' else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(CANONICAL_URL)}/{"th/" if lang == "th" else ""}{E(path)}">
<link rel="alternate" href="{E(SITE_URL)}/{E(path)}">
<link rel="alternate" hreflang="en" href="{SITE_URL}/{E(path)}">
<link rel="alternate" hreflang="th" href="{SITE_URL}/th/{E(path)}">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{E(path)}">
<meta property="og:title" content="{E(og_title)}">
<meta property="og:description" content="{E(og_desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{E(og_url)}">
<meta property="og:site_name" content="{E(NAME[lang])}">
<meta property="og:locale" content="{'th_TH' if lang == 'th' else 'en_GB'}">
<meta name="twitter:card" content="summary_large_image">
{card_meta}
<link rel="icon" href="{r}icon.svg" type="image/svg+xml">
<link rel="manifest" href="{r}manifest.webmanifest">
<link rel="alternate" type="application/atom+xml" href="{r}feed.xml">
<style>{CSS}</style>{head}
<script type="application/ld+json">{ld}</script>
<script defer src="{r}copy.js"></script>
</head>
<body>
<a class="sr" href="#main">Skip to content</a>
<header class="top"><div class="in">
<a class="brand" href="{rin}">Hand <b>Poke</b></a>
<nav>{nav}</nav>
<span class="langsw">
<a href="{en_url}"{THATTR if lang == 'en' else ''} hreflang="en">EN</a>
{thsw}
</span>
</div></header>
<main id="main">
{body}
</main>
<footer class="bot"><div class="in">
<p><b>{E(NAME[lang])}</b> — {E(TAG[lang])}</p>
<p>{'Records CC BY 4.0. Country outlines from Natural Earth, public domain. Corpus text from Wikipedia, CC BY-SA 4.0. Books scanned by the Internet Archive, out of copyright. Pictures from Wikimedia Commons, licensed per file with the author beside each one.' if lang == 'en' else 'บันทึกเผยแพร่ภายใต้ CC BY 4.0 เส้นขอบประเทศจาก Natural Earth สาธารณสมบัติ เนื้อหาจากวิกิพีเดีย ภายใต้ CC BY-SA 4.0 หนังสือสแกนโดย Internet Archive หมดลิขสิทธิ์แล้ว ภาพจากวิกิมีเดียคอมมอนส์ ตามสัญญาอนุญาตของแต่ละไฟล์ พร้อมชื่อผู้ถ่าย'}</p>
<p class="byline">{BYLINE[lang]}</p>
<p><a href="{rin}about/">{E(ui['about'])}</a> · <a href="{r}api/">API</a> · <a href="{rin}all/">{E(ui['all'])}</a> · <a href="{r}llms.txt">llms.txt</a></p>
{fleet.row_html(SELF, label=("More from the same publisher" if lang == "en" else "เว็บอื่นของผู้จัดทำ"), roster=FLEET)}
{fleet.support_html(roster=FLEET)}
</div></footer>
</body></html>
"""


def marks(text: str) -> str:
    t = E(text)
    t = re.sub(r"\*(Inference|Tradition holds|Tradition|อนุมาน|ตามธรรมเนียม)\s*—\*",
               lambda m: f'<mark class="inf">{m.group(1)} —</mark>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def prose(text: str) -> str:
    if not text:
        return ""
    out, bullets = [], []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("- "):
            items = "".join(f"<li>{marks(li[2:])}</li>" for li in para.split("\n")
                            if li.strip().startswith("- "))
            out.append(f"<ul>{items}</ul>")
        else:
            out.append(f"<p>{marks(para)}</p>")
    return "".join(out)


ICONS = {
 "facebook": "M17 2h-3a5 5 0 0 0-5 5v3H6v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z",
 "line": "M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.2 7.9.3.07.8.2.9.5.1.3.07.7.03 1l-.14.9c-.04.3-.2 1 .9.55 1.1-.45 6-3.5 8.2-6C21.4 14.2 22 12.7 22 11c0-4.4-4.5-8-10-8z",
 "whatsapp": "M20 12a8 8 0 0 1-11.9 7L4 20l1-4.1A8 8 0 1 1 20 12z",
 "x": "M3 3l7.5 9.5L3.5 21h2l6-6.8L17 21h4l-7.9-10L20.5 3h-2l-5.6 6.4L8 3z",
 "reddit": "M22 12a2 2 0 0 0-3.4-1.4A11 11 0 0 0 13 9l.9-3.4 2.6.6a1.6 1.6 0 1 0 .2-1.4l-3.4-.8-1.3 4.9A11 11 0 0 0 5.4 10.6 2 2 0 1 0 3.6 14 4 4 0 0 0 3.5 15c0 3 3.8 5.5 8.5 5.5s8.5-2.5 8.5-5.5a4 4 0 0 0-.1-1A2 2 0 0 0 22 12z",
 "mail": "M3 6h18v12H3zM3 6l9 7 9-7",
 "link": "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1",
 "print": "M7 8V3h10v5M7 18H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2M7 14h10v7H7z",
}


def _icon(name: str) -> str:
    d = ICONS.get(name, "")
    fill = "none" if name in ("mail", "link", "print", "whatsapp") else "currentColor"
    return (f'<svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" '
            f'fill="{fill}" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{d}"/></svg>')


def share_row(url: str, title: str, lang: str, blurb: str = "") -> str:
    ui = UI[lang]
    en = lang == "en"
    q = urllib.parse.quote
    share_text = f"{title} — {blurb}" if blurb else title
    links = [
        ("facebook", "Facebook", f"https://www.facebook.com/sharer/sharer.php?u={q(url)}"),
        ("line", "LINE", f"https://social-plugins.line.me/lineit/share?url={q(url)}"),
        ("whatsapp", "WhatsApp", f"https://api.whatsapp.com/send?text={q(share_text + ' ' + url)}"),
        ("x", "X", f"https://twitter.com/intent/tweet?text={q(share_text)}&url={q(url)}"),
        ("reddit", "Reddit", f"https://reddit.com/submit?url={q(url)}&title={q(title)}"),
        ("mail", "Email", f"mailto:?subject={q(title)}&body={q(share_text + chr(10) + chr(10) + url)}"),
    ]
    btns = "".join(
        f'<a class="sh sh-{k}" href="{E(href)}" rel="noopener" target="_blank" '
        f'data-share="{E(k)}">{_icon(k)}<span>{E(label)}</span></a>'
        for k, label, href in links)
    head = "Send this to whoever you train with" if en else "ส่งให้คนที่ซ้อมด้วยกัน"
    sub = "It opens the same in Thai." if en else "เปิดเป็นภาษาอังกฤษได้เหมือนกัน"
    return (f'<aside class="sharebar"><div class="shhead"><b>{E(head)}</b>'
            f'<span class="mute small">{E(sub)}</span></div>'
            f'<div class="shrow">{btns}'
            f'<button type="button" class="sh sh-link" data-copy="{E(url)}">'
            f'{_icon("link")}<span>{E(ui["copy"])}</span></button>'
            f'<button type="button" class="sh sh-print" onclick="window.print()">'
            f'{_icon("print")}<span>{E(ui["print"])}</span></button>'
            f'<button type="button" class="sh sh-native" hidden data-native="{E(url)}" '
            f'data-title="{E(title)}">{_icon("link")}<span>'
            f'{E("Share…" if en else "แชร์…")}</span></button></div></aside>'
            '<script>document.addEventListener("DOMContentLoaded",function(){'
            'var n=document.querySelector(".sh-native");'
            'if(n&&navigator.share){n.hidden=false;n.addEventListener("click",function(){'
            'navigator.share({title:n.dataset.title,url:n.dataset.native}).catch(function(){})})}});'
            "</script>")


# ---------------------------------------------------------------- small parts
def tier_chip(p: dict, lang="en") -> str:
    t = (p or {}).get("tier", "")
    return f'<span class="tier {E(t)}">{E(t)}</span>' if t else ""


def src_link(sid: str, lang="en") -> str:
    s = SOURCES.get(sid)
    if not s:
        return E(sid)
    t = E(s.get("title") or sid)
    pub = E(s.get("publisher") or "")
    if s.get("url"):
        return f'<a href="{E(s["url"])}" rel="noopener">{t}</a>{" — " + pub if pub else ""}'
    return f"{t} — {pub}"


def prov_block(r: dict, lang: str) -> str:
    ui = UI[lang]
    pv = r.get("provenance") or {}
    rows = [("<em>default</em>", pv.get("default") or {})]
    rows += [(E(k), v) for k, v in (pv.get("fields") or {}).items()]
    body = "".join(
        f"<tr><td>{k}</td><td>{tier_chip(v, lang)}</td>"
        f"<td>{src_link(v.get('source'), lang) if v.get('source') else ''}</td>"
        f"<td class='small mute'>{E(v.get('note') or '')}</td></tr>" for k, v in rows)
    srcs = "".join(f"<li>{src_link(s, lang)}</li>" for s in r.get("sources", []))
    return (f'<details><summary>{E(ui["prov"])}</summary>'
            f'<div class="scroll"><table><thead><tr><th>Field</th><th>Tier</th><th>Source</th>'
            f'<th>Note</th></tr></thead><tbody>{body}</tbody></table></div>'
            f'<h3>{E(ui["sources"])}</h3><ul class="small">{srcs}</ul>'
            f'<p class="small mute">' +
            " · ".join(f"<b>{E(k)}</b> {E(v)}" for k, v in TIER_LABEL.items()) +
            "</p></details>")


def clip(t: str, n: int) -> str:
    t = (t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def credit(im: dict, short=False) -> str:
    """Licence, author and a link to the Commons page, beside the picture. Share-alike is
    complied with rather than avoided, so the terms travel with the file."""
    who = E(im.get("author") or "unknown")
    lic = E(im.get("license") or "")
    page_url = im.get("page_url") or ""
    lic_html = (f'<a href="{E(im["license_url"])}" rel="license noopener">{lic}</a>'
                if im.get("license_url") else lic)
    src = f'<a href="{E(page_url)}" rel="noopener">Commons</a>' if page_url else ""
    note = E(im.get("credit") or "") if im.get("source") == "own" else ""
    parts = [who, note, lic_html] if note else [who, lic_html]
    if not short and src:
        parts.append(src)
    return " · ".join(x for x in parts if x)



def shot_link(href: str, src: str, label: str, im: dict = None) -> str:
    """A picture that leads somewhere, in four layers: the photograph as a background, a
    scrim under the words, a spacer that gives the box its height, and the text over both.
    The whole box is the link, so the picture is not a decoration beside one."""
    cred = f'<span class="cred">{credit(im, short=True)}</span>' if im else ""
    return (f'<figure class="thumb"><h3><a class="shot" href="{E(href)}">'
            f'<span class="bg" style="background-image:url({E(src)})"></span>'
            f'<span class="scrim"></span><span class="sp"></span>'
            f'<span class="tx">{E(label)}</span></a></h3>{cred}</figure>')


def img_url(im: dict, thumb=False) -> str:
    f = im["file"]
    if thumb:
        f = f.rsplit(".", 1)[0] + ".thumb.jpg"
    return f"{rel()}images/{f}"


def pictures(n: dict) -> list:
    return [i for i in (n.get("images") or []) if i.get("file")]


def hero_shot(n: dict) -> str:
    ims = pictures(n)
    if not ims:
        return ""
    im = next((i for i in ims if i.get("primary")), ims[0])
    return (f'<div class="hero-shot"><img src="{E(img_url(im))}" alt="{E(im.get("alt") or "")}" '
            f'loading="lazy" decoding="async">'
            f'<span class="cap">{credit(im, short=True)}</span></div>')


def shot_strip(ims: list) -> str:
    if not ims:
        return ""
    out = ['<div class="strip">']
    for im in ims:
        out.append(f'<figure><img src="{E(img_url(im, thumb=True))}" '
                   f'alt="{E(im.get("alt") or "")}" loading="lazy" decoding="async">'
                   f'<figcaption>{credit(im, short=True)}</figcaption></figure>')
    out.append("</div>")
    return "".join(out)


def node_card(n: dict, lang: str, n_label=None) -> str:
    r = lroot(lang)
    name = T(n, "names.name", lang)
    th = n["names"].get("th")
    what = T(n, "text.what", lang) or ""
    pr = n.get("practice") or {}
    meta = []
    if pr.get("method"):
        meta.append(f'<span class="tag {METHOD_CLASS.get(pr["method"], "")}">'
                    f'{E(METHOD_LABEL[lang].get(pr["method"], pr["method"]))}</span>')
    if pr.get("status"):
        meta.append(f'<span class="tag">{E(STATUS_LABEL[lang].get(pr["status"], pr["status"]))}</span>')
    for t in (n.get("tags") or [])[:2]:
        meta.append(f'<span class="tag">{E(t)}</span>')
    ims = pictures(n)
    thumb = ""
    if ims:
        im = next((i for i in ims if i.get("primary")), ims[0])
        thumb = shot_link(f"{r}{url_of(n)}", img_url(im, thumb=True), name, im)
    num = f'<span class="n">{n_label}</span>' if n_label else ""
    thai = f'<p class="th">{E(th)}</p>' if th and lang == "en" else ""
    head = "" if thumb else f'<h3><a href="{r}{url_of(n)}">{E(name)}</a></h3>'
    return (f'<article class="card">{num}{thumb}{head}{thai}'
            f'<p>{E(clip(what, 150))}</p>'
            f'<div class="tags">{"".join(meta)}</div></article>')


# ---------------------------------------------------------------- parallax bands
# Hand-picked backgrounds. A Commons search returns a lot that is true and useless, so a
# picture that gets a full-width band is named here rather than taken from whatever sorts
# first. Each entry is (record id, filename fragment); the fragment picks one file.
BANDS = {
    "legs":     ("sak-kha-lai", "peinture"),
    "murals":   ("murals", ""),
    "burma":    ("htoe-kwin", "burmese-tattooing"),
    "tools":    ("khem-sak", ""),
    "pacific":  ("tatau", "samoan-malu"),
    "arctic":   ("kakiniit", "milukkattuk"),
    "luzon":    ("whang-od", "whang-od-tattooing"),
    "japan":    ("irezumi", "roshi"),
    "chin":     ("chin-ming", "letu"),
    "yant":     ("sak-yant", "chiang-mai"),
    "mentawai": ("mentawai-titi", "waterfall"),
    "bosnia":   ("sicanje", "bh-croats"),
}


def band_image(key: str):
    rid, frag = BANDS.get(key, (None, None))
    n = BY_ID.get(rid or "")
    ims = pictures(n) if n else []
    if not ims:
        return None
    if frag:
        for im in ims:
            if frag in im["file"]:
                return im
    return next((i for i in ims if i.get("primary")), ims[0])


def band(key: str, kicker: str, head: str, line: str = "", lang: str = "en",
         big: str = "", big_label: str = "", href: str = "", cta: str = "",
         cls: str = "") -> str:
    """One full-bleed parallax band. Returns "" when the picture is missing, so a band
    never ships as an empty black strip."""
    im = band_image(key)
    if not im:
        return ""
    inner = [f'<span class="kicker">{E(kicker)}</span>']
    if big:
        inner.append(f'<p class="big">{E(big)}'
                     f'{f"<small>{E(big_label)}</small>" if big_label else ""}</p>')
    if head:
        inner.append(f"<h2>{E(head)}</h2>")
    if line:
        inner.append(f"<p>{E(line)}</p>")
    if href and cta:
        inner.append(f'<a class="btn" href="{E(href)}">{E(cta)}</a>')
    return (f'<section class="band {cls}" style="background-image:url({E(img_url(im))})">'
            f'<div class="in">{"".join(inner)}</div>'
            f'<span class="cred">{credit(im, short=True)}</span></section>')


def slab(cells) -> str:
    return '<div class="slab">' + "".join(
        f"<div><b>{E(v)}</b><span>{E(l)}</span></div>" for v, l in cells) + "</div>"


def by_type(t: str) -> list:
    return [n for n in NODES if n["type"] == t]


def grid(nodes, lang, numbered=False) -> str:
    return '<div class="grid">' + "".join(
        node_card(n, lang, str(i + 1) if numbered else None) for i, n in enumerate(nodes)
    ) + "</div>"


# ---------------------------------------------------------------- charts
METHOD_CLASS = {"poke": "mpoke", "tap": "mtap", "stitch": "mstitch", "cut": "mcut",
                "mixed": "mmix", "machine": "mmach"}


def barchart(rows, lang="en", note="", maxv=None) -> str:
    """rows: (label, value, class, right-hand note). One bar each, widths as a share of the
    largest value, the number printed beside every bar."""
    if not rows:
        return ""
    mx = maxv or max((r[1] for r in rows), default=1) or 1
    out = ['<div class="barchart">']
    for label, val, cls, right in rows:
        w = max(1.2, 100.0 * val / mx)
        out.append(f'<div class="brow"><span class="blab">{E(label)}</span>'
                   f'<span class="btrack"><span class="bar {E(cls)}" style="width:{w:.1f}%"></span></span>'
                   f'<span class="bval">{E(val)}{f" <small>{E(right)}</small>" if right else ""}</span></div>')
    out.append("</div>")
    if note:
        out.append(f'<p class="mute small">{marks(note)}</p>')
    return "".join(out)


def legend(pairs) -> str:
    return ('<p class="legend">' + "".join(
        f'<span class="lg"><i class="sw {E(cls)}"></i>{E(label)}</span>' for label, cls in pairs)
        + "</p>")


def year_label(y: int, lang="en") -> str:
    if y < 0:
        return f"{abs(y):,} BCE" if lang == "en" else f"{abs(y):,} ก่อน ค.ศ."
    return f"{y:,}" if lang == "en" else f"ค.ศ. {y:,}"


def timeline_svg(rows, lang="en", w=1060) -> str:
    """A broken scale: everything before year 0 is compressed, because five thousand years
    of bodies and two hundred years of paper cannot share one axis at one rate without one
    of them vanishing. The break is drawn. Labels sit at the start of each span, which is
    the end that is dated; the far end of a living tradition is today."""
    rows = [r for r in rows if r.get("from") is not None]
    if not rows:
        return ""
    lo = min(r["from"] for r in rows)
    pad, right = 86, 16
    split_x = 0.30 * w

    def X(y):
        if y <= 0:
            return pad + (y - lo) / (0 - lo) * (split_x - pad)
        return split_x + min(1.0, y / 2050.0) * (w - split_x - right)

    h = 46 + 24 * len(rows)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="tl" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="Dated points, from the oldest marked skin to now">']
    for y in (lo, -2000, -1000, 0, 500, 1000, 1500, 1800, 1900, 2000):
        if y < lo:
            continue
        x = X(y)
        out.append(f'<line class="tlgrid" x1="{x:.0f}" y1="20" x2="{x:.0f}" y2="{h - 20}"/>'
                   f'<text class="tlyr" x="{x:.0f}" y="13" text-anchor="middle">'
                   f'{year_label(y, lang)}</text>')
    out.append(f'<line class="tlbreak" x1="{split_x:.0f}" y1="16" x2="{split_x:.0f}" '
               f'y2="{h - 16}"/>')
    for i, r in enumerate(rows):
        y = 36 + 24 * i
        x1, x2 = X(r["from"]), X(max(r["to"], r["from"]))
        cls = {"find": "tfind", "story": "tstory", "tradition": "ttrad",
               "method": "tmeth"}.get(r["type"], "tother")
        thin = 6 if r["type"] == "tradition" else 10
        if x2 - x1 < 4:
            out.append(f'<circle class="tdot {cls}" cx="{x1:.0f}" cy="{y:.0f}" r="4.5"/>')
        else:
            out.append(f'<rect class="tbar {cls}" x="{x1:.0f}" y="{y - thin / 2:.0f}" '
                       f'width="{x2 - x1:.0f}" height="{thin}" rx="3"/>')
        # the label goes at the dated end, inside the frame
        if x1 > w * 0.62:
            tx, anchor = x1 - 9, "end"
        else:
            tx, anchor = x1 + 9, "start"
        circa = "c. " if r.get("circa") and lang == "en" else ""
        out.append(f'<text class="tlab" x="{tx:.0f}" y="{y - 8:.0f}" text-anchor="{anchor}">'
                   f'{E(circa + r["name"])}</text>')
    out.append("</svg>")
    return "".join(out)


def inline_svg(name: str) -> str:
    """Inline the drawn map. An <img> pointing at an SVG is an isolated document, so a
    CSS variable on the page never reaches it and the sea comes out light on a dark page."""
    p = SITE / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def taxonomy_svg(lang="en", w=920) -> str:
    """The four hands, and the machine outside them, with the count of traditions on each."""
    m = CH["by_method"]
    ml = METHOD_LABEL[lang]
    kids = [("poke", ml["poke"], "one point, pushed by the hand that holds it",
             "ปลายเดียว ดันด้วยมือที่ถือ"),
            ("tap", ml["tap"], "a hafted comb, struck by a second stick",
             "หวีติดด้าม ตอกด้วยไม้อีกอัน"),
            ("stitch", ml["stitch"], "a threaded needle, drawn under the skin",
             "เข็มร้อยด้าย ลอดใต้ผิวหนัง"),
            ("cut", ml["cut"], "an incision, rubbed with pigment",
             "กรีดแล้วถูสีลงไป")]
    h = 300
    bw, gap = 190, 22
    x0 = (w - (bw * 4 + gap * 3)) / 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="tax" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="Four hand methods and the machine, with how many '
           f'traditions on this site use each">']
    out.append(f'<rect class="taxtop" x="{w / 2 - 150:.0f}" y="8" width="300" height="42" rx="6"/>'
               f'<text class="taxh" x="{w / 2:.0f}" y="35" text-anchor="middle">'
               f'{E("By hand" if lang == "en" else "ด้วยมือ")}</text>')
    for i, (key, label, note_en, note_th) in enumerate(kids):
        x = x0 + i * (bw + gap)
        out.append(f'<path class="taxline" d="M{w / 2:.0f} 50 V72 H{x + bw / 2:.0f} V96"/>')
        out.append(f'<rect class="taxbox {METHOD_CLASS[key]}" x="{x:.0f}" y="96" '
                   f'width="{bw}" height="108" rx="8"/>')
        out.append(f'<text class="taxn" x="{x + bw / 2:.0f}" y="140" text-anchor="middle">'
                   f'{m.get(key, 0)}</text>')
        out.append(f'<text class="taxl" x="{x + bw / 2:.0f}" y="166" text-anchor="middle">'
                   f'{E(label)}</text>')
        note = note_en if lang == "en" else note_th
        words = note.split()
        line1 = " ".join(words[:5])
        line2 = " ".join(words[5:])
        out.append(f'<text class="taxs" x="{x + bw / 2:.0f}" y="184" text-anchor="middle">'
                   f'{E(line1)}</text>'
                   f'<text class="taxs" x="{x + bw / 2:.0f}" y="198" text-anchor="middle">'
                   f'{E(line2)}</text>')
    out.append(f'<rect class="taxbox mmach" x="{w / 2 - 150:.0f}" y="238" width="300" height="50" rx="8"/>'
               f'<text class="taxl dark" x="{w / 2:.0f}" y="268" text-anchor="middle">'
               f'{E("Machine, from 1891" if lang == "en" else "เครื่องสัก ตั้งแต่ปี 1891")}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- front page
def front(lang: str) -> str:
    ui = UI[lang]
    r = lroot(lang)
    en = lang == "en"
    b = [f'<h1>{E(NAME[lang])}</h1>', f'<p class="lede">{E(TAG[lang])}</p>']
    b.append(slab([
        (CH["traditions"], "traditions" if en else "ธรรมเนียม"),
        (len(CH["by_method"]), "hand methods" if en else "วิธีของมือ"),
        (len(CH["countries"]), "countries" if en else "ประเทศ"),
        (f"{CH['timeline'][0]['from'] * -1:,} BCE" if en else f"{CH['timeline'][0]['from'] * -1:,} ปีก่อน ค.ศ.",
         "oldest dated skin" if en else "ผิวหนังที่เก่าที่สุด"),
    ]))
    b.append(band("legs", "The finding" if en else "ข้อค้นพบ",
                  "The tattoo is clothing" if en else "รอยสักคือเครื่องนุ่งห่ม",
                  ("Burmese, Northern Thai, Spanish and Samoan sources reach for the same "
                   "comparison, and none of them had read the others."
                   if en else
                   "แหล่งข้อมูลพม่า ล้านนา สเปน และซามัว เลือกคำเปรียบเดียวกัน โดยไม่ได้อ่านของกันและกัน"),
                  lang, big=str(len(CH["clothing"])),
                  big_label="traditions say so" if en else "ธรรมเนียมที่พูดแบบนี้",
                  href=f"{r}clothing/", cta="Read the quotes" if en else "อ่านคำที่ยกมา"))
    b.append(f'<h2>{E("Start here" if en else "เริ่มตรงนี้")}</h2>')
    starters = [n for n in NODES if "start-here" in (n.get("tags") or [])]
    b.append(grid(starters[:12], lang))
    b.append(band("burma", "The deep one" if en else "หน้าหลัก",
                  "One custom, four peoples, one border in the wrong place"
                  if en else "ธรรมเนียมเดียว สี่กลุ่มชน และพรมแดนที่วางผิดที่",
                  ("Burma, the Shan States and Lanna tattooed their men from the waist down. "
                   "The record noticed the first two and read the third as Siam."
                   if en else
                   "พม่า รัฐฉาน และล้านนา สักผู้ชายตั้งแต่เอวลงไป บันทึกเห็นสองกลุ่มแรก และอ่านกลุ่มที่สามเป็นสยาม"),
                  lang, href=f"{r}legs/", cta="The leg zone" if en else "เขตลายขา"))
    b.append(f'<h2>{E("The four hands" if en else "สี่มือ")}</h2>')
    b.append(taxonomy_svg(lang))
    b.append(f'<p><a class="btn" href="{r}methods/">'
             f'{E("How each one works" if en else "แต่ละวิธีทำงานอย่างไร")}</a></p>')
    b.append(f'<h2>{E("Everywhere it is recorded" if en else "ที่ไหนบ้างที่มีบันทึก")}</h2>')
    cap = ("One dot per tradition, coloured by method. Equal Earth, because the subject is "
           "how many of a thing are where. A country is shaded when a tradition on this "
           "site was practised there."
           if en else
           "หนึ่งจุดต่อหนึ่งธรรมเนียม สีตามวิธี ใช้การฉายแบบ Equal Earth เพราะเรื่องนี้คือของอย่างหนึ่งมีอยู่ที่ไหนบ้าง")
    b.append(f'<figure class="map">{inline_svg("world.svg")}'
             f'<figcaption>{E(cap)}</figcaption></figure>')
    b.append(legend([(METHOD_LABEL[lang][k], METHOD_CLASS[k]) for k in
                     ("poke", "tap", "stitch", "cut")]))
    b.append(f'<p><a class="btn" href="{r}map/">{E("The map, with the list" if en else "แผนที่พร้อมรายชื่อ")}</a></p>')
    b.append(f'<h2>{E("Who gets written about" if en else "ใครถูกเขียนถึง")}</h2>')
    rows = [(x["name"], x["n"], "mpoke", "") for x in LANGCOV["rows"] if x.get("n")][:8]
    b.append(barchart(rows, lang,
                      note=(f"Wikipedia language editions carrying an article about the "
                            f"tattooing itself. {LANGCOV['with_own_article']} of "
                            f"{LANGCOV['traditions']} traditions have one at all."
                            if en else
                            f"จำนวนภาษาของวิกิพีเดียที่มีบทความเรื่องการสักนั้นโดยตรง "
                            f"{LANGCOV['with_own_article']} จาก {LANGCOV['traditions']} ธรรมเนียมเท่านั้นที่มี")))
    b.append(f'<p><a class="btn" href="{r}coverage/">{E("The whole count" if en else "การนับทั้งหมด")}</a></p>')
    b.append(band("tools", "Instruments" if en else "เครื่องมือ",
                  "Two feet of brass, weighted with a bird" if en else "ทองเหลืองยาวสองฟุต ถ่วงด้วยรูปนก",
                  ("Shway Yoe took the Burmese pricker apart in print in 1882: a split "
                   "four-way point that carries its own ink, a hollow shaft, and the weight "
                   "at the far end."
                   if en else
                   "เชวโยถอดเครื่องมือสักของพม่าออกเป็นชิ้นๆ ในปี 1882 ปลายผ่าสี่แฉกที่อุ้มสีไว้เอง ก้านกลวง และน้ำหนักอยู่ปลายบน"),
                  lang, href=f"{r}tools/", cta="The instruments" if en else "เครื่องมือ"))
    b.append(f'<h2>{E("Sections" if en else "หมวด")}</h2>')
    cards = []
    for t in TYPES:
        rows_t = by_type(t)
        if not rows_t:
            continue
        ti = TYPE_INFO[t]
        cards.append(f'<article class="card"><h3><a href="{r}{DIR_OF[t]}/">'
                     f'{E(ti["th"] if lang == "th" else ti["name"])}</a> '
                     f'<span class="n">{len(rows_t)}</span></h3>'
                     f'<p>{E(ti["th_blurb"] if lang == "th" else ti["blurb"])}</p></article>')
    b.append('<div class="grid">' + "".join(cards) + "</div>")
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}", NAME[lang], lang,
                       TAG[lang]))
    return "".join(b)


# ---------------------------------------------------------------- sections
def traditions_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    ml = METHOD_LABEL[lang]
    sl = STATUS_LABEL[lang]
    rows = by_type("tradition")
    b = [f'<h1>{E("The traditions" if en else "ธรรมเนียม")}</h1>',
         f'<p class="lede">{E(TAG[lang])}</p>']
    b.append(slab([(CH["traditions"], "traditions" if en else "ธรรมเนียม"),
                   (CH["by_status"].get("living", 0) + CH["by_status"].get("revived", 0),
                    "living or revived" if en else "ยังมีอยู่หรือรื้อฟื้น"),
                   (CH["by_status"].get("dormant", 0), "dormant" if en else "หยุดไป"),
                   (len(CH["breaks"]), "with a datable break" if en else "ระบุช่วงขาดตอนได้")]))
    b.append(barchart([(sl[k], v, {"living": "mtap", "revived": "mstitch", "thinning": "mcut",
                                   "dormant": "mpoke", "historical": "mmix"}.get(k, "mmix"), "")
                       for k, v in CH["by_status"].items()], lang))
    for key in ("poke", "tap", "stitch", "cut", "mixed"):
        grp = [n for n in rows if (n.get("practice") or {}).get("method") == key]
        if not grp:
            continue
        b.append(f'<h2>{E(ml[key])} <span class="n">{len(grp)}</span></h2>')
        b.append(grid(sorted(grp, key=lambda n: T(n, "names.name", lang) or ""), lang))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}traditions/",
                       "The traditions" if en else "ธรรมเนียม", lang))
    return "".join(b)


def methods_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    lede = ("A hand can put pigment under skin in four ways, and the traditions that use "
            "each one know the difference even where English does not."
            if en else
            "มือคนนำสีลงใต้ผิวหนังได้สี่วิธี และธรรมเนียมที่ใช้แต่ละวิธีรู้ความต่าง แม้ภาษาอังกฤษจะไม่รู้")
    b = [f'<h1>{E("Four hands" if en else "สี่มือ")}</h1>',
         f'<p class="lede">{E(lede)}</p>']
    b.append(taxonomy_svg(lang))
    b.append(barchart([(METHOD_LABEL[lang][k], v, METHOD_CLASS[k], "") for k, v in
                       CH["by_method"].items()], lang,
                      note=("Counted from the method field on every tradition record."
                            if en else "นับจากช่องวิธีของบันทึกธรรมเนียมทุกชิ้น")))
    for n in by_type("method"):
        if n["id"] == "machine":
            continue
        b.append(f'<h2><a href="{r}{url_of(n)}">{E(T(n, "names.name", lang))}</a></h2>')
        b.append(prose(T(n, "text.what", lang)))
        b.append(prose(T(n, "text.story", lang)))
    mach = BY_ID.get("machine")
    if mach:
        b.append(f'<h2>{E("And the one that renamed them" if en else "และสิ่งที่ตั้งชื่อใหม่ให้ทั้งหมด")}</h2>')
        b.append(prose(T(mach, "text.story", lang)))
        b.append(f'<p><a href="{r}{url_of(mach)}">{E(T(mach, "names.name", lang))}</a></p>')
    q = BY_ID.get("what-counts")
    if q:
        b.append(f'<div class="note"><h3>{E(T(q, "names.name", lang))}</h3>'
                 f'{prose(T(q, "text.story", lang))}'
                 f'<p><a href="{r}{url_of(q)}">{E("The whole question" if en else "คำถามทั้งหมด")}</a></p></div>')
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}methods/",
                       "Four hands" if en else "สี่มือ", lang))
    return "".join(b)


def map_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    lede = ("One dot per tradition, placed at a point that stands for where it was "
            "practised — not a boundary, and not a claim about who lives there now."
            if en else
            "หนึ่งจุดต่อหนึ่งธรรมเนียม วางไว้ที่จุดแทนบริเวณที่เคยปฏิบัติ ไม่ใช่เส้นแบ่ง และไม่ใช่ข้อความเรื่องผู้คนในปัจจุบัน")
    b = [f'<h1>{E("The map" if en else "แผนที่")}</h1>',
         f'<p class="lede">{E(lede)}</p>']
    b.append(f'<figure class="map">{inline_svg("world.svg")}</figure>')
    b.append(legend([(METHOD_LABEL[lang][k], METHOD_CLASS[k]) for k in
                     ("poke", "tap", "stitch", "cut", "mixed")]))
    regions = {}
    for n in by_type("tradition"):
        regions.setdefault((n.get("region") or ["worldwide"])[0], []).append(n)
    for key, e in REGIONS.items():
        grp = regions.get(key)
        if not grp:
            continue
        b.append(f'<h2>{E(e["th"] if lang == "th" else e["name"])} '
                 f'<span class="n">{len(grp)}</span></h2><ul class="cols">')
        for n in sorted(grp, key=lambda x: T(x, "names.name", lang) or ""):
            p = n.get("practice") or {}
            b.append(f'<li><a href="{r}{url_of(n)}">{E(T(n, "names.name", lang))}</a> '
                     f'<span class="mute small">{E(METHOD_LABEL[lang].get(p.get("method"), ""))}'
                     f' · {E(STATUS_LABEL[lang].get(p.get("status"), ""))}</span></li>')
        b.append("</ul>")
    b.append(f'<h2>{E("The zone map" if en else "แผนที่เขต")}</h2>')
    zn = ("The one map on this site that no source drew: the leg-tattoo zone, across three "
          "modern countries." if en else
          "แผนที่เดียวบนเว็บนี้ที่ไม่มีแหล่งไหนวาดไว้ เขตลายขาพาดสามประเทศปัจจุบัน")
    b.append(f'<p>{E(zn)} <a href="{r}legs/">{E("The leg zone" if en else "เขตลายขา")}</a></p>')
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}map/",
                       "The map" if en else "แผนที่", lang))
    return "".join(b)


def legs_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    b = [f'<h1>{E("The leg zone" if en else "เขตลายขา")}</h1>']
    lede = ("Burma, the Shan States and Lanna tattooed their men from the waist down, in "
            "patterns dense enough that every source reaches for a garment to describe them. "
            "The zone's edge runs through the middle of modern Thailand."
            if en else
            "พม่า รัฐฉาน และล้านนา สักผู้ชายตั้งแต่เอวลงไป แน่นจนทุกแหล่งข้อมูลต้องหยิบชื่อเสื้อผ้ามาอธิบาย "
            "และขอบของเขตนี้พาดกลางประเทศไทยปัจจุบัน")
    b.append(f'<p class="lede">{E(lede)}</p>')
    cap = ("The zone as this site reads four written sources and one manuscript. Nobody "
           "surveyed it. The blue line is the modern Thai border."
           if en else
           "เขตนี้คือการอ่านแหล่งข้อมูลสี่ชิ้นกับเอกสารหนึ่งเล่มของเว็บนี้ ไม่มีใครเคยสำรวจ เส้นสีน้ำเงินคือพรมแดนไทยปัจจุบัน")
    b.append(f'<figure class="map">{inline_svg("legs.svg")}<figcaption>{E(cap)}</figcaption></figure>')

    b.append(f'<h2>{E("Four sources, side by side" if en else "สี่แหล่ง วางเรียงกัน")}</h2>')
    quotes = [
        ("s:shway-yoe", 1882, "Upper Burma",
         "Nearly all Bamar men were tattooed at boyhood, from the waist to the knees.",
         "ชายพม่าเกือบทุกคนถูกสักตั้งแต่เด็ก ตั้งแต่เอวถึงเข่า"),
        ("s:milne-shans", 1910, "the Shan States",
         "A Shan boy is considered to have reached manhood when he has been tattooed… "
         "the rule is to tattoo both legs from waist to knee.",
         "เด็กชายไทใหญ่ถือว่าเป็นผู้ใหญ่เมื่อได้สักแล้ว กติกาคือสักสองขาตั้งแต่เอวถึงเข่า"),
        ("s:ms6968", 0, "Lanna",
         "…until it looked as if they wore black trousers… from the waist down to the ankles.",
         "จนดูเหมือนนุ่งกางเกงสีดำ ตั้งแต่บั้นเอวลงมาจนถึงข้อเท้า"),
        ("s:milne-shans", 1910, "Siam",
         "The Siamese, who are so closely related to them, tattoo themselves very slightly, "
         "or not at all.",
         "ชาวสยามซึ่งเป็นเครือญาติใกล้ชิด สักน้อยมากหรือไม่สักเลย"),
    ]
    rows = []
    for sid, year, place, q_en, q_th in quotes:
        s = SOURCES.get(sid, {})
        when = str(year) if year else (s.get("year") or "")
        rows.append(f'<tr><th>{E(place)}</th><td>{E(when)}</td>'
                    f'<td>&ldquo;{E(q_en if en else q_th)}&rdquo;</td>'
                    f'<td class="small">{src_link(sid, lang)}</td></tr>')
    b.append('<div class="scroll"><table><thead><tr>'
             f'<th>{E("Where" if en else "ที่ไหน")}</th><th>{E("When" if en else "เมื่อไร")}</th>'
             f'<th>{E("What it says" if en else "ว่าอย่างไร")}</th>'
             f'<th>{E("Source" if en else "แหล่ง")}</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')
    note = ("*Inference —* the fourth line is usually read as a fact about Thailand. It is a "
            "fact about **central** Thailand: Milne was comparing the Shan to Bangkok, and "
            "Lanna — a tributary kingdom, not a province, until 1899 — is on the other side "
            "of her comparison."
            if en else
            "*อนุมาน —* บรรทัดที่สี่มักถูกอ่านว่าเป็นข้อเท็จจริงเรื่องประเทศไทย แต่เป็นข้อเท็จจริงเรื่อง**ภาคกลาง** "
            "มิลน์เทียบไทใหญ่กับบางกอก ส่วนล้านนาซึ่งเป็นประเทศราช ไม่ใช่มณฑล จนถึงปี 1899 อยู่อีกฝั่งของการเทียบนั้น")
    b.append(f'<div class="note">{prose(note)}</div>')

    legs = BY_ID.get("legs")
    if legs:
        b.append(prose(T(legs, "text.story", lang)))

    b.append(f'<h2>{E("What the corpus says" if en else "คลังเอกสารว่าอย่างไร")}</h2>')
    c = CORPUS.get("corpus") or {}
    terms = {t["th"]: t for t in CORPUS.get("terms", [])}
    b.append(slab([(f"{c.get('pages_transcribed', 0):,}",
                    "transcribed pages" if en else "หน้าที่ถอดความแล้ว"),
                   (f"{c.get('manuscripts', 0):,}", "manuscripts" if en else "เอกสาร"),
                   (terms.get("สักขาลาย", {}).get("pages", 0),
                    "mention สักขาลาย" if en else "หน้าที่มีคำว่าสักขาลาย"),
                   (terms.get("พุงดำ", {}).get("pages", 0),
                    "mention พุงดำ" if en else "หน้าที่มีคำว่าพุงดำ")]))
    trows = [(f'{t["th"]} · {t["rtgs"]}', t["pages"], "mpoke", f'{t["manuscripts"]} mss')
             for t in CORPUS.get("terms", [])]
    b.append(barchart(trows, lang))
    corpus_note = ("Counted in the wichaa.net manuscript corpus, a body of northern and "
                   "central Thai manuscript material transcribed and translated page by page. "
                   "Thai is written without spaces, so short words match inside longer ones "
                   "and every count is an upper bound. **The tradition that covered the legs "
                   "of every man in Lanna appears on one page.** That is a fact about what "
                   "manuscripts are for — recipes, katha, yantra, horoscopes — not evidence "
                   "that the custom was rare. It is also not on this disk in any other form."
                   if en else
                   "นับในคลังเอกสารของ wichaa.net ซึ่งเป็นเอกสารล้านนาและภาคกลางที่ถอดความและแปลทีละหน้า "
                   "ภาษาไทยเขียนติดกัน คำสั้นจึงไปตรงกับคำยาว ทุกตัวเลขเป็นเพดานบน "
                   "**ธรรมเนียมที่คลุมขาชายล้านนาทุกคน ปรากฏอยู่หน้าเดียว** "
                   "นั่นเป็นข้อเท็จจริงว่าเอกสารมีไว้ทำอะไร ไม่ใช่หลักฐานว่าธรรมเนียมนี้หายาก")
    b.append(f'<div class="note">{prose(corpus_note)}</div>')

    b.append(f'<h2>{E("The records" if en else "บันทึกที่เกี่ยวข้อง")}</h2>')
    ids = ["sak-kha-lai", "htoe-kwin", "shan-tattooing", "chin-ming", "sak-yant",
           "hnitkwasok", "lek-char", "khan-tang", "murals", "sample-book", "shway-yoe",
           "milne-shans", "wat-phumin", "kengtung", "lampblack", "vermilion"]
    b.append(grid([BY_ID[i] for i in ids if i in BY_ID], lang))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}legs/",
                       "The leg zone" if en else "เขตลายขา", lang,
                       "Burma, the Shan States and Lanna" if en else "พม่า รัฐฉาน และล้านนา"))
    return "".join(b)


def clothing_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    rec = BY_ID.get("clothing")
    b = [f'<h1>{E("The tattoo is clothing" if en else "รอยสักคือเครื่องนุ่งห่ม")}</h1>']
    if rec:
        b.append(f'<p class="lede">{E(T(rec, "text.what", lang))}</p>')
    rows = []
    for c in CH["clothing"]:
        n = BY_ID.get(c["id"])
        nm = T(n, "names.name", lang) if n else c["name"]
        rows.append(f'<tr><th><a href="{r}{url_of(n)}">{E(nm)}</a></th>'
                    f'<td class="small">{E(c["lang"])}</td>'
                    f'<td>&ldquo;{E(c["quote"])}&rdquo;</td>'
                    f'<td class="small">{src_link(c["source"], lang)}</td></tr>')
    b.append('<div class="scroll"><table><thead><tr>'
             f'<th>{E("Tradition" if en else "ธรรมเนียม")}</th>'
             f'<th>{E("Said in" if en else "ภาษา")}</th>'
             f'<th>{E("The comparison" if en else "คำเปรียบ")}</th>'
             f'<th>{E("Source" if en else "แหล่ง")}</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')
    if rec:
        b.append(prose(T(rec, "text.story", lang)))
    body = BY_ID.get("body")
    if body:
        b.append(f'<h2>{E("And what follows from it" if en else "และสิ่งที่ตามมา")}</h2>')
        b.append(prose(T(body, "text.story", lang)))
        b.append(f'<p><a class="btn" href="{r}body/">'
                 f'{E("Where the marks go" if en else "ลายลงตรงไหน")}</a></p>')
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}clothing/",
                       "The tattoo is clothing" if en else "รอยสักคือเครื่องนุ่งห่ม", lang))
    return "".join(b)


def body_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    zl = ZONE_LABEL[lang]
    b = [f'<h1>{E("Where the marks go" if en else "ลายลงตรงไหน")}</h1>']
    lede = ("Every tradition here records which zones of the body it marks. Counted "
            "together, they sort into skin that clothing covers and skin it does not — and "
            "the bans land almost entirely on the second kind."
            if en else
            "ทุกธรรมเนียมบนเว็บนี้บันทึกไว้ว่าลงลายที่ส่วนใดของร่างกาย เมื่อนับรวมกัน แยกได้เป็นผิวที่เสื้อผ้าปิด "
            "กับผิวที่เสื้อผ้าไม่ปิด และคำสั่งห้ามเกือบทั้งหมดลงที่อย่างหลัง")
    b.append(f'<p class="lede">{E(lede)}</p>')
    b.append(slab([(CH["coverable"], "marks on covered skin" if en else "รอยบนผิวที่ปิดได้"),
                   (CH["open_skin"], "marks on open skin" if en else "รอยบนผิวที่ปิดไม่ได้"),
                   (CH["placed"], "traditions counted" if en else "ธรรมเนียมที่นับ"),
                   (len(CH["banned_on_open_skin"]), "bans, on open skin" if en else "คำสั่งห้ามที่ลงกับผิวเปิด")]))
    cover = [(zl.get(z, z), n, "mtap", "") for z, n in CH["zones"].items()
             if z in CH["coverable_zones"]]
    open_ = [(zl.get(z, z), n, "mpoke", "") for z, n in CH["zones"].items()
             if z in CH["open_zones"]]
    b.append(f'<h2>{E("Skin a longyi, a sarong or a shirt covers" if en else "ผิวที่ผ้าถุง ผ้าซิ่น หรือเสื้อปิดไว้")}</h2>')
    b.append(barchart(cover, lang))
    b.append(f'<h2>{E("Skin nothing covers" if en else "ผิวที่ไม่มีอะไรปิด")}</h2>')
    b.append(barchart(open_, lang))
    banned = [BY_ID[i] for i in CH["banned"] if i in BY_ID]
    if banned:
        b.append(f'<h2>{E("The traditions a government stopped" if en else "ธรรมเนียมที่รัฐสั่งหยุด")}</h2>')
        rows = []
        for n in banned:
            p = n.get("practice") or {}
            zones = ", ".join(zl.get(z, z) for z in (p.get("placement") or []))
            rows.append(f'<tr><th><a href="{r}{url_of(n)}">{E(T(n, "names.name", lang))}</a></th>'
                        f'<td>{E(zones)}</td><td class="small">{E(p.get("suppressed_by", ""))}</td></tr>')
        b.append('<div class="scroll"><table><thead><tr>'
                 f'<th>{E("Tradition" if en else "ธรรมเนียม")}</th>'
                 f'<th>{E("Where the marks go" if en else "ลายอยู่ตรงไหน")}</th>'
                 f'<th>{E("Stopped by" if en else "หยุดเพราะ")}</th></tr></thead>'
                 f'<tbody>{"".join(rows)}</tbody></table></div>')
    rec = BY_ID.get("body")
    if rec:
        b.append(prose(T(rec, "text.story", lang)))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}body/",
                       "Where the marks go" if en else "ลายลงตรงไหน", lang))
    return "".join(b)


def timeline_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    b = [f'<h1>{E("Timeline" if en else "ลำดับเวลา")}</h1>']
    lede = ("Bodies, instruments and paper, on one axis with a break in it. Everything "
            "before year zero is drawn at a different rate, and the break is drawn too."
            if en else
            "ร่างกาย เครื่องมือ และเอกสาร บนแกนเดียวที่มีรอยหัก ทุกอย่างก่อนปีศูนย์ถูกวาดด้วยอัตราส่วนอีกแบบ")
    b.append(f'<p class="lede">{E(lede)}</p>')
    b.append(f'<figure class="map tlwrap">{timeline_svg(CH["timeline"], lang)}</figure>')
    b.append(legend([("Evidence" if en else "หลักฐาน", "tfind"),
                     ("Episodes" if en else "เหตุการณ์", "tstory"),
                     ("Traditions" if en else "ธรรมเนียม", "ttrad")]))
    rec = BY_ID.get("timeline")
    if rec:
        b.append(prose(T(rec, "text.story", lang)))
    b.append(f'<h2>{E("Stopped, and started again" if en else "หยุดไปแล้วกลับมา")}</h2>')
    rows = [(f'{BY_ID[x["id"]]["names"]["name"] if x["id"] in BY_ID else x["name"]}',
             x["gap"], "mstitch", f'{x["from"]}–{x["to"]}') for x in CH["breaks"]]
    b.append(barchart(rows, lang,
                      note=("The years between the last ordinary practice and the revival, "
                            "where both ends are datable. Where a tradition has not come "
                            "back, the second number is this year and the bar is a gap, not "
                            "a recovery." if en else
                            "จำนวนปีระหว่างการปฏิบัติครั้งสุดท้ายกับการรื้อฟื้น เมื่อระบุปีได้ทั้งสองปลาย "
                            "ธรรมเนียมที่ยังไม่กลับมา ตัวเลขที่สองคือปีนี้ และแท่งนั้นคือช่องว่าง ไม่ใช่การฟื้นตัว")))
    rev = BY_ID.get("revival")
    if rev:
        b.append(prose(T(rev, "text.story", lang)))
    b.append(f'<h2>{E("The evidence" if en else "หลักฐาน")}</h2>')
    b.append(grid(by_type("find"), lang))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}timeline/",
                       "Timeline" if en else "ลำดับเวลา", lang))
    return "".join(b)


def words_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    means_label = {"en": {"prick": "It means to prick", "strike": "It means to strike",
                          "write": "It means to write", "pattern": "It means a pattern",
                          "sew": "It means to sew", "other": "Something else"},
                   "th": {"prick": "แปลว่าแทง", "strike": "แปลว่าตอก", "write": "แปลว่าเขียน",
                          "pattern": "แปลว่าลาย", "sew": "แปลว่าเย็บ", "other": "อย่างอื่น"}}[lang]
    b = [f'<h1>{E("The words" if en else "คำ")}</h1>']
    lede = ("What each tradition calls it, and what the word meant first. Four answers, and "
            "they line up with the method rather than with the map."
            if en else
            "แต่ละธรรมเนียมเรียกมันว่าอะไร และคำนั้นแปลว่าอะไรก่อน สี่คำตอบ และเรียงตามวิธี ไม่ใช่ตามแผนที่")
    b.append(f'<p class="lede">{E(lede)}</p>')
    b.append(barchart([(means_label.get(k, k), v, "mpoke" if k == "prick" else
                        "mtap" if k == "strike" else "mstitch" if k == "write" else "mcut", "")
                       for k, v in CH["by_means"].items()], lang))
    for means in ("prick", "strike", "pattern", "write", "sew", "other"):
        grp = [w for w in CH["words"] if w["means"] == means]
        if not grp:
            continue
        b.append(f'<h2>{E(means_label.get(means, means))} <span class="n">{len(grp)}</span></h2>')
        rows = []
        for w in grp:
            n = BY_ID.get(w["id"])
            rows.append(f'<tr><th class="th">{E(w["local"])}</th>'
                        f'<td><a href="{r}{url_of(n)}">{E(w["name"])}</a></td>'
                        f'<td class="small">{E(w["lang"])}</td>'
                        f'<td>{E(w["gloss"])}</td></tr>')
        b.append(f'<div class="scroll"><table><tbody>{"".join(rows)}</tbody></table></div>')
    rec = BY_ID.get("words")
    if rec:
        b.append(prose(T(rec, "text.story", lang)))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}words/",
                       "The words" if en else "คำ", lang))
    return "".join(b)


def coverage_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    b = [f'<h1>{E("Who gets written about" if en else "ใครถูกเขียนถึง")}</h1>']
    lede = ("For each tradition: how many Wikipedia language editions carry an article about "
            "the tattooing itself. A count of attention, not of importance."
            if en else
            "แต่ละธรรมเนียมมีบทความวิกิพีเดียเรื่องการสักนั้นโดยตรงกี่ภาษา นี่คือการนับความสนใจ ไม่ใช่ความสำคัญ")
    b.append(f'<p class="lede">{E(lede)}</p>')
    b.append(slab([(LANGCOV["traditions"], "traditions" if en else "ธรรมเนียม"),
                   (LANGCOV["with_own_article"], "have an article of their own" if en else "มีบทความของตัวเอง"),
                   (LANGCOV["without_own_article"], "are a section in someone else's" if en else "เป็นหัวข้อย่อยในบทความอื่น"),
                   (LANGCOV.get("median") or 0, "median editions" if en else "มัธยฐานของจำนวนภาษา")]))
    own = [x for x in LANGCOV["rows"] if x.get("n")]
    b.append(barchart([(x["name"], x["n"], "mpoke", x["own_article"]) for x in own], lang))
    none = [x for x in LANGCOV["rows"] if not x.get("n")]
    b.append(f'<h2>{E("No article about the tattooing" if en else "ไม่มีบทความเรื่องการสัก")} '
             f'<span class="n">{len(none)}</span></h2>')
    rows = []
    for x in none:
        n = BY_ID.get(x["id"])
        nm = T(n, "names.name", lang) if n else x["name"]
        rows.append(f'<tr><th><a href="{r}{url_of(n)}">{E(nm)}</a></th>'
                    f'<td class="small">{E(x.get("host_article") or "")}</td>'
                    f'<td>{E(x.get("host_n") or "")}</td></tr>')
    b.append('<div class="scroll"><table><thead><tr>'
             f'<th>{E("Tradition" if en else "ธรรมเนียม")}</th>'
             f'<th>{E("It is a section inside" if en else "เป็นหัวข้อย่อยใน")}</th>'
             f'<th>{E("Editions of that" if en else "บทความนั้นมีกี่ภาษา")}</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')
    rec = BY_ID.get("coverage")
    if rec:
        b.append(prose(T(rec, "text.story", lang)))
    b.append(f'<p class="mute small">{E(LANGCOV["note"])} '
             f'{E("Counted" if en else "นับเมื่อ")} {E(LANGCOV["counted"])}.</p>')
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}coverage/",
                       "Who gets written about" if en else "ใครถูกเขียนถึง", lang))
    return "".join(b)


def counted_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    b = [f'<h1>{E("Counted" if en else "ตัวเลข")}</h1>']
    lede = ("Every number on this site, with the thing it was counted from. A figure that "
            "does not appear here is not one this site claims."
            if en else
            "ตัวเลขทุกตัวบนเว็บนี้ พร้อมสิ่งที่นับมา ตัวเลขที่ไม่ปรากฏตรงนี้ไม่ใช่ตัวเลขที่เว็บนี้อ้าง")
    b.append(f'<p class="lede">{E(lede)}</p>')
    c = CORPUS.get("corpus") or {}
    rows = [
        (COV["records"], "records", "the files in data/nodes/", "บันทึก"),
        (CH["traditions"], "traditions", "records of type tradition", "ธรรมเนียม"),
        (COV["kin_edges"], "links between records", "kin entries, counted both ways", "ความเชื่อมโยงระหว่างบันทึก"),
        (COV["sources"], "sources", "data/sources/sources.json", "แหล่งอ้างอิง"),
        (COV["books"], "out-of-copyright books", "fetched whole from the Internet Archive", "หนังสือหมดลิขสิทธิ์"),
        (COV["images"], "pictures", "each with its author and licence", "ภาพ"),
        (COV["th_fields"], "fields written in Thai", "text_th keys across all records", "ช่องที่เขียนเป็นภาษาไทย"),
        (len(CH["countries"]), "countries", "practice.countries, deduplicated", "ประเทศ"),
        (CH["coverable"], "marks on covered skin", "placement zones, summed", "รอยบนผิวที่ปิดได้"),
        (CH["open_skin"], "marks on open skin", "placement zones, summed", "รอยบนผิวที่ปิดไม่ได้"),
        (len(CH["clothing"]), "traditions whose sources call the tattoo clothing",
         "one quote each, printed at /clothing/", "ธรรมเนียมที่แหล่งข้อมูลเรียกรอยสักว่าเครื่องนุ่งห่ม"),
        (len(CH["breaks"]), "datable breaks", "practice.break, both ends", "ช่วงขาดตอนที่ระบุปีได้"),
        (LANGCOV["with_own_article"], "traditions with a Wikipedia article about the tattooing",
         "checked by hand, counted by API", "ธรรมเนียมที่มีบทความวิกิพีเดียเรื่องการสัก"),
        (c.get("pages_transcribed", 0), "transcribed manuscript pages searched",
         "the wichaa.net corpus", "หน้าเอกสารที่ถอดความแล้วและถูกค้น"),
    ]
    trows = "".join(
        f'<tr><td class="num">{v:,}</td><td>{E(lab_en if en else lab_th)}</td>'
        f'<td class="small mute">{E(how)}</td></tr>' for v, lab_en, how, lab_th in rows)
    b.append(f'<div class="scroll"><table><tbody>{trows}</tbody></table></div>')
    b.append(f'<h2>{E("What this site does not have" if en else "สิ่งที่เว็บนี้ไม่มี")}</h2>')
    missing = ("- No price for any tattoo anywhere, and no booking for one.\n"
               "- No count of how many people alive now carry any of these marks. Nobody "
               "publishes one, and the estimates that circulate have no method attached.\n"
               "- No designs to copy. Several traditions here hold that certain marks may "
               "not be worn by people who have not earned them.\n"
               "- No medical advice, no aftercare, no opinion about where anyone should be "
               "tattooed.\n"
               "- No photographs of a tattoo in progress that read as blood.\n"
               "- No Thai translation of every record: the English is shown where the Thai "
               "is missing, and the page says so."
               if en else
               "- ไม่มีราคาของการสักที่ไหนทั้งสิ้น และไม่มีการจอง\n"
               "- ไม่มีตัวเลขว่าคนที่มีชีวิตอยู่ตอนนี้มีรอยเหล่านี้กี่คน ไม่มีใครเผยแพร่ และตัวเลขที่วนอยู่ไม่มีวิธีนับกำกับ\n"
               "- ไม่มีลายให้ลอก หลายธรรมเนียมถือว่าลายบางลายสวมไม่ได้ถ้าไม่ได้มาด้วยการกระทำ\n"
               "- ไม่มีคำแนะนำทางการแพทย์ ไม่มีวิธีดูแลแผล ไม่มีความเห็นว่าใครควรไปสักที่ไหน\n"
               "- ไม่มีภาพการสักระหว่างทำที่อ่านออกมาเป็นเลือด\n"
               "- ไม่ได้แปลทุกบันทึกเป็นภาษาไทย ตรงที่ไม่มีภาษาไทยจะแสดงภาษาอังกฤษและบอกไว้")
    b.append(prose(missing))
    b.append(f'<p class="mute small">{E("Built" if en else "สร้างเมื่อ")} {E(COV["built"])} · '
             f'<a href="{rel()}api/">API</a></p>')
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}counted/",
                       "Counted" if en else "ตัวเลข", lang))
    return "".join(b)


# ---------------------------------------------------------------- record page
def node_page(n: dict, lang: str) -> str:
    ui = UI[lang]
    r = lroot(lang)
    ti = TYPE_INFO[n["type"]]
    name = T(n, "names.name", lang)
    kind = ti["th"] if lang == "th" else ti["one"]
    said = T(n, "names.said", lang)
    url = f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}{url_of(n)}"
    b = [f'<h1><span class="kind">{E(kind)}</span>{E(name)}</h1>']
    nm = n["names"]
    if lang == "en" and nm.get("th"):
        b.append(f'<p class="said th">{E(nm["th"])}'
                 f'{" · " + E(nm["rtgs"]) if nm.get("rtgs") else ""}</p>')
    if nm.get("local") and nm.get("local") != nm.get("th"):
        b.append(f'<p class="said local">{E(nm["local"])}'
                 f'{" · " + E(nm["local_lang"]) if nm.get("local_lang") else ""}</p>')
    if said:
        b.append(f'<p class="said">{E(said)}</p>')
    if n.get("needs_verification"):
        b.append(f'<div class="warn">{E(ui["unverified"])}</div>')
    ims = pictures(n)
    if ims:
        b.append(hero_shot(n))

    pr = n.get("practice") or {}
    if pr:
        cells = []
        if pr.get("method"):
            cells.append((METHOD_LABEL[lang].get(pr["method"], pr["method"]), ui["method"]))
        if pr.get("status"):
            cells.append((STATUS_LABEL[lang].get(pr["status"], pr["status"]), ui["status"]))
        if pr.get("marked"):
            cells.append((pr["marked"], ui["marked"]))
        if pr.get("marks"):
            cells.append((pr["marks"], ui["marks"]))
        b.append(slab(cells))
        rows = []
        if pr.get("placement"):
            zl = ZONE_LABEL[lang]
            rows.append(f'<tr><th>{E(ui["placement"])}</th><td>'
                        f'{E(", ".join(zl.get(z, z) for z in pr["placement"]))}</td></tr>')
        for key, label in (("sessions", ui["sessions"]), ("suppressed_by", ui["ban"]),
                           ("note", ui["notes"])):
            if pr.get(key):
                rows.append(f'<tr><th>{E(label)}</th><td>{E(pr[key])}</td></tr>')
        for key, label in (("tool", ui["tool"]), ("ink", ui["ink"])):
            t = BY_ID.get(pr.get(key) or "")
            if t:
                rows.append(f'<tr><th>{E(label)}</th><td><a href="{r}{url_of(t)}">'
                            f'{E(T(t, "names.name", lang))}</a></td></tr>')
        if pr.get("break"):
            f0, f1 = pr["break"]
            rows.append(f'<tr><th>{E(ui["gap"])}</th><td>{f0}&ndash;{f1} '
                        f'<span class="mute">({f1 - f0})</span></td></tr>')
        if rows:
            b.append(f'<div class="scroll"><table class="kv"><tbody>{"".join(rows)}</tbody></table></div>')

    it = n.get("instrument") or {}
    if it:
        cells = []
        if it.get("length_cm"):
            cells.append((f'{it["length_cm"]:g} cm', "length" if lang == "en" else "ความยาว"))
        if it.get("worked"):
            cells.append((it["worked"], "worked" if lang == "en" else "ใช้อย่างไร"))
        if it.get("hands"):
            cells.append((it["hands"], "hands" if lang == "en" else "ใช้กี่มือ"))
        if cells:
            b.append(slab(cells))
        rows = []
        if it.get("material"):
            rows.append(f'<tr><th>{E("Made of" if lang == "en" else "ทำจาก")}</th>'
                        f'<td>{E(", ".join(it["material"]))}</td></tr>')
        for key, label in (("points", "Points" if lang == "en" else "ปลาย"),
                           ("held_by", "Held" if lang == "en" else "การจับ"),
                           ("length_note", "Length" if lang == "en" else "ความยาว"),
                           ("museum", "In a collection" if lang == "en" else "อยู่ในคอลเลกชัน")):
            if it.get(key):
                rows.append(f'<tr><th>{E(label)}</th><td>{E(it[key])}</td></tr>')
        if rows:
            b.append(f'<div class="scroll"><table class="kv"><tbody>{"".join(rows)}</tbody></table></div>')

    mk = n.get("mark") or {}
    if mk:
        rows = []
        if mk.get("where"):
            rows.append(f'<tr><th>{E(ui["placement"])}</th><td>'
                        f'{E(", ".join(ZONE_LABEL[lang].get(z, z) for z in mk["where"]))}</td></tr>')
        if mk.get("earned"):
            rows.append(f'<tr><th>{E("Earned" if lang == "en" else "ต้องได้มา")}</th>'
                        f'<td>{E(mk.get("earned_how") or ("yes" if lang == "en" else "ใช่"))}</td></tr>')
        if rows:
            b.append(f'<div class="scroll"><table class="kv"><tbody>{"".join(rows)}</tbody></table></div>')

    wh = n.get("when") or {}
    if wh.get("label") or wh.get("from") is not None:
        lab = (wh.get("label_th") if lang == "th" and wh.get("label_th") else wh.get("label", ""))
        span = year_label(wh["from"], lang) if wh.get("from") is not None else ""
        if wh.get("to") and wh.get("to") != wh.get("from"):
            span += " – " + year_label(wh["to"], lang)
        if wh.get("circa"):
            span = ("about " if lang == "en" else "ราว ") + span
        b.append(f'<p class="when"><b>{E(span)}</b>'
                 f'{" · " + E(lab) if lab else ""}</p>')

    if n.get("geo"):
        g = n["geo"]
        b.append(f'<p class="mute mono">{g["lat"]:.4f}, {g["lon"]:.4f} · '
                 f'<a href="https://www.openstreetmap.org/?mlat={g["lat"]}&mlon={g["lon"]}#map=15/'
                 f'{g["lat"]}/{g["lon"]}" rel="noopener">OpenStreetMap</a></p>')

    for key, label in (("what", ui["what"]), ("story", ui["story"]), ("how", ui["how"]),
                       ("today", ui["today"]), ("notes", ui["notes"])):
        txt = T(n, f"text.{key}", lang, fallback=False)
        miss = False
        if txt is None:
            txt = (n.get("text") or {}).get(key)
            miss = lang == "th" and bool(txt)
        if not txt:
            continue
        b.append(f"<h2>{E(label)}</h2>")
        if miss:
            b.append(f'<div class="warn">{E(ui["no_th"])}</div>')
        b.append(prose(txt))

    ety = n.get("etymology") or {}
    if ety.get("root"):
        b.append(f'<h2>{E("Root" if lang == "en" else "รากศัพท์")}</h2>'
                 f'<p class="root">{E(ety["root"])}</p>')
        if ety.get("first_attested"):
            b.append(f'<p class="mute">{E("First attested" if lang == "en" else "หลักฐานแรกสุด")}'
                     f': {E(ety["first_attested"])}</p>')
        if ety.get("note"):
            b.append(f'<p class="mute">{E(ety["note"])}</p>')

    if len(ims) > 1:
        b.append(shot_strip([i for i in ims if not i.get("primary")]))

    kin = [k for k in (n.get("kin") or []) if k["to"] in BY_ID]
    if kin:
        b.append(f'<h2>{E(ui["kin"])}</h2><ul class="kin">')
        for k in kin:
            t = BY_ID[k["to"]]
            b.append(f'<li><a href="{r}{url_of(t)}">{E(T(t, "names.name", lang))}</a> '
                     f'<span class="mute">{E(k["as"])}</span></li>')
        b.append("</ul>")
    kin_in = [k for k in (n.get("kin_in") or []) if k["from"] in BY_ID]
    if kin_in:
        b.append(f'<h2>{E(ui["said_here"])}</h2><ul class="kin">')
        for k in kin_in:
            t = BY_ID[k["from"]]
            b.append(f'<li><a href="{r}{url_of(t)}">{E(T(t, "names.name", lang))}</a> '
                     f'<span class="mute">{E(k["as"])}</span></li>')
        b.append("</ul>")

    if n.get("links"):
        b.append("<ul class=\"kin\">" + "".join(
            f'<li><a href="{E(l["url"])}" rel="noopener">{E(l.get("label") or l["url"])}</a></li>'
            for l in n["links"]) + "</ul>")

    b.append(prov_block(n, lang))
    b.append(f'<p class="mute small"><a href="{rel()}api/{n["type"]}/{n["id"]}.json">'
             f'{E("This record as JSON" if lang == "en" else "บันทึกนี้ในรูป JSON")}</a></p>')
    b.append(share_row(url, name, lang, T(n, "names.said", lang) or ""))
    return "".join(b)


# ---------------------------------------------------------------- type index
def type_index(t: str, lang: str) -> str:
    ti = TYPE_INFO[t]
    en = lang == "en"
    rows = by_type(t)
    b = [f'<h1>{E(ti["th"] if lang == "th" else ti["name"])}</h1>',
         f'<p class="lede">{E(ti["th_blurb"] if lang == "th" else ti["blurb"])}</p>']
    facet = (ti.get("group_by") or "").replace("facets.", "")
    spec = FACETS.get(facet)
    if spec and spec.get("values"):
        groups = {}
        for n in rows:
            v = (n.get("facets") or {}).get(facet) or "_"
            groups.setdefault(v, []).append(n)
        order = list(spec["values"]) + ["_"]
        for v in order:
            if v not in groups:
                continue
            label = spec["values"].get(v, "Everything else" if en else "อื่น ๆ")
            b.append(f'<h2>{E(label)}</h2>')
            b.append(grid(groups[v], lang))
    else:
        b.append(grid(rows, lang))
    b.append(share_row(f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}{DIR_OF[t]}/",
                       ti["th"] if lang == "th" else ti["name"], lang))
    return "".join(b)


def all_page(lang: str) -> str:
    en = lang == "en"
    r = lroot(lang)
    b = [f'<h1>{E("Everything" if en else "ทั้งหมด")}</h1>',
         f'<p class="lede">{COV["records"]} '
         f'{E("records, by type" if en else "บันทึก จัดตามประเภท")}</p>']
    for t in TYPES:
        rows = by_type(t)
        if not rows:
            continue
        ti = TYPE_INFO[t]
        b.append(f'<h2><a href="{r}{DIR_OF[t]}/">{E(ti["th"] if lang == "th" else ti["name"])}</a> '
                 f'<span class="n">{len(rows)}</span></h2><ul class="cols">')
        for n in sorted(rows, key=lambda x: (T(x, "names.name", lang) or "")):
            th = n["names"].get("th")
            thai = f' <span class="th mute">{E(th)}</span>' if th and lang == "en" else ""
            b.append(f'<li><a href="{r}{url_of(n)}">{E(T(n, "names.name", lang))}</a>{thai}</li>')
        b.append("</ul>")
    return "".join(b)


def about(lang: str) -> str:
    en = lang == "en"
    c = CORPUS.get("corpus") or {}
    b = [f'<h1>{E("How this was made" if en else "ทำขึ้นอย่างไร")}</h1>']
    if en:
        b.append(prose(
            f"A static site built from {COV['records']} records in a public repository. Every "
            f"figure printed anywhere on it is computed at build time from those files and "
            f"from three harvests, so a number on a page and a number in the API cannot "
            f"drift apart.\n\n"
            f"**Where the material comes from.** Wikipedia, English and Thai, as a drafting "
            f"corpus. {COV['books']} out-of-copyright books fetched whole from the Internet "
            f"Archive — Shway Yoe on Burma in 1882, Leslie Milne on the Shan in 1910, the "
            f"Gazetteer of Upper Burma, Hose and McDougall on Borneo, Handy on the "
            f"Marquesas. A Lanna volume held in the wichaa.net manuscript corpus, quoted in "
            f"brief with its page. Wikimedia Commons, for {COV['images']} pictures, each "
            f"with its author and licence printed beside it.\n\n"
            f"**Three counts were run for this site.** How many Wikipedia language editions "
            f"carry an article about each tradition's tattooing, rather than about the "
            f"people. How many of {c.get('pages_transcribed', 0):,} transcribed manuscript "
            f"pages mention the leg tattoo, by each word it could be called. And where on "
            f"the body every tradition here puts its marks, sorted into skin that clothing "
            f"covers and skin it does not.\n\n"
            f"**Tiers.** Every claim carries one: *cited* names a source, *harvested* came "
            f"out of an open dataset with its licence, *tradition* is general knowledge of "
            f"the practice and is hedged, *inference* is this project's own reasoning from "
            f"the above, and *field* means someone stood there. The record page for anything "
            f"you doubt has the table at the bottom.\n\n"
            f"**Both languages.** Each page is one build function called twice. Where a "
            f"record has no Thai text the Thai page says so and shows the English rather "
            f"than machine-translating in silence. {COV['th_fields']} fields are written in "
            f"Thai.\n\n"
            f"**The pictures.** No blood, no open wounds, nothing that turns a person into a "
            f"specimen. Where a historical photograph is used it is named for what it is, "
            f"including the ones made to be sold to a European audience.\n\n"
            f"**What it does not have** is listed at /counted/."))
    else:
        b.append(prose(
            f"เว็บสถิตที่สร้างจากบันทึก {COV['records']} ชิ้นในคลังสาธารณะ "
            f"ตัวเลขทุกตัวที่พิมพ์บนเว็บนี้คำนวณตอนสร้างจากไฟล์เหล่านั้นและจากการเก็บข้อมูลสามชุด "
            f"ตัวเลขบนหน้าเว็บกับตัวเลขใน API จึงเคลื่อนออกจากกันไม่ได้\n\n"
            f"**วัสดุมาจากไหน** วิกิพีเดียภาษาอังกฤษและภาษาไทยเป็นคลังร่าง หนังสือหมดลิขสิทธิ์ "
            f"{COV['books']} เล่มที่ดึงมาทั้งเล่มจาก Internet Archive ได้แก่เชวโยเรื่องพม่าปี 1882 "
            f"เลสลี มิลน์เรื่องไทใหญ่ปี 1910 Gazetteer of Upper Burma โฮสกับแมคดูกัลล์เรื่องบอร์เนียว "
            f"และแฮนดีเรื่องหมู่เกาะมาร์เคซัส หนังสือล้านนาหนึ่งเล่มในคลังเอกสารของ wichaa.net "
            f"ยกมาสั้นๆ พร้อมเลขหน้า และวิกิมีเดียคอมมอนส์ ได้ภาพ {COV['images']} ภาพ "
            f"แต่ละภาพพิมพ์ชื่อผู้ถ่ายและสัญญาอนุญาตไว้ข้างๆ\n\n"
            f"**มีการนับสามชุดสำหรับเว็บนี้** วิกิพีเดียกี่ภาษามีบทความเรื่องการสักของแต่ละธรรมเนียม "
            f"ไม่ใช่บทความเรื่องกลุ่มชน · หน้าเอกสารที่ถอดความแล้ว {c.get('pages_transcribed', 0):,} หน้า "
            f"มีกี่หน้าที่เอ่ยถึงลายขา แยกตามคำที่ใช้เรียก · และแต่ละธรรมเนียมลงลายตรงไหนของร่างกาย "
            f"แยกเป็นผิวที่เสื้อผ้าปิดกับผิวที่ไม่ปิด\n\n"
            f"**ชั้นของข้อความ** ทุกข้อความมีชั้นกำกับ *cited* ระบุแหล่ง *harvested* มาจากชุดข้อมูลเปิดพร้อมสัญญาอนุญาต "
            f"*tradition* คือความรู้ทั่วไปของแนวปฏิบัติและมีการกันไว้ *inference* คือการให้เหตุผลของโครงการนี้เอง "
            f"และ *field* คือมีคนไปยืนอยู่ตรงนั้น\n\n"
            f"**สองภาษา** แต่ละหน้าคือฟังก์ชันเดียวที่ถูกเรียกสองครั้ง "
            f"ที่ใดบันทึกไม่มีข้อความภาษาไทย หน้าไทยจะบอกไว้และแสดงภาษาอังกฤษ แทนการแปลด้วยเครื่องเงียบๆ "
            f"มีช่องที่เขียนเป็นภาษาไทย {COV['th_fields']} ช่อง\n\n"
            f"**เรื่องภาพ** ไม่มีเลือด ไม่มีแผลเปิด ไม่มีภาพที่ทำให้คนกลายเป็นตัวอย่างในตู้ "
            f"ภาพประวัติศาสตร์ที่ใช้จะระบุไว้ว่าเป็นภาพแบบใด รวมถึงภาพที่ทำขึ้นเพื่อขายให้คนดูชาวยุโรป\n\n"
            f"**สิ่งที่เว็บนี้ไม่มี** อยู่ที่หน้า /counted/"))
    b.append(f'<p class="mute small">{E("Built" if en else "สร้างเมื่อ")} {E(COV["built"])} · '
             f'<a href="{rel()}api/">API</a> · '
             f'<a href="https://github.com/NaNoBotCo/hand-poke" rel="noopener">GitHub</a> · '
             f'<a href="https://wichaa.net/handpoke/" rel="noopener">wichaa.net</a></p>')
    return "".join(b)


# ---------------------------------------------------------------- machine files
def icon_svg() -> str:
    """A point, a hand's grip, and a line of punctures that reads as a line."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="10" fill="#17110c"/>'
            '<g fill="#e0662b"><circle cx="16" cy="44" r="3"/><circle cx="24" cy="40" r="3"/>'
            '<circle cx="32" cy="36" r="3"/><circle cx="40" cy="32" r="3"/>'
            '<circle cx="48" cy="28" r="3"/></g>'
            '<path d="M14 22 L46 10 L50 18 L18 30 Z" fill="#f0a500"/></svg>')


def manifest() -> str:
    return json.dumps({"name": NAME["en"], "short_name": "Hand Poke",
                       "start_url": BASE_PATH, "display": "standalone",
                       "background_color": "#fdfbf4", "theme_color": "#17110c",
                       "icons": [{"src": f"{BASE_PATH}icon.svg", "sizes": "any",
                                  "type": "image/svg+xml"}]}, ensure_ascii=False, indent=1)


def all_paths() -> list:
    paths = [""] + [p for p, _ in NAV[1:]] + ["all/", "about/"]
    paths += [f"{DIR_OF[t]}/" for t in TYPES if by_type(t)]
    paths += [url_of(n) for n in NODES]
    return sorted(set(paths))


def robots() -> str:
    lines = ["User-agent: *", "Allow: /", "", f"Sitemap: {SITE_URL}/sitemap.xml"]
    lines.append(fleet.robots_lines(SELF, roster=FLEET))
    return "\n".join(lines) + "\n"


def sitemap() -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for p in all_paths():
        for lang in LANGS:
            loc = f"{SITE_URL}/{'th/' if lang == 'th' else ''}{p}"
            alts = "".join(
                f'<xhtml:link rel="alternate" hreflang="{l}" '
                f'href="{SITE_URL}/{"th/" if l == "th" else ""}{p}"/>' for l in LANGS)
            out.append(f"<url><loc>{E(loc)}</loc>{alts}"
                       f"<lastmod>{COV['built'][:10]}</lastmod></url>")
    out.append("</urlset>")
    return "\n".join(out)


def feed() -> str:
    items = sorted(NODES, key=lambda n: n.get("updated", ""), reverse=True)[:40]
    ent = "".join(
        f"<entry><title>{E(n['names']['name'])}</title>"
        f"<link href=\"{SITE_URL}/{url_of(n)}\"/>"
        f"<id>{SITE_URL}/{url_of(n)}</id>"
        f"<updated>{n.get('updated', COV['built'][:10])}T00:00:00Z</updated>"
        f"<summary>{E(clip((n.get('text') or {}).get('what', ''), 300))}</summary></entry>"
        for n in items)
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            f"<title>{E(NAME['en'])}</title><link href=\"{SITE_URL}/\"/>"
            f"<id>{SITE_URL}/</id><updated>{COV['built'][:10]}T00:00:00Z</updated>"
            f"{ent}</feed>")


def llms_txt() -> str:
    c = CORPUS.get("corpus") or {}
    terms = {t["th"]: t for t in CORPUS.get("terms", [])}
    lines = [f"# {NAME['en']}", "", f"> {TAG['en']}", "",
             f"{COV['records']} records, bilingual English and Thai, every claim tiered and "
             f"sourced. Built {COV['built']}. A companion page sits on wichaa.net.", "",
             "## Findings",
             f"- **The tattoo is clothing.** {len(CH['clothing'])} traditions on this site "
             f"have a source that compares the finished work to a garment, in four "
             f"languages across three centuries, plus a Cordilleran rule recorded in "
             f"English: Burmese thigh work as \"a skin-tight pair "
             f"of caleçons\" (1882), Lanna work as \"black trousers\", Visayan work as "
             f"\"a kind of handsome armor\", and untattooed Samoan and Cordilleran men as "
             f"naked, in the ordinary word. Printed with each quote at /clothing/.",
             f"- **The leg-tattoo zone crosses modern Thailand rather than stopping at its "
             f"border.** Burma, the Shan States and Lanna tattooed men from the waist down; "
             f"Milne's 1910 line that \"the Siamese tattoo themselves very slightly, or not "
             f"at all\" is a statement about central Siam, not about Lanna, which was a "
             f"tributary kingdom until 1899. Drawn at /legs/.",
             f"- **{LANGCOV['with_own_article']} of {LANGCOV['traditions']} traditions have a "
             f"Wikipedia article about the tattooing itself**; for the other "
             f"{LANGCOV['without_own_article']} it is a section inside an article about the "
             f"people. Counted in language editions at /coverage/.",
             f"- **In {c.get('pages_transcribed', 0):,} transcribed pages of the wichaa.net "
             f"manuscript corpus, สักขาลาย — the Lanna leg tattoo — appears on "
             f"{terms.get('สักขาลาย', {}).get('pages', 0)}.** Counted at /legs/.",
             f"- **{CH['coverable']} of the marks recorded here go on skin that clothing "
             f"covers and {CH['open_skin']} on skin it does not** — and the bans land almost "
             f"entirely on the second kind. At /body/.",
             "",
             "## Pages"]
    for p, k in NAV:
        lines.append(f"- [{UI['en'][k]}]({SITE_URL}/{p})")
    lines += [f"- [Everything]({SITE_URL}/all/)", f"- [How this was made]({SITE_URL}/about/)",
              f"- [API]({SITE_URL}/api/)", "", "## Data",
              f"- [nodes.json]({SITE_URL}/api/nodes.json) — every record",
              f"- [charts.json]({SITE_URL}/api/charts.json) — every figure the pages print",
              f"- [coverage-langs.json]({SITE_URL}/api/coverage-langs.json) — the language count",
              f"- [corpus.json]({SITE_URL}/api/corpus.json) — the manuscript word counts",
              f"- [nodes.jsonl]({SITE_URL}/nodes.jsonl) · [nodes.csv]({SITE_URL}/nodes.csv)",
              "", "## Licence",
              "Records CC BY 4.0. Wikipedia CC BY-SA 4.0, books out of copyright, pictures "
              "per file with the author beside each one.", ""]
    lines.append(fleet.llms_section(SELF, roster=FLEET))
    return "\n".join(lines) + "\n"


def llms_full() -> str:
    out = [llms_txt(), "", "# Records", ""]
    for n in NODES:
        out.append(f"## {n['names']['name']} ({n['type']}/{n['id']})")
        if n["names"].get("th"):
            out.append(f"Thai: {n['names']['th']}")
        for k, v in (n.get("text") or {}).items():
            out.append(f"### {k}\n{v}")
        out.append(f"Sources: {', '.join(n.get('sources', []))}")
        out.append("")
    return "\n".join(out)


def humans_txt() -> str:
    lines = ["/* TEAM */", "Built by: NaN", "Site: https://wichaa.net",
             "Studio: hongdam.net — Chiang Rai", "",
             "/* THANKS */",
             "OpenStreetMap contributors · Wikidata · Wikipedia (English and Thai) · "
             "Wikimedia Commons photographers · Natural Earth", "",
             "/* SITE */", f"Records: {COV['records']}", f"Built: {COV['built']}",
             "Standards: HTML5, CSS, no framework, no tracker, no web font", ""]
    lines.append(fleet.readme_lines(SELF, roster=FLEET))
    return "\n".join(lines) + "\n"


def ai_txt() -> str:
    return ("# Reuse\n"
            "Records on this site are CC BY 4.0: reuse them with attribution to "
            f"{SITE_URL} .\n"
            "Harvested rows keep their own licences — OpenStreetMap ODbL 1.0, Wikidata CC0, "
            "Wikipedia CC BY-SA 4.0, pictures per file. The machine-readable form is at "
            f"{SITE_URL}/api/ .\n")


def api_index() -> str:
    files = [("nodes.json", "every record, with its kin resolved both ways"),
             ("charts.json", "every figure the pages print, computed once"),
             ("coverage-langs.json", "Wikipedia language editions per tradition"),
             ("corpus.json", "the manuscript corpus word counts"),
             ("sources.json", "every source by id"),
             ("vocab.json", "types, regions, facets, tags"),
             ("coverage.json", "what this build contains")]
    files += [(f"{t}.json", f"records of type {t}") for t in TYPES if by_type(t)]
    rows = "".join(f'<tr><td><a href="{rel()}api/{f}">{f}</a></td><td>{E(d)}</td></tr>'
                   for f, d in files)
    return (f"<h1>API</h1><p class=\"lede\">Plain JSON, same origin, no key. "
            f"Records CC BY 4.0; harvested rows keep their own licences.</p>"
            f'<div class="scroll"><table><tbody>{rows}</tbody></table></div>'
            f'<p><a href="{rel()}nodes.jsonl">nodes.jsonl</a> · '
            f'<a href="{rel()}nodes.csv">nodes.csv</a></p>')


COPY_JS = """document.addEventListener("click",function(e){
var b=e.target.closest("[data-copy]");if(!b)return;
navigator.clipboard.writeText(b.dataset.copy).then(function(){
var s=b.querySelector("span");if(!s)return;var t=s.textContent;s.textContent="Copied";
setTimeout(function(){s.textContent=t},1600)})});
(function(){var h=document.querySelector("header.top");if(!h)return;
var b=document.body,last=window.pageYOffset,hh=h.offsetHeight;
addEventListener("resize",function(){hh=h.offsetHeight},{passive:true});
addEventListener("scroll",function(){var y=window.pageYOffset,d=y-last;
if(y<=hh||d<-4){b.classList.remove("nav-away")}
else if(d>4){b.classList.add("nav-away")}
if(Math.abs(d)>1)last=y},{passive:true});
addEventListener("focusin",function(e){if(h.contains(e.target))
b.classList.remove("nav-away")});})();"""


# ---------------------------------------------------------------- main
def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    if SITE.exists():
        for child in SITE.iterdir():
            if child.name in ("world.svg", "legs.svg"):
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    SITE.mkdir(parents=True, exist_ok=True)

    pages = 0
    for lang in LANGS:
        base = SITE / ("th" if lang == "th" else "")
        ui = UI[lang]
        ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": NAME[lang],
               "url": f"{CANONICAL_URL}/", "inLanguage": lang, "author": AUTHOR,
               "license": DATA_LICENSE},
              fleet.publisher_ld(roster=FLEET),
              {"@context": "https://schema.org", "@type": "WebPage",
               "creator": MAKER, "inLanguage": lang}]
        specials = [
            ("", front, ui["home"], f"{NAME[lang]} — {TAG[lang]}", "home", "index"),
            ("traditions/", traditions_page, ui["traditions"], None, "traditions", "traditions"),
            ("legs/", legs_page, ui["legs"], None, "legs", "legs"),
            ("methods/", methods_page, ui["methods"], None, "methods", "methods"),
            ("map/", map_page, ui["map"], None, "map", "map"),
            ("timeline/", timeline_page, ui["timeline"], None, "timeline", "timeline"),
            ("body/", body_page, ui["body"], None, "body", "body"),
            ("clothing/", clothing_page, ui["clothing"], None, "clothing", "clothing"),
            ("words/", words_page, ui["words"], None, "words", "words"),
            ("coverage/", coverage_page, ui["coverage"], None, "coverage", "coverage"),
            ("counted/", counted_page, ui["counted"], None, "counted", "counted"),
            ("all/", all_page, ui["all"], None, "", "index"),
            ("about/", about, ui["about"], None, "", "index"),
        ]
        for path, fn, label, title, cur, card in specials:
            body = fn(lang)
            t = title or f"{label} — {NAME[lang]}"
            desc = TAG[lang] if path == "" else f"{label} — {NAME[lang]}"
            write(base / path / "index.html",
                  page(t, body, 0 if path == "" else 1, lang, desc=desc, jsonld=ld,
                       cur=cur, path=path, card=card))
            pages += 1
        special_paths = {x[0] for x in specials}
        for t in TYPES:
            # A type whose directory is one of the assembled sections above is reached
            # through that section, which already lists it. Writing the plain index here
            # would overwrite the section with a bare grid.
            if not by_type(t) or f"{DIR_OF[t]}/" in special_paths:
                continue
            ti = TYPE_INFO[t]
            label = ti["th"] if lang == "th" else ti["name"]
            write(base / DIR_OF[t] / "index.html",
                  page(f"{label} — {NAME[lang]}", type_index(t, lang), 1, lang,
                       desc=ti["th_blurb"] if lang == "th" else ti["blurb"],
                       jsonld=ld, path=f"{DIR_OF[t]}/", card=DIR_OF[t]
                       if (SITE / "cards" / f"{DIR_OF[t]}.jpg").exists() else "index"))
            pages += 1
        for n in NODES:
            name = T(n, "names.name", lang)
            desc = clip(T(n, "text.what", lang) or "", 180)
            nld = [{"@context": "https://schema.org", "@type": "Article",
                    "headline": name, "inLanguage": lang,
                    "url": f"{CANONICAL_URL}/{'th/' if lang == 'th' else ''}{url_of(n)}",
                    "author": AUTHOR, "creator": MAKER, "license": DATA_LICENSE,
                    "dateModified": n.get("updated", "")}]
            write(base / url_of(n) / "index.html",
                  page(f"{name} — {NAME[lang]}", node_page(n, lang), 2, lang, desc=desc,
                       jsonld=nld, cur="", path=url_of(n),
                       card=f'{n["type"]}-{n["id"]}'))
            pages += 1

    # machine files, once
    write(SITE / "api" / "index.html",
          page("API — Hand Poke", api_index(), 1, "en", desc="Plain JSON, same origin, no key.",
               path="api/"))
    pages += 1
    shutil.copytree(API, SITE / "api", dirs_exist_ok=True)
    if (ROOT / "data" / "images").exists():
        shutil.copytree(ROOT / "data" / "images", SITE / "images", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("_triage", "*.json"))
    write(SITE / "robots.txt", robots())
    write(SITE / "sitemap.xml", sitemap())
    write(SITE / "feed.xml", feed())
    write(SITE / "icon.svg", icon_svg())
    write(SITE / "manifest.webmanifest", manifest())
    write(SITE / "copy.js", COPY_JS)
    write(SITE / "llms.txt", llms_txt())
    write(SITE / "llms-full.txt", llms_full())
    write(SITE / "humans.txt", humans_txt())
    write(SITE / "ai.txt", ai_txt())
    write(SITE / "nodes.jsonl",
          "\n".join(json.dumps(n, ensure_ascii=False) for n in NODES) + "\n")
    cols = ["id", "type", "name", "th", "region", "confidence", "updated", "sources"]
    rows = [",".join(cols)]
    for n in NODES:
        vals = [n["id"], n["type"], n["names"]["name"], n["names"].get("th", ""),
                " ".join(n.get("region", [])), n.get("confidence", ""), n.get("updated", ""),
                " ".join(n.get("sources", []))]
        rows.append(",".join('"' + str(v).replace('"', '""') + '"' for v in vals))
    write(SITE / "nodes.csv", "\n".join(rows) + "\n")
    fleet.decorate(SITE, SELF, roster=FLEET)
    write(SITE / ".basepath", BASE_PATH)   # what links.py resolves against

    print(f"site: {pages} pages ({pages // 2} per language) into {SITE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
