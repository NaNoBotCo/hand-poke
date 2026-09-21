# Hand Poke

130 records on 28 traditions of marking skin by hand — who is
marked, who does the marking, where on the body, and whether anyone is still doing it.
Bilingual English and Thai, every claim tiered and sourced.

**Live:** https://wichaa.net/handpoke/ — the home since 2026-09-21. The
GitHub Pages copy at `nanobotco.github.io/hand-poke/` is redirect stubs now; a
static host cannot answer 301, so each address carries a canonical, a meta
refresh and a link. The corpus count that used to be the whole of the wichaa
page kept its own door at [/handpoke/corpus/](https://wichaa.net/handpoke/corpus/).

## What is in it

130 records across 14 types, 216 links between
them, 157 sources including 8 out-of-copyright books fetched whole,
146 fields written in Thai, 39 pictures each with its author and
licence.

## The findings

**The tattoo is clothing.** 6 traditions here have a source that compares
the finished work to a garment, in four languages across three centuries — and a
Cordilleran rule recorded in English: Burmese thigh work
as "a skin-tight pair of caleçons" (Shway Yoe, 1882), Lanna work as "black trousers", Visayan
work as "a kind of handsome armor", and untattooed Samoan and Cordilleran men as naked — in
the ordinary word, not as a figure of speech. Every quote is printed with its source at
`/clothing/`.

**The leg-tattoo zone crosses modern Thailand rather than stopping at its border.** Burma,
the Shan States and Lanna tattooed men from the waist down. Leslie Milne's 1910 line that
"the Siamese… tattoo themselves very slightly, or not at all" is a statement about central
Siam; Lanna was a tributary kingdom until 1899 and is on the other side of her comparison.
The zone is drawn at `/legs/` from four written sources and one manuscript, and the map says
that nobody surveyed it.

**13 of 28 traditions have a Wikipedia article about the
tattooing itself.** For the other 15 it is a section inside an
article about the people. Counted in language editions at `/coverage/` — a count of
attention, not of importance.

**In 4,710 transcribed pages of the wichaa.net manuscript
corpus, สักขาลาย — the Lanna leg tattoo — appears on
1.** Counted at `/legs/`, with every word it could be called and
what each count is an upper bound on.

**72 of the marks recorded here go on skin that clothing covers and
40 on skin it does not** — and the bans land almost entirely on the second
kind. At `/body/`.

## Build

```
python3 tools/fetch_wiki.py             # the drafting corpus (gitignored)
python3 tools/fetch_books.py            # the out-of-copyright books (gitignored)
python3 tools/harvest_langlinks.py      # language editions per tradition
python3 tools/harvest_corpus.py         # the manuscript counts, if the corpus is local
python3 tools/harvest_commons.py --harvest --apply    # pictures, with their licences
./publish.sh                            # validate, build, draw, check links, into docs/
python3 tools/serve.py 8817             # a local preview, mounted where the host mounts it
```

## Pictures

No blood, no open wounds, nothing that turns a person into a specimen. Historical
photographs are named for what they are, including the ones made to be sold to a European
audience. `tools/validate.py` errors on a caption that reads as blood unless the record
carries `x_blood_ok`, and the gate is a backstop for looking at the picture.

## Licence

Records and text CC BY 4.0. Wikipedia CC BY-SA 4.0; books scanned by the Internet Archive and
out of copyright; pictures per file with the author beside each one; country outlines from
Natural Earth, public domain. Code MIT. See NOTICE.txt.
