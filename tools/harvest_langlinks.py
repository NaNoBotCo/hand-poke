#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harvest_langlinks.py — how many languages wrote about each tradition, and whether the
tradition has an article at all.

Two different questions, and the second one turned out to be the finding. ARTICLES below
names, for each tradition, the English Wikipedia article that is ABOUT THE TATTOOING —
and where there is none, it says so and names the article the tattooing is a section or a
sentence inside. Counting language editions of "Ainu people" would measure a people, not
a practice, and that is not the thing this site is asking about.

The count is of attention, not of importance, and the page that prints it says so.

Writes data/harvest/langlinks.json.

    python3 tools/harvest_langlinks.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HARVEST, jdump, load_nodes  # noqa: E402

UA = "hand-poke-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"
API = "https://en.wikipedia.org/w/api.php"

# record id -> (article about the tattooing, or None; the host article the tattooing sits
# inside when it has none). Checked by hand against each article, 2026-09-19.
ARTICLES = {
 "sak-kha-lai":        (None, "Lan Na"),
 "htoe-kwin":          ("Tattooing in Myanmar", None),
 "shan-tattooing":     (None, "Shan people"),
 "chin-ming":          (None, "Chin people"),
 "sak-yant":           ("Yantra tattooing", None),
 "batok":              ("Batok", None),
 "kalinga-cordillera": (None, "Kalinga people"),
 "iban-borneo":        (None, "Iban people"),
 "kayan-borneo":       (None, "Kayan people (Borneo)"),
 "mentawai-titi":      (None, "Mentawai people"),
 "atayal-ptasan":      (None, "Atayal people"),
 "ainu-anchi-piri":    (None, "Ainu people"),
 "irezumi":            ("Irezumi", None),
 "hajichi":            (None, "Irezumi"),
 "kakiniit":           ("Kakiniit", None),
 "ta-moko":            ("T\u0101 moko", None),
 "tatau":              ("Pe\u02bba", None),
 "veiqia":             ("Veiqia", None),
 "marquesan-patutiki": (None, "Marquesas Islands"),
 "godna":              ("Godna", None),
 "konyak-naga":        (None, "Konyak Naga"),
 "derung-face":        (None, "Derung people"),
 "hlai-marks":         (None, "Hlai people"),
 "deq":                ("Deq (tattoo)", None),
 "amazigh-marks":      (None, "Berbers"),
 "sicanje":            ("Sicanje", None),
 "coptic-pilgrim":     ("Razzouk Tattoo", None),
 "stick-and-poke":     ("Stick and poke", None),
}



def langlinks(title: str):
    langs, cont = [], None
    for _ in range(12):
        q = {"action": "query", "format": "json", "prop": "langlinks", "lllimit": "500",
             "redirects": 1, "titles": title}
        if cont:
            q["llcontinue"] = cont
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        pages = d.get("query", {}).get("pages", {})
        for p in pages.values():
            if "missing" in p:
                return None
            langs += [ll["lang"] for ll in p.get("langlinks", [])]
        cont = d.get("continue", {}).get("llcontinue")
        if not cont:
            break
    return sorted(set(langs))


def main() -> int:
    rows, unnamed = [], []
    for r in load_nodes():
        if r["type"] != "tradition":
            continue
        if r["id"] not in ARTICLES:
            unnamed.append(r["id"])
            continue
        own, host = ARTICLES[r["id"]]
        row = {"id": r["id"], "name": r["names"]["name"],
               "region": (r.get("region") or [None])[0],
               "own_article": own, "host_article": host, "n": None, "host_n": None}
        for key, title in (("n", own), ("host_n", host)):
            if not title:
                continue
            langs = langlinks(title)
            if langs is None:
                print(f"  ! {r['id']}: {title} missing")
                continue
            row[key] = len(langs) + 1  # the English article itself
            if key == "n":
                row["langs"] = langs
            time.sleep(0.3)
        rows.append(row)
        print(f"  {r['id']:22} own={str(row['n']):>5}  host={str(row['host_n']):>5}  "
              f"{own or '(' + str(host) + ')'}")
    with_own = [r for r in rows if r["n"]]
    rows.sort(key=lambda x: (-(x["n"] or 0), -(x["host_n"] or 0)))
    jdump({"source": "s:langlinks", "counted": time.strftime("%Y-%m-%d"),
           "note": "For each tradition: the number of Wikipedia language editions carrying an "
                   "article ABOUT THE TATTOOING (own_article), and, where there is none, the "
                   "editions carrying the article the tattooing sits inside (host_article). "
                   "A count of attention, not of importance.",
           "traditions": len(rows), "with_own_article": len(with_own),
           "rows": rows, "not_listed": sorted(unnamed)}, HARVEST / "langlinks.json")
    print(f"{len(rows)} traditions · {len(with_own)} have an article about the tattooing itself")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
