#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_books.py — the out-of-copyright books this site quotes, as plain text.

Each title is fetched from the Internet Archive by identifier, with its OCR text file, and
written to data/corpus/books/<identifier>.txt with the identifier, the edition year and the
fetch date at the top. The corpus is a working input: .gitignore excludes it.

These are nineteenth- and early twentieth-century observers. Their books are the reason a
practice that stopped is describable at all, and they were written inside a colonial
administration — so a page that quotes one says who was writing, where, and in what year.

    python3 tools/fetch_books.py            # all of them
    python3 tools/fetch_books.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, jdump  # noqa: E402

UA = "hand-poke-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"
OUT = ROOT / "data" / "corpus" / "books"

# identifier, short id, author, title, year — the year of the edition fetched
BOOKS = [
    ("burmanhislifenot00scot", "shway-yoe", "Shway Yoe (Sir James George Scott)",
     "The Burman: His Life and Notions", 1910),
    ("gazetteerupperb06hardgoog", "gazetteer-1", "J. G. Scott and J. P. Hardiman",
     "Gazetteer of Upper Burma and the Shan States", 1900),
    ("gazetteerupperb04hardgoog", "gazetteer-2", "J. G. Scott and J. P. Hardiman",
     "Gazetteer of Upper Burma and the Shan States, Part II", 1900),
    ("shansathomewitht00miln", "milne-shans", "Leslie Milne", "Shans at Home", 1910),
    ("pagantribesofbor01hose", "hose-borneo-1", "Charles Hose and William McDougall",
     "The Pagan Tribes of Borneo, Vol. I", 1912),
    ("pagantribesofbor02hose", "hose-borneo-2", "Charles Hose and William McDougall",
     "The Pagan Tribes of Borneo, Vol. II", 1912),
    ("in.ernet.dli.2015.281437", "gazetteer-3", "J. G. Scott and J. P. Hardiman",
     "Gazetteer of Upper Burma and the Shan States, Part I Vol. I", 1901),
    ("tattooinginmarqu00hand", "handy-marquesas", "Willowdean Chatterson Handy",
     "Tattooing in the Marquesas", 1922),
    ("samoaahundredye00turngoog", "turner-samoa", "George Turner", "Samoa, a Hundred Years Ago", 1884),
]


def get(url: str, timeout=120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def files_of(identifier: str) -> list[dict]:
    d = json.loads(get(f"https://archive.org/metadata/{identifier}").decode("utf-8", "replace"))
    return d.get("files", []), d.get("metadata", {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for b in BOOKS:
            print("\t".join(str(x) for x in b))
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    index = []
    for ident, short, author, title, year in BOOKS:
        try:
            files, meta = files_of(ident)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {ident}: {e}")
            continue
        txt = [f for f in files if f["name"].endswith("_djvu.txt")] or \
              [f for f in files if f["name"].endswith(".txt") and "meta" not in f["name"]]
        if not txt:
            print(f"  ! {ident}: no text file")
            continue
        name = txt[0]["name"]
        try:
            raw = get(f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {ident}: {e}")
            continue
        body = raw.decode("utf-8", "replace")
        p = OUT / f"{short}.txt"
        p.write_text(f"# {title}\n# {author}, {year}\n# https://archive.org/details/{ident}\n"
                     f"# file {name}\n# fetched {today}\n# out of copyright; scanned by the Internet Archive\n\n{body}\n",
                     encoding="utf-8")
        index.append({"id": f"s:{short}", "kind": "book", "title": title, "author": author,
                      "year": year, "url": f"https://archive.org/details/{ident}",
                      "file": p.name, "words": len(body.split()), "accessed": today})
        print(f"  {p.name}  {len(body.split()):,} words")
        time.sleep(1)
    jdump({"fetched": today, "books": index}, OUT / "_index.json")
    print(f"{len(index)} books into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
