#!/bin/bash
# Build the site, and leave docs/ as redirects to wichaa.net/handpoke.
#
# THE SITE LIVES ON WICHAA — Nan's call, 2026-09-21
# ------------------------------------------------
# It was served from nanobotco.github.io/hand-poke, with a one-page corpus count at
# wichaa.net/handpoke linking to it. Two hosts, and neither could carry the canonical
# honestly: the companion held 1 page against 311, and a canonical pointing at
# different content is either ignored or obeyed, and obeyed loses the site.
#
# So wichaa is the home. tools/export_wichaa.py builds the site and puts it in the
# wiki's docs/ (manuscript-wiki/publishing/publish_site.sh runs it on every publish),
# and this script leaves the GitHub copy as one redirect stub per address, which is
# the most a static host can say. Nothing here is the canonical any more.
#
# To put the site back on this host, build with SITE_URL set and copy build/site into
# docs/ as it used to — and change the canonical on wichaa in the same hour, not later.
set -euo pipefail
cd "$(dirname "$0")"

SITE_URL="https://wichaa.net/handpoke"

export PYTHONUTF8=1

STYLE="$HOME/.claude/bin/stylecheck.py"
if [ -f "$STYLE" ]; then
  # the corpus is Wikipedia text and is not this project's prose, so it is not gated
  python3 "$STYLE" tools data/nodes data/vocab data/sources schema README.md NOTICE.txt || {
    echo "REFUSED: style. See ~/.claude/STYLE.md"; exit 4; }
fi

python3 tools/validate.py
SITE_URL="$SITE_URL" python3 tools/build.py
python3 tools/worldmap.py
SITE_URL="$SITE_URL" python3 tools/site.py
python3 tools/cards.py

# every internal reference, resolved where the host mounts the site — and again from
# the URL without its trailing slash, which is the one people type and the one a host
# may answer with a 200 instead of a redirect
python3 tools/links.py

python3 tools/redirect_stubs.py --to "$SITE_URL"

# nothing that names this machine may be published
if grep -rl "/Users/" docs >/dev/null 2>&1; then
  echo "REFUSED: host paths found in docs/"; exit 2
fi
echo "docs/ redirects to $SITE_URL/ — $(find docs -name '*.html' | wc -l | tr -d ' ') stubs, $(du -sh docs | cut -f1)"
