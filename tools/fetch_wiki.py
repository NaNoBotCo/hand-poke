#!/usr/bin/env python3
"""fetch_wiki.py — the drafting corpus: Wikipedia articles as plain text, one per file.

Pulls the English article and, where it exists, the Thai one, so a bilingual record can
cite both. Each file carries its URL, its revision id and the fetch date at the top.
Wikipedia is CC BY-SA 4.0. The corpus is a working input: .gitignore excludes it and
publish.sh does not copy it into docs/.

    python3 tools/fetch_wiki.py                 # into data/corpus/
    python3 tools/fetch_wiki.py --out /tmp/x    # somewhere else
    python3 tools/fetch_wiki.py --list          # print the article list and stop
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, jdump, slugify  # noqa: E402

UA = "hand-poke-build/0.1 (https://wichaa.net; nan@motdang.net) python-urllib"

EN = """
Tattoo
History of tattooing
Hand-poked tattoo
Tattoo ink
Tattoo machine
Samuel O'Reilly
Sutherland Macdonald
Tā moko
Uhi (tool)
Moko kauae
Tatau
Pe'a
Samoan tattooing
Tatatau
Traditional tattooing in the Philippines
Whang-od
Kalinga people
Bontoc people
Igorot people
Iban people
Kayan people (Borneo)
Dayak people
Mentawai people
Atayal people
Paiwan people
Ainu people
Irezumi
Tebori
Horimono
Yakuza
Inuit
Tattooing in the Arctic
Kakiniit
Chin people
Chin State
Shan people
Shan State
Bamar people
Myanmar
Konbaung dynasty
Lan Na
Chiang Mai
Nan province
Wat Phumin
Tai Yai
Tai Lue
Sak Yant
Yantra tattooing
Wat Bang Phra
Khom Thai script
Tai Tham script
Naga people
Konyak people
Apatani people
Godna
Rabari
Tharu people
Munda people
Li people
Derung people
Drung language
Kurds
Deq (tattoo)
Amazigh
Berbers
Tattooing in Egypt
Coptic Christianity
Razzouk Tattoo
Jerusalem
Sicanje
Bosnian Croats
Ötzi
Pazyryk culture
Siberian Ice Maiden
Chinchorro mummies
Nubia
Ancient Egypt
Hathor
Cucuteni–Trypillia culture
Māori people
Rapa Nui people
Marquesas Islands
Marquesan language
Hawaii
Kākau
Tonga
Fiji
Veiqia
Papua New Guinea
Tattooing in Oceania
Prison tattooing
Russian criminal tattoos
Captain James Cook
Joseph Banks
Omai
Prince Giolo
Jean-Baptiste Cabri
Sideshow
Soot
Lampblack
Indigo dye
Woad
Cinnabar
Vermilion
Charcoal
Bamboo
Bloodborne disease
Sterilization (microbiology)
Christianity and tattooing
Leviticus
Meiji era
Dermis
Skin
Scarification
Blackwork (tattoo)
Cultural appropriation
Intangible cultural heritage
UNESCO Intangible Cultural Heritage Lists
""".strip().splitlines()

TH = """
สักยันต์
รอยสัก
ล้านนา
ไทใหญ่
ไทลื้อ
วัดภูมินทร์
จังหวัดน่าน
อักษรธรรมล้านนา
อักษรขอมไทย
อาณาจักรล้านนา
พม่า
ชาวชิน
จังหวัดเชียงใหม่
""".strip().splitlines()


def fetch(title: str, lang: str) -> dict | None:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    q = {"action": "query", "format": "json", "prop": "extracts|info", "explaintext": 1,
         "redirects": 1, "inprop": "url", "titles": title}
    req = urllib.request.Request(api + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {title}: {e}")
        return None
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p or not p.get("extract"):
            return None
        return {"title": p["title"], "url": p.get("fullurl", ""), "rev": p.get("lastrevid"),
                "lang": lang, "text": p["extract"]}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "corpus"))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("\n".join(EN + TH))
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    index, missing = [], []
    for lang, titles in (("en", EN), ("th", TH)):
        for t in titles:
            t = t.strip()
            if not t:
                continue
            d = fetch(t, lang)
            if not d:
                missing.append(f"{lang}:{t}")
                print(f"  MISSING {lang}:{t}")
                continue
            slug = slugify(d["title"]) or re.sub(r"\W+", "-", d["title"])[:60]
            name = f"{'wp' if lang == 'en' else 'th'}-{slug}.txt"
            (out / name).write_text(
                f"# {d['title']}\n# {d['url']}\n# revision {d['rev']}\n# fetched {today}\n"
                f"# Wikipedia, CC BY-SA 4.0\n\n{d['text']}\n", encoding="utf-8")
            index.append({"id": f"s:{'wp' if lang == 'en' else 'thwp'}-{slug}", "kind": "web",
                          "title": d["title"], "publisher": f"Wikipedia ({lang})", "url": d["url"],
                          "accessed": today, "file": name, "words": len(d["text"].split())})
            print(f"  {name}  {len(d['text'].split())} words")
            time.sleep(0.4)
    jdump({"fetched": today, "licence": "CC BY-SA 4.0", "articles": index, "missing": missing},
          out / "_index.json")
    print(f"\n{len(index)} articles into {out}; {len(missing)} missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
