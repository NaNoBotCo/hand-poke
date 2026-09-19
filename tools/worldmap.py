#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worldmap.py — two maps, drawn as plain SVG from the records and from Natural Earth.

  world.svg  Equal Earth, one dot per tradition, coloured by the method its hands use,
             with a country shaded when a tradition on this site is recorded there.
             Equal Earth because the subject is how many of a thing are where, and an
             equal-area projection is the only kind that does not lie about that.
  legs.svg   the leg-tattoo zone: Upper Burma, the Shan States and Lanna, drawn as one
             outline across three modern countries, with the Thai border under it. The
             outline is this project's reading of four written sources and one manuscript.
             Nobody surveyed it; nobody counted tattooed men anywhere.

Written into build/site/ and also inlined into the pages, so the colours follow the
stylesheet on a page and stand alone in the file.

    python3 tools/worldmap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD, GEO, jload  # noqa: E402
from geo import equal_earth  # noqa: E402

SITE = BUILD / "site"

# An <img> pointing at an SVG is an isolated document: a CSS variable defined on the page
# resolves to the fallback here. The stylesheet below is therefore self-contained, dark
# mode included, and asks the viewer's own preference rather than the page's.
STYLE = (
    "<style>"
    ".sea{fill:#f7f2e6}.c{fill:#ece3d0;stroke:#d8cbb0;stroke-width:.5}"
    ".on{fill:#e8d4b4}.zone{fill:#b4472a;fill-opacity:.22;stroke:#b4472a;stroke-width:1.6;stroke-dasharray:6 4}"
    ".bord{fill:none;stroke:#6b5a43;stroke-width:1.1;stroke-opacity:.85}"
    ".th{fill:none;stroke:#1d4e5f;stroke-width:1.8}"
    ".poke{fill:#b4472a}.tap{fill:#1d6a5f}.stitch{fill:#5b3a86}.cut{fill:#b8860b}.mixed{fill:#6b5a43}"
    ".dot{stroke:#fffdf7;stroke-width:1}"
    ".lbl{font:600 12px/1.2 system-ui,sans-serif;fill:#3a2f22}"
    ".lbl2{font:500 11px/1.2 system-ui,sans-serif;fill:#6b5a43}"
    "@media (prefers-color-scheme:dark){"
    ".sea{fill:#191510}.c{fill:#2c261d;stroke:#453b2c}.on{fill:#4a3a26}"
    ".zone{fill:#e08a5a;fill-opacity:.2;stroke:#e08a5a}"
    ".bord{stroke:#8d7a5c}.th{stroke:#7fc4d8}"
    ".poke{fill:#e08a5a}.tap{fill:#57bfa9}.stitch{fill:#b49ae0}.cut{fill:#e8c35a}.mixed{fill:#a2917a}"
    ".dot{stroke:#12100d}"
    ".lbl{fill:#efe6d5}.lbl2{fill:#b5a досить}}"
    "</style>")
STYLE = STYLE.replace("#b5a досить", "#b5a58c")


def keep(ring, min_span=0.6):
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (max(lons) - min(lons)) > min_span or (max(lats) - min(lats)) > min_span


