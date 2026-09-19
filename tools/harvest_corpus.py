#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harvest_corpus.py — what a corpus of northern Thai manuscripts says about the leg tattoo.

The wichaa.net manuscript corpus holds thousands of pages of transcribed and translated
northern Thai and central Thai manuscript material. This asks it one question: how many of
those pages mention the tattoo, by each of the words a page could use.

Counts only. No page image, no transcription and no translation leaves the corpus through
this tool, and the output is a table of numbers.

The corpus is a local database and is not part of this repository; the counts it produced
are committed as data/harvest/corpus.json so the page can be rebuilt without it.

    python3 tools/harvest_corpus.py            # re-count, if the corpus is on this machine
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HARVEST, PROJECTS, jdump  # noqa: E402

DB = Path(os.environ.get("WICHAA_CORPUS") or (PROJECTS / "manuscript-crawler" / "crawler" / "catalog.db"))

# the word, what it means, and why it is being asked for
TERMS = [
    ("สัก", "sak", "to prick — and also the everyday word for \"about\", so this count is an upper bound"),
    ("สักยันต์", "sak yant", "to tattoo a yantra"),
    ("การสัก", "kan sak", "tattooing, as a noun"),
    ("สักขาลาย", "sak kha lai", "to tattoo the legs in patterns — the Lanna leg tattoo"),
    ("ขาลาย", "kha lai", "patterned legs"),
    ("พุงดำ", "phung dam", "black belly — the outsider's name for the tattooed northerner"),
    ("ลาวพุงดำ", "lao phung dam", "the black-bellied Lao"),
    ("รอยสัก", "roi sak", "a tattoo, as a mark"),
    ("ช่างสัก", "chang sak", "a tattooist"),
    ("เหล็กจาร", "lek chan", "the iron stylus"),
    ("เข็มสัก", "khem sak", "the tattooing needle"),
    ("ขันตั้ง", "khan tang", "the Lanna teacher's fee"),
    ("ชาด", "chat", "vermilion"),
    ("เขม่า", "khamao", "soot"),
]


def main() -> int:
    if not DB.exists():
        print(f"corpus not on this machine ({DB}); leaving data/harvest/corpus.json as it is")
        return 0
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    text = "ifnull(p.transcription,'')||ifnull(p.translation,'')"
    pages = db.execute("select count(*) from pages where ifnull(transcription,'')<>''").fetchone()[0]
    trans = db.execute("select count(*) from pages where ifnull(translation,'')<>''").fetchone()[0]
    mss = db.execute("select count(*) from manuscripts").fetchone()[0]
    rows = []
    for th, rtgs, gloss in TERMS:
        n = db.execute(f"select count(*) from pages p where {text} like ?", (f"%{th}%",)).fetchone()[0]
        m = db.execute(f"select count(distinct p.manuscript_id) from pages p where {text} like ?",
                       (f"%{th}%",)).fetchone()[0]
        where = db.execute(
            f"select p.manuscript_id, p.page_no from pages p where {text} like ? order by p.manuscript_id, p.page_no limit 8",
            (f"%{th}%",)).fetchall()
        rows.append({"th": th, "rtgs": rtgs, "gloss": gloss, "pages": n, "manuscripts": m,
                     "where": [f"{a}:{b}" for a, b in where] if n <= 8 else []})
        print(f"  {th:12} {rtgs:14} pages={n:5} mss={m}")
    titles = {}
    for th, key in (("สัก", "sak"), ("ยันต์", "yant")):
        titles[key] = db.execute(
            "select count(*) from manuscripts where ifnull(title_thai,'')||ifnull(title_english,'')||ifnull(title_translit,'') like ?",
            (f"%{th}%",)).fetchone()[0]
    jdump({"source": "s:corpus", "counted": time.strftime("%Y-%m-%d"),
           "note": "Pages in the wichaa.net manuscript corpus whose transcription or translation "
                   "contains each word. Substring matching: Thai is written without spaces, so a "
                   "short word matches inside longer ones and every count is an upper bound.",
           "corpus": {"manuscripts": mss, "pages_transcribed": pages, "pages_translated": trans,
                      "titles_with_sak": titles.get("sak"), "titles_with_yant": titles.get("yant")},
           "terms": rows}, HARVEST / "corpus.json")
    print(f"{pages} transcribed pages across {mss} manuscripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
