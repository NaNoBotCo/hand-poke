#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py — records + harvests → build/api.

Everything the site prints is computed here and written as JSON, so the API a reader or a
bot can fetch is the same data the pages are made from. Each figure is computed once, and
the pages read it rather than restating it.

    python3 tools/build.py
"""
from __future__ import annotations

import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BUILD, TYPES, jdump, load_harvest, load_nodes,  # noqa: E402
                    load_sources, load_vocab)

API = BUILD / "api"

# Zones a longyi, a sarong or a shirt covers, and zones nothing covers. The split is this
# project's, it is the argument the body chart makes, and it is printed as a table so a
# reader can move a row.
COVERABLE = {"chest", "back", "belly", "thighs", "legs", "knees", "waist-to-knee",
             "waist-to-ankle", "buttocks", "whole-body", "arms", "feet"}
OPEN_SKIN = {"face", "chin", "neck", "hands", "fingers", "mouth", "forehead", "tongue"}


def charts(recs: list) -> dict:
    trad = [r for r in recs if r["type"] == "tradition"]
    p = {r["id"]: (r.get("practice") or {}) for r in trad}
    name = {r["id"]: r["names"]["name"] for r in recs}

    by_method = Counter(p[r["id"]].get("method") for r in trad if p[r["id"]].get("method"))
    by_status = Counter(p[r["id"]].get("status") for r in trad if p[r["id"]].get("status"))
    marked = Counter(p[r["id"]].get("marked") for r in trad if p[r["id"]].get("marked"))
    marks = Counter(p[r["id"]].get("marks") for r in trad if p[r["id"]].get("marks"))

    zones = Counter()
    zone_trads = defaultdict(list)
    placed = 0
    for r in trad:
        zs = p[r["id"]].get("placement") or []
        if zs:
            placed += 1
        for z in zs:
            zones[z] += 1
            zone_trads[z].append(r["id"])
    cover = sum(n for z, n in zones.items() if z in COVERABLE)
    open_ = sum(n for z, n in zones.items() if z in OPEN_SKIN)

    # a ban, where a record names one, against where the marks go
    banned = [r["id"] for r in trad if (p[r["id"]].get("suppressed_by") or "").lower().find("ban") >= 0
              or "prohibit" in (p[r["id"]].get("suppressed_by") or "").lower()]
    banned_open = [i for i in banned if set(p[i].get("placement") or []) & OPEN_SKIN]

    breaks = []
    for r in trad:
        b = p[r["id"]].get("break")
        if b and len(b) == 2:
            breaks.append({"id": r["id"], "name": r["names"]["name"], "from": b[0], "to": b[1],
                           "gap": b[1] - b[0], "revived": p[r["id"]].get("revived"),
                           "status": p[r["id"]].get("status")})
    breaks.sort(key=lambda x: -x["gap"])

    countries = Counter()
    for r in trad:
        for c in p[r["id"]].get("countries") or []:
            countries[c] += 1

    clothing = [{"id": r["id"], "name": r["names"]["name"], **r["x_clothing"]}
                for r in recs if r.get("x_clothing")]
    clothing.sort(key=lambda x: x["year"])

    # the timeline: every record that carries a `when`
    tl = []
    for r in recs:
        w = r.get("when")
        if not w or "from" not in w:
            continue
        tl.append({"id": r["id"], "type": r["type"], "name": r["names"]["name"],
                   "from": w["from"], "to": w.get("to", w["from"]), "circa": w.get("circa", False),
                   "label": w.get("label", ""), "label_th": w.get("label_th", "")})
    tl.sort(key=lambda x: x["from"])

    words = []
    for r in recs:
        if r["type"] != "term":
            continue
        words.append({"id": r["id"], "name": r["names"]["name"],
                      "local": r["names"].get("local", ""), "lang": r["names"].get("local_lang", ""),
                      "means": (r.get("facets") or {}).get("means", "other"),
                      "gloss": (r.get("etymology") or {}).get("root", ""),
                      "region": (r.get("region") or [""])[0]})
    by_means = Counter(w["means"] for w in words)

    return {
        "traditions": len(trad),
        "by_method": dict(by_method.most_common()),
        "by_status": dict(by_status.most_common()),
        "marked": dict(marked.most_common()), "marks": dict(marks.most_common()),
        "zones": dict(zones.most_common()), "zone_traditions": dict(zone_trads),
        "placed": placed, "coverable": cover, "open_skin": open_,
        "coverable_zones": sorted(COVERABLE), "open_zones": sorted(OPEN_SKIN),
        "banned": banned, "banned_on_open_skin": banned_open,
        "breaks": breaks,
        "countries": dict(countries.most_common()),
        "clothing": clothing,
        "timeline": tl,
        "words": words, "by_means": dict(by_means.most_common()),
        "names": name,
    }


def coverage_rows(h: dict, recs: list) -> dict:
    """The language-edition count, joined back to the records."""
    if not h:
        return {}
    name = {r["id"]: r["names"]["name"] for r in recs}
    rows = [dict(r, name=name.get(r["id"], r["name"])) for r in h["rows"]]
    own = [r for r in rows if r.get("n")]
    none = [r for r in rows if not r.get("n")]
    return {"counted": h["counted"], "note": h["note"], "rows": rows,
            "traditions": len(rows), "with_own_article": len(own),
            "without_own_article": len(none),
            "most": own[0] if own else None, "fewest": own[-1] if own else None,
            "median": sorted(r["n"] for r in own)[len(own) // 2] if own else None}


def main() -> int:
    recs = load_nodes()
    sources = load_sources()
    vocab = {n: load_vocab(n) for n in ("types", "regions", "facets", "tags")}
    for r in recs:
        r.pop("_path", None)
        r.pop("_dir_type", None)

    back = {}
    for r in recs:
        for k in r.get("kin", []):
            back.setdefault(k["to"], []).append({"from": r["id"], "type": r["type"],
                                                 "name": r["names"]["name"], "as": k["as"]})
    for r in recs:
        r["kin_in"] = back.get(r["id"], [])

    ch = charts(recs)
    cov_lang = coverage_rows(load_harvest("langlinks"), recs)
    corpus = load_harvest("corpus") or {}

    cov = {
        "built": time.strftime("%Y-%m-%d %H:%M"),
        "records": len(recs),
        "by_type": {t: sum(1 for r in recs if r["type"] == t) for t in TYPES},
        "kin_edges": sum(len(r.get("kin", [])) for r in recs),
        "sources": len(sources),
        "books": sum(1 for s in sources.values() if s.get("kind") == "book"),
        "needs_verification": sum(1 for r in recs if r.get("needs_verification")),
        "bilingual": sum(1 for r in recs if r.get("text_th")),
        "th_fields": sum(len(r.get("text_th") or {}) for r in recs),
        "images": sum(len(r.get("images") or []) for r in recs),
        "records_with_images": sum(1 for r in recs if r.get("images")),
        "traditions": ch["traditions"],
        "countries": len(ch["countries"]),
        "clothing": len(ch["clothing"]),
        "with_own_article": cov_lang.get("with_own_article"),
        "corpus_pages": (corpus.get("corpus") or {}).get("pages_transcribed"),
        "tiers": {},
    }
    for r in recs:
        t = (r.get("provenance", {}).get("default") or {}).get("tier", "?")
        cov["tiers"][t] = cov["tiers"].get(t, 0) + 1

    API.mkdir(parents=True, exist_ok=True)
    jdump({"count": len(recs), "nodes": recs}, API / "nodes.json")
    jdump(ch, API / "charts.json")
    jdump(cov_lang, API / "coverage-langs.json")
    jdump(corpus, API / "corpus.json")
    jdump({"sources": list(sources.values())}, API / "sources.json")
    jdump(vocab, API / "vocab.json")
    jdump(cov, API / "coverage.json")
    for t in TYPES:
        rows = [r for r in recs if r["type"] == t]
        jdump({"type": t, "count": len(rows), "nodes": rows}, API / f"{t}.json")
        for r in rows:
            jdump(r, API / t / f"{r['id']}.json")

    print(f"build: {len(recs)} records · {cov['kin_edges']} kin · {len(sources)} sources · "
          f"{cov['th_fields']} Thai fields · {cov['images']} images")
    print(f"       {ch['traditions']} traditions · methods {ch['by_method']}")
    print(f"       status {ch['by_status']}")
    print(f"       placement: {ch['coverable']} marks on skin clothing covers, "
          f"{ch['open_skin']} on skin it does not, from {ch['placed']} traditions")
    print(f"       clothing comparison in {len(ch['clothing'])} traditions · "
          f"{len(ch['breaks'])} datable breaks")
    print(f"       coverage: {cov_lang.get('with_own_article')} of {cov_lang.get('traditions')} "
          f"have an article about the tattooing")
    print(f"       tiers: {cov['tiers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
