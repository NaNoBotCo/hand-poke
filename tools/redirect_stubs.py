#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redirect_stubs.py — turn docs/ into redirects to wichaa.net/handpoke.

    python3 tools/redirect_stubs.py
    python3 tools/redirect_stubs.py --to https://wichaa.net/handpoke

Nan's call, 2026-09-21: the site's home is wichaa. GitHub Pages serves static files
and cannot answer 301, so each of the 311 pages becomes a stub carrying the three
signals a static host can send — rel=canonical at the new address, an instant
meta refresh, and a link a reader can press when the refresh is blocked.

A sitemap of the OLD addresses is written alongside them on purpose. It is the one
thing that asks Google to come back and look at a page it already has, which is how
a redirect gets seen at all; it comes out once the new addresses are indexed.
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "build" / "site"
DOCS = ROOT / "docs"
OLD = "https://nanobotco.github.io/hand-poke"

PAGE = """<!doctype html>
<html lang="{lang}" translate="no" class="notranslate">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moved to wichaa.net</title>
<link rel="canonical" href="{new}">
<meta http-equiv="refresh" content="0; url={new}">
<meta name="referrer" content="no-referrer-when-downgrade">
{cardmeta}<meta name="google" content="notranslate">
<meta name="robots" content="notranslate">
<script>if(/[.]translate[.]goog$/.test(location.hostname))location.replace("https://"+location.hostname.slice(0,-15).replace(/--/g,"~").replace(/-/g,".").replace(/~/g,"-")+location.pathname+location.search.replace(/([?&])_x_tr_[^&]*/g,"$1").replace(/[?&]+$/,"").replace(/[?]&+/,"?")+location.hash)</script>
<style>
  body{{font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;
       margin:0;display:grid;place-items:center;min-height:100vh;
       background:#12100e;color:#e8e2d9;padding:2rem}}
  main{{max-width:34rem;text-align:center}}
  a{{color:#d8a657}}
</style>
<main>
  <h1>Hand Poke has moved</h1>
  <p>This page now lives at <a href="{new}">{shown}</a>.</p>
</main>
</html>
"""


CARD_KEYS = ("og:title", "og:description", "og:type", "og:site_name", "og:locale",
             "og:image", "og:image:secure_url", "og:image:type", "og:image:width",
             "og:image:height", "og:image:alt", "twitter:card", "twitter:image")
META = re.compile(r'<meta (?:property|name)="([^"]+)" content="([^"]*)">')


def card_meta(built: Path, new: str) -> str:
    """The link-card tags of the built page, with the address pointing at its new home,
    so a feed that reads the stub shows the same card as the page it moved to."""
    found = {}
    for k, v in META.findall(built.read_text(encoding="utf-8")):
        if k in CARD_KEYS and k not in found:
            found[k] = v
    if "og:image" not in found:
        return ""
    found["og:url"] = html.escape(new, quote=True)
    order = ("og:title", "og:description", "og:type", "og:url", "og:site_name",
             "og:locale", "twitter:card", "og:image", "og:image:secure_url",
             "og:image:type", "og:image:width", "og:image:height", "og:image:alt",
             "twitter:image")
    return "".join(f'<meta property="{k}" content="{found[k]}">\n' if k.startswith("og:")
                   else f'<meta name="{k}" content="{found[k]}">\n'
                   for k in order if k in found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default="https://wichaa.net/handpoke")
    a = ap.parse_args()
    new_base = a.to.rstrip("/")

    if not SITE.is_dir():
        raise SystemExit("redirect_stubs: build/site is missing — build first")

    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        raise SystemExit("redirect_stubs: build/site holds no pages — refusing")

    shutil.rmtree(DOCS, ignore_errors=True)
    DOCS.mkdir(parents=True)
    (DOCS / ".nojekyll").touch()

    locs = []
    for p in pages:
        rel = p.relative_to(SITE)
        out = DOCS / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        # index.html is the directory; every other page keeps its own name.
        path = rel.parent.as_posix() + "/" if rel.name == "index.html" else rel.as_posix()
        path = "" if path == "./" else path
        new = f"{new_base}/{path}"
        out.write_text(PAGE.format(new=html.escape(new, quote=True),
                                   shown=html.escape(new.replace("https://", "")),
                                   cardmeta=card_meta(p, new),
                                   lang="th" if rel.as_posix().startswith("th/") else "en"),
                       encoding="utf-8")
        locs.append(f"{OLD}/{path}")

    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{html.escape(u)}</loc></url>\n" for u in locs)
        + "</urlset>\n", encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        f"# every page here redirects to {new_base}/\n"
        f"Sitemap: {OLD}/sitemap.xml\n", encoding="utf-8")

    print(f"docs/ → {len(locs)} redirect stubs to {new_base}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