def simplify(ring, tol=0.7):
    out = [ring[0]]
    for pt in ring[1:]:
        if abs(pt[0] - out[-1][0]) > tol or abs(pt[1] - out[-1][1]) > tol:
            out.append(pt)
    if len(out) < 3:
        return ring[::max(1, len(ring) // 8)]
    return out


def world_svg(rows: list, countries: dict, w=1100) -> str:
    """rows: [{id,name,lat,lon,method}] — one per tradition. countries: {iso: n}."""
    g = jload(GEO / "countries.json")
    pts = [equal_earth(lon, lat) for lon in (-180, 180) for lat in (-90, 90)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    h = int(w * (y1 - y0) / (x1 - x0))

    def P(lon, lat):
        x, y = equal_earth(lon, lat)
        return ((x - x0) / (x1 - x0) * w, h - (y - y0) / (y1 - y0) * h)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="Traditions of tattooing by hand, one dot each, on an Equal Earth projection">',
           STYLE, f'<rect class="sea" width="{w}" height="{h}"/>']
    for c in g["countries"]:
        on = "on" if countries.get(c["iso"]) else ""
        for ring in c["rings"]:
            if len(ring) < 4 or not keep(ring):
                continue
            ring = simplify(ring)
            d = "M" + "L".join(f"{P(p[0], p[1])[0]:.0f} {P(p[0], p[1])[1]:.0f}" for p in ring) + "Z"
            out.append(f'<path class="c {on}" d="{d}"/>')
    for r in sorted(rows, key=lambda r: r["lat"]):
        x, y = P(r["lon"], r["lat"])
        out.append(f'<circle class="dot {r["method"]}" cx="{x:.1f}" cy="{y:.1f}" r="5.5">'
                   f'<title>{r["name"]} — {r["method"]}</title></circle>')
    out.append("</svg>")
    return "".join(out)


# The zone, as this project reads it: Upper Burma, the Shan States, the Tai Khuen and Tai
# Lue towns, and Lanna. Hand-drawn from the sources, not surveyed, and the page says so.
ZONE = [(94.3, 22.6), (95.2, 24.6), (97.4, 25.6), (99.6, 25.4), (101.4, 23.4), (101.6, 21.2),
        (100.7, 19.1), (99.8, 17.6), (98.6, 16.4), (96.2, 17.4), (94.6, 20.0)]

MARKS = [(96.09, 21.96, "Mandalay", "waist to below the knee, every up-country man — 1882"),
         (99.60, 21.29, "Kengtung", "Tai Khuen, inside the zone"),
         (97.40, 23.10, "Namkham", "a boy is a child until he is tattooed — 1910"),
         (98.99, 18.79, "Chiang Mai", "black trousers, in the murals"),
         (100.77, 18.77, "Nan", "Wat Phumin"),
         (100.50, 13.75, "Bangkok", "\"very slightly, or not at all\" — 1910")]


def legs_svg(w=780) -> str:
    g = jload(GEO / "countries.json")
    box = (10.0, 92.0, 28.5, 106.5)          # S, W, N, E
    h = int(w * (box[2] - box[0]) / ((box[3] - box[1]) * 0.94))

    def P(lon, lat):
        return ((lon - box[1]) / (box[3] - box[1]) * w,
                h - (lat - box[0]) / (box[2] - box[0]) * h)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="The leg-tattoo zone across Upper Burma, the Shan States and Lanna, '
           f'with the modern Thai border under it">',
           STYLE, f'<rect class="sea" width="{w}" height="{h}"/>']
    for c in g["countries"]:
        for ring in c["rings"]:
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            if max(lons) < box[1] or min(lons) > box[3] or max(lats) < box[0] or min(lats) > box[2]:
                continue
            ring = simplify(ring, 0.04)
            d = "M" + "L".join(f"{P(p[0], p[1])[0]:.0f} {P(p[0], p[1])[1]:.0f}" for p in ring) + "Z"
            out.append(f'<path class="c" d="{d}"/>')
            if c["iso"] == "TH":
                out.append(f'<path class="th" d="{d}"/>')
            else:
                out.append(f'<path class="bord" d="{d}"/>')
    zd = "M" + "L".join(f"{P(*p)[0]:.0f} {P(*p)[1]:.0f}" for p in ZONE) + "Z"
    out.append(f'<path class="zone" d="{zd}"><title>The leg-tattoo zone, as this site reads '
               f'the sources</title></path>')
    for lon, lat, name, note in MARKS:
        x, y = P(lon, lat)
        out.append(f'<circle class="dot poke" cx="{x:.1f}" cy="{y:.1f}" r="4.5"/>'
                   f'<text class="lbl" x="{x + 8:.0f}" y="{y + 4:.0f}">{name}</text>'
                   f'<text class="lbl2" x="{x + 8:.0f}" y="{y + 18:.0f}">{note}</text>')
    out.append("</svg>")
    return "".join(out)


def main() -> int:
    api = BUILD / "api"
    nodes = jload(api / "nodes.json")["nodes"]
    ch = jload(api / "charts.json")
    rows = [{"id": n["id"], "name": n["names"]["name"], "lat": n["geo"]["lat"],
             "lon": n["geo"]["lon"], "method": (n.get("practice") or {}).get("method", "mixed")}
            for n in nodes if n["type"] == "tradition" and n.get("geo")]
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "world.svg").write_text(world_svg(rows, ch["countries"]), encoding="utf-8")
    (SITE / "legs.svg").write_text(legs_svg(), encoding="utf-8")
    print(f"maps: world.svg {(SITE / 'world.svg').stat().st_size // 1024} KB, {len(rows)} dots · "
          f"legs.svg {(SITE / 'legs.svg').stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
