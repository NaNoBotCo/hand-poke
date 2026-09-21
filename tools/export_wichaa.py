#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""export_wichaa.py — build the site for wichaa.net/handpoke and put it in the wiki's docs.

Run by manuscript-wiki/publishing/publish_site.sh on every publish, and by hand:

    python3 tools/export_wichaa.py --docs ../nanobotco-lanna/docs --site-url https://wichaa.net

Nan's call, 2026-09-21: wichaa is the home. Until then the site was served from
nanobotco.github.io/hand-poke with a one-page companion at wichaa.net/handpoke that
linked to it. The companion could not carry the canonical — it holds 1 page against
311, and a canonical that points at different content is either ignored or obeyed, and
obeyed is worse. So the whole site moves, the GitHub copy becomes redirect stubs
(tools/redirect_stubs.py), and handpoke.py's corpus page keeps its own door at
/handpoke/corpus.

The route is declared in manuscript-wiki/routes.py, so a failure here makes
verify_build refuse the publish rather than ship a door onto nothing. The subtree is
listed in build_static.py's UNMANAGED, so the wiki's own wipe leaves it alone.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "build" / "site"
MOUNT = "handpoke"


def run(script: str, env: dict[str, str], *args: str) -> None:
    r = subprocess.run([sys.executable, str(ROOT / "tools" / script), *args],
                       cwd=ROOT, env=env)
    if r.returncode != 0:
        sys.exit(f"export_wichaa: tools/{script} exited {r.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="the wiki's docs/ directory")
    ap.add_argument("--site-url", default="https://wichaa.net")
    ap.add_argument("--skip-cards", action="store_true",
                    help="leave the share cards as they are (they are drawn with Chrome)")
    a = ap.parse_args()

    docs = Path(a.docs).expanduser().resolve()
    if not docs.is_dir():
        sys.exit(f"export_wichaa: no such docs directory: {docs}")

    site_url = f"{a.site_url.rstrip('/')}/{MOUNT}"
    env = {**os.environ, "PYTHONUTF8": "1", "SITE_URL": site_url,
           "CANONICAL_URL": site_url}

    run("validate.py", env)
    run("build.py", env)
    run("worldmap.py", env)
    run("site.py", env)
    if not a.skip_cards:
        run("cards.py", env)
    run("links.py", env, "--quiet")

    # Nothing that names this machine may be published.
    leak = subprocess.run(["grep", "-rl", "/Users/", str(SITE)],
                          capture_output=True, text=True)
    if leak.stdout.strip():
        sys.exit("export_wichaa: host paths found in build/site — refusing")

    out = docs / MOUNT
    # The corpus page is written by manuscript-wiki/handpoke.py into handpoke/corpus/
    # and is not this repo's to keep or to throw away, so it is carried across the
    # replacement rather than deleted with the rest of the old tree.
    carried = out / "corpus"
    keep = None
    if carried.is_dir():
        keep = docs / "_handpoke-corpus.keep"
        shutil.rmtree(keep, ignore_errors=True)
        shutil.move(str(carried), str(keep))
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(SITE, out)
    if keep is not None:
        shutil.move(str(keep), str(out / "corpus"))

    pages = sum(1 for _ in out.rglob("*.html"))
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"  handpoke → {out}  ({pages} pages, {files} files, canonical {site_url})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
