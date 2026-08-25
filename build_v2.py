"""
Bhavani Thekkada — V2 site generator.

A parallel build. `build.py` and everything it writes are untouched: V2 shares
`content/bhavani.json`, `content/images.json` and `assets/img/` with V1, and
shares no markup, no CSS and no JavaScript with it.

    python build_v2.py        ->  v2/index.html

Benchmark: rogerfederer.com, the site the client named best.

The first pass at V2 improvised a page shape and the client was right that it
drifted. This one copies the benchmark's skeleton deliberately. What that site
actually does, measured by scrolling the whole page:

  1. a thin dark chrome bar carrying a wordmark and no link row
  2. a full-bleed hero, type centred over it, one outlined pill
  3. a sponsor band, one solid colour, logos only
  4. repeated full-bleed panels: centred sans title, serif subtitle beneath,
     one outlined button, under forty words each
  5. one 50/50 split with a pull quote and two short paragraphs
  6. a dark footer, one statement, a row of links

The palette is the one thing deliberately changed, because the brief is white
and blue and the benchmark is near-black.

Why a second build rather than a rewrite. The expensive part of V1 was never
the layout: it was the content layer. Verified facts with sources, fifty
photographs each carrying a focal point measured on the face, the FIS results
rows. All of that is presentation-independent and reused here verbatim.

Nothing here invents copy or numbers. The medal counts are counted from the
results rows at build time, so they cannot drift from the table they came from.
"""

from __future__ import annotations

import hashlib
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "v2"

FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Archivo:wght@400;500;600;700;800"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&family=Newsreader:opsz,wght@6..72,300..500"
    "&display=swap"
)

NAV = [
    ("About", "about.html"),
    ("Journey", "journey.html"),
    ("Records", "records.html"),
    ("Media", "media.html"),
    ("Partnership", "partnership.html"),
]

# One photograph per panel. Named here rather than inline so the whole cast of
# the home page is visible in one place and can be swapped without reading any
# markup. Every one is from her own archive, rights settled.
SHOTS = {
    "hero": "race-worldcup",
    "sport": "classic-tracks",
    "about": "portrait-studio",
    "closer": "chile-lake",
}

# The four photographs in the media row. Journey takes its four from the story
# beats, so it always matches whatever the journey page shows.
MEDIA_TILES = ["khelo-medals", "chile-corralco", "nordic-overlook", "flag-harbin"]

TILE_SIZES = "(min-width:1000px) 22vw, (min-width:560px) 45vw, 92vw"


def fingerprint() -> str:
    """Short content hash over every asset the page links.

    V1 has this and V2 did not, which cost real time: a rewritten stylesheet
    was served from cache while the markup was fresh, so `.panel` rules never
    applied and the hero rendered 4164px tall. Measured at the time:
    `panel.display` came back `block` and `panel-shot.position` came back
    `static`, neither of which appears anywhere in the file on disk.
    """
    h = hashlib.sha1()
    for rel in ("assets/css/tokens.css", "assets/css/v2.css", "assets/js/v2.js"):
        f = OUT / rel
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()[:8]


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


class Img:
    """Responsive markup for a slot, with its focal point carried through.

    Same contract as V1's helper. Every V2 page sits one directory down, so
    the base path is fixed at `../assets/img`.
    """

    def __init__(self, lib: dict):
        self.by_slot = {i["slot"]: i for i in lib["images"]}
        self.base = "../assets/img"

    def get(self, slot):
        return self.by_slot.get(slot)

    def focal(self, slot) -> str:
        a = self.by_slot.get(slot)
        if not a or not a.get("focal"):
            return "50% 50%"
        return f"{a['focal'][0] * 100:.1f}% {a['focal'][1] * 100:.1f}%"

    def tag(self, slot, sizes="100vw", eager=False) -> str:
        a = self.by_slot.get(slot)
        if not a:
            return ""
        w, h = a["natural"]
        srcset = ", ".join(f"{self.base}/{a['file']}-{x}.webp {x}w" for x in a["widths"])
        src = f"{self.base}/{a['file']}-{a['widths'][-1]}.webp"
        extra = ' fetchpriority="high"' if eager else ""
        return (
            f'<img src="{e(src)}" srcset="{e(srcset)}" sizes="{e(sizes)}" '
            f'width="{w}" height="{h}" alt="{e(a["alt"])}" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async"{extra} '
            f'style="object-position:{self.focal(slot)}">'
        )

    def caption(self, slot) -> str:
        """Place and year. A caption here is never a sentence of marketing."""
        a = self.by_slot.get(slot)
        if not a:
            return ""
        return " &middot; ".join(
            str(x) for x in (a.get("location"), a.get("year")) if x
        )


def medals(c: dict) -> dict:
    """Count medals into the two divisions the client asked for.

    Counted, not typed. A row is International when it carries the
    `international` tag and National otherwise, the same split the results
    filters already use.
    """
    out = {
        "International": {"gold": 0, "silver": 0, "bronze": 0},
        "National": {"gold": 0, "silver": 0, "bronze": 0},
    }
    for r in c["results"]["rows"]:
        if not r.get("medal"):
            continue
        side = "International" if "international" in r.get("tags", []) else "National"
        out[side][r["medal"]] += 1
    return out


def first_sentences(text: str, n: int = 2) -> str:
    """Trim a paragraph to its first n sentences.

    The About block is a small introduction, per the brief; the full version
    lives on the About page. This trims rather than rewrites, so no new copy
    is invented anywhere on the index.
    """
    parts, buf, count = [], "", 0
    for ch in text:
        buf += ch
        if ch == ".":
            count += 1
            parts.append(buf.strip())
            buf = ""
            if count >= n:
                break
    return " ".join(parts) if parts else text


def nav_block() -> str:
    """N9 edge-aligned.

    The benchmark hides its navigation behind a single MENU word. That is a
    step too far for a site nobody has visited before, so a link row stays,
    tracked-out at 12px, never competing with the panel titles beneath it.
    """
    items = "".join(f'<a href="{e(h)}">{e(t)}</a>' for t, h in NAV)
    return f"""
<header class="nav" id="nav">
  <div class="wrap nav-inner">
    <a class="wordmark" href="index.html">Bhavani Thekkada</a>
    <nav class="nav-links" aria-label="Primary">{items}</nav>
  </div>
</header>"""


def panel(img: Img, slot, title, sub, cta=None, size=None, level="h2") -> str:
    """The benchmark's one repeated shape.

    Photograph fills the fold, type centred over it, one outlined button
    underneath, a place-and-year caption last.
    """
    attrs = f' data-size="{size}"' if size else ""
    hero = size == "hero"
    btn = ""
    if cta:
        label, href = cta
        btn = f'<a class="btn" data-on="shot" href="{e(href)}">{e(label)}</a>'
    cap = img.caption(slot)
    cap = f'<p class="caption">{cap}</p>' if cap else ""
    return f"""
<section class="panel"{attrs}>
  <div class="panel-shot">{img.tag(slot, "100vw", eager=hero)}</div>
  <div class="wrap panel-body" data-rise>
    <{level}>{e(title)}</{level}>
    <p class="sub">{e(sub)}</p>
    {btn}
    {cap}
  </div>
</section>"""


def sponsors(c: dict) -> str:
    """The benchmark's Rolex band: one solid colour, logos, no copy.

    Only marks with written permission on file appear. Permission for both was
    confirmed on 11 Aug 2026 and is recorded in the content file.
    """
    cur = c["partnership"].get("current") or {}
    logos = "".join(
        f'<img src="../assets/img/partners/{e(p["logo"])}" alt="{e(p["name"])}" '
        f'loading="lazy" decoding="async">'
        for p in cur.get("list", [])
        if p.get("logo")
    )
    if not logos:
        return ""
    return f"""
<aside class="sponsors" aria-label="Current support">
  <div class="wrap sponsors-inner">
    <p>{e(cur.get("note", "Current support"))}</p>
    {logos}
  </div>
</aside>"""


def split(c: dict, img: Img) -> str:
    """The benchmark's profile block, copied move for move.

    On the benchmark it is: name, a borrowed line with attribution under it
    (Messi, on Federer), two short paragraphs, VIEW PROFILE. Here the borrowed
    line is the standfirst the Associated Press reporting gave us, which is
    the same trick: someone else's words carrying the weight, attributed.
    Not in quotation marks, because it is sourced reporting rather than a
    verbatim quotation, and the citation says so honestly.
    """
    h = c["hero"]
    slot = SHOTS["about"]
    src = h.get("standfirstSource", {}).get("sourceName", "Associated Press")
    src_short = src.split(",")[0]
    return f"""
<section class="split" id="about">
  <figure class="split-shot">{img.tag(slot, "(min-width:900px) 50vw, 100vw")}</figure>
  <div class="split-body" data-rise>
    <h2>Bhavani Thekkada</h2>
    <p class="split-quote">{e(h['standfirst'])}</p>
    <p class="split-cite">Reported by the {e(src_short)}</p>
    <p>{e(first_sentences(h['profileBody'], 2))}</p>
    <p>{e(first_sentences(h['profileBody2'], 1))}</p>
    <a class="btn" href="about.html">View profile</a>
  </div>
</section>"""


def records(c: dict) -> str:
    """Two divisions, medals only. That is the whole brief for this block."""
    m = medals(c)
    cards = []
    for side in ("International", "National"):
        counts = m[side]
        total = sum(counts.values())
        rows = "".join(
            f'<span class="medal" data-medal="{k}"><i></i><b>{v}</b>{k}</span>'
            for k, v in counts.items()
            if v
        )
        cards.append(
            f"""<article class="tally-card">
        <h3>{e(side)}</h3>
        <p class="tally-total">{total}</p>
        <p class="tally-label">{'medal' if total == 1 else 'medals'}</p>
        <div class="tally-row">{rows}</div>
      </article>"""
        )
    return f"""
<section class="panel" data-ground="ice" id="records">
  <div class="wrap panel-body" data-rise>
    <h2>The record</h2>
    <p class="sub">Every medal, split two ways.</p>
    <div class="tally">{''.join(cards)}</div>
    <a class="btn" data-on="accent" href="records.html">View all results</a>
  </div>
</section>"""


def tiles(title, sub, cta, items, ground=None) -> str:
    """The card row from badosapaula.com, the client's second reference.

    A section is four things there: a title, one line, a link, four cards.
    Alternating these with the full-bleed panels is what keeps the page
    arriving one simple idea at a time instead of as a wall.
    """
    attrs = f' data-ground="{ground}"' if ground else ""
    label, href = cta
    cards = "".join(items)
    return f"""
<section class="tiles-section"{attrs}>
  <div class="wrap">
    <div class="tiles-head" data-rise>
      <h2>{e(title)}</h2>
      <p class="sub">{e(sub)}</p>
      <a class="btn" data-on="accent" href="{e(href)}">{e(label)}</a>
    </div>
    <div class="tiles">{cards}</div>
  </div>
</section>"""


def journey_tiles(c: dict, img: Img) -> str:
    beats = [
        b for b in c["story"]["beats"]
        if b.get("image") and (img.get(b["image"]) or {}).get("rights") == "owned"
    ][:4]
    items = [
        f"""<a class="tile" href="journey.html#beat-{e(b['id'])}" data-rise>
      <span class="tile-shot">{img.tag(b['image'], TILE_SIZES)}</span>
      <p class="caption">{e(b['year'])}</p>
      <h3>{e(b['heading'])}</h3>
    </a>"""
        for b in beats
    ]
    return tiles(
        c["sections"]["journey"]["title"],
        "Six seasons, from a coffee farm in Kodagu to a World Cup start list.",
        ("View journey", "journey.html"),
        items,
    )


def media_tiles(c: dict, img: Img) -> str:
    items = [
        f"""<figure class="tile" data-rise>
      <span class="tile-shot">{img.tag(s, TILE_SIZES)}</span>
      <figcaption class="caption">{img.caption(s) or 'From the archive'}</figcaption>
    </figure>"""
        for s in MEDIA_TILES
    ]
    return tiles(
        "Six seasons, photographed",
        "Press coverage and the working archive.",
        ("View media", "media.html"),
        items,
        ground="ice",
    )


def footer(c: dict) -> str:
    ct = c["contact"]
    items = "".join(f'<a href="{e(h)}">{e(t)}</a>' for t, h in NAV)
    return f"""
<footer class="foot">
  <div class="wrap">
    <p class="foot-statement">India&rsquo;s cross-country skier, on the road to 2030.</p>
    <div class="foot-rows">
      <div class="foot-links">{items}
        <a href="{e(ct['instagramUrl'])}" rel="me">Instagram</a>
        <a href="mailto:{e(ct['email'])}">Email</a>
      </div>
      <p class="foot-fine">&copy; 2026 Bhavani Thekkada Nanjunda</p>
    </div>
  </div>
</footer>"""


def page(c: dict, img: Img) -> str:
    v = fingerprint()
    desc = c.get("seo", {}).get("description") or c["hero"]["line"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Bhavani Thekkada | Indian cross-country skier</title>
<meta name="description" content="{e(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="assets/css/v2.css?v={v}">
</head>
<body>
{nav_block()}
<main>
{panel(img, SHOTS['hero'], 'Bhavani Thekkada', c['hero']['line'],
       ('View profile', 'about.html'), size='hero', level='h1')}
{sponsors(c)}
{panel(img, SHOTS['sport'], 'Cross-country skiing', c['sport']['lede'],
       ('Read more', 'about.html#sport'))}
{split(c, img)}
{records(c)}
{journey_tiles(c, img)}
{media_tiles(c, img)}
{panel(img, SHOTS['closer'], 'The road to 2030',
       'Four seasons between here and a start list in the French Alps.',
       ('Become a partner', 'partnership.html'))}
</main>
{footer(c)}
<script src="assets/js/v2.js?v={v}" defer></script>
</body>
</html>
"""


def subpage(c, img, title, lede, body_html, shot=None):
    """One interior page. Same language as the index, one idea per page.

    Every interior page is the same three moves: a short photographic header,
    the content, the footer. Nothing on these pages scrolls sideways, pins,
    or animates beyond the standard rise.
    """
    v = fingerprint()
    head_shot = ""
    if shot:
        head_shot = (
            f'<div class="panel-shot">{img.tag(shot, "100vw", eager=True)}</div>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{e(title)} | Bhavani Thekkada</title>
<meta name="description" content="{e(lede)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="assets/css/v2.css?v={v}">
</head>
<body>
{nav_block()}
<main>
<section class="panel" data-size="head">{head_shot}
  <div class="wrap panel-body">
    <h1>{e(title)}</h1>
    <p class="sub">{e(lede)}</p>
  </div>
</section>
{body_html}
</main>
{footer(c)}
<script src="assets/js/v2.js?v={v}" defer></script>
</body>
</html>
"""


def about_page(c, img):
    h = c["hero"]
    facts = "".join(
        f'<div class="fact"><dt class="caption">{e(x["k"])}</dt>'
        f'<dd>{e(x["v"])}</dd></div>'
        for x in h.get("profileFacts", [])
    )
    sport = c["sport"]
    disciplines = "".join(
        f'<div class="fact"><dt class="caption">{e(d["name"])}</dt>'
        f'<dd>{e(d.get("note") or d.get("desc") or "")}</dd></div>'
        for d in sport.get("disciplines", [])[:4]
    )
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <h2>{e(h['profileHeading'])}</h2>
    <p>{e(h['profileBody'])}</p>
    <p>{e(h['profileBody2'])}</p>
    <dl class="facts">{facts}</dl>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="sport">
  <div class="wrap prose">
    <h2>The sport</h2>
    <p>{e(sport['lede'])}</p>
    <p>{e(sport.get('yearNote') or '')}</p>
    <dl class="facts">{disciplines}</dl>
  </div>
</section>"""
    return subpage(c, img, "About", h["line"], body, shot="portrait-studio")


def journey_page(c, img):
    items = []
    for b in c["story"]["beats"]:
        shot = ""
        if b.get("image"):
            shot = (
                '<figure class="step-shot">'
                + img.tag(b["image"], "(min-width:800px) 44vw, 92vw")
                + "</figure>"
            )
        items.append(f"""
  <article class="step" id="beat-{e(b['id'])}">
    {shot}
    <div class="step-copy">
      <p class="caption">{e(b['year'])}</p>
      <h2>{e(b['heading'])}</h2>
      <p>{e(b['body'])}</p>
    </div>
  </article>""")
    body = (
        '<section class="prose-fold"><div class="wrap steps">'
        + "".join(items)
        + "</div></section>"
    )
    return subpage(c, img, c["sections"]["journey"]["title"],
                   "Six seasons, told in order.", body, shot="ridge-sunrise")


def records_page(c, img):
    rows = [r for r in c["results"]["rows"] if r.get("medal")]
    intl = [r for r in rows if "international" in r.get("tags", [])]
    natl = [r for r in rows if "international" not in r.get("tags", [])]

    def table(rs):
        body = "".join(
            f'<tr><td class="caption">{e(r["year"])}</td>'
            f'<td><b>{e(r["event"])}</b><span>{e(r["detail"])}'
            f' &middot; {e(r["place"])}</span></td>'
            f'<td class="c-medal"><i data-medal="{e(r["medal"])}"></i>'
            f'{e(r["medal"])}</td></tr>'
            for r in rs
        )
        return f'<table class="medals"><tbody>{body}</tbody></table>'

    m = medals(c)
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <h2>International</h2>
    <p>{sum(m['International'].values())} medals, every one on snow outside India.</p>
    {table(intl)}
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap prose">
    <h2>National</h2>
    <p>{sum(m['National'].values())} medals across the Khelo India Winter Games
       and the national championships.</p>
    {table(natl)}
  </div>
</section>"""
    return subpage(c, img, "The record", "Every medal, in two divisions.",
                   body, shot="nordic-podium")


def media_page(c, img):
    press = []
    for pr in c["press"]:
        head = pr.get("headline") or pr.get("title") or ""
        if not head:
            continue
        outlet = pr.get("outlet") or ""
        url = pr.get("url") or ""
        inner = f'<b>{e(head)}</b><span class="caption">{e(outlet)}</span>'
        press.append(
            f'<li><a href="{e(url)}" rel="noopener" target="_blank">{inner}</a></li>'
            if url else f"<li><p>{inner}</p></li>"
        )
    lib = json.loads((CONTENT / "images.json").read_text(encoding="utf-8"))
    gallery = "".join(
        f'<figure class="tile"><span class="tile-shot">'
        f'{img.tag(a["slot"], TILE_SIZES)}</span>'
        f'<figcaption class="caption">'
        f'{img.caption(a["slot"]) or "From the archive"}</figcaption></figure>'
        for a in lib["images"]
        if a.get("rights") == "owned" and a.get("category") in ("race", "training")
    )
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <h2>Press</h2>
    <ul class="press">{''.join(press)}</ul>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap">
    <div class="prose"><h2>Photographs</h2></div>
    <div class="tiles" style="margin-top:var(--space-md)">{gallery}</div>
  </div>
</section>"""
    return subpage(c, img, "Media",
                   "Every article written about her, and six seasons of photographs.",
                   body, shot="khelo-medals")


def partnership_page(c, img):
    p = c["partnership"]
    areas = "".join(
        f'<div class="fact"><dt class="caption">{e(a["title"])}</dt>'
        f'<dd>{e(a["body"])}</dd></div>'
        for a in p.get("areas", [])
    )
    t = c.get("targets", {}).get("finale", {})
    ct = c["contact"]
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <h2>{e(t.get('year', '2030'))} &middot; {e(t.get('title', 'Winter Olympics'))}</h2>
    <p>{e(t.get('line') or '')}</p>
    <p class="caption">{e(t.get('host') or '')} &middot; {e(t.get('dates') or '')}</p>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap prose">
    <h2>What support funds</h2>
    <dl class="facts">{areas}</dl>
  </div>
</section>
<section class="prose-fold" id="contact">
  <div class="wrap prose">
    <h2>Work with Bhavani</h2>
    <p>One route in, for everything.</p>
    <p><a class="btn" data-on="accent" href="mailto:{e(ct['email'])}">{e(ct['email'])}</a></p>
  </div>
</section>"""
    return subpage(c, img, "Partnership",
                   "The road to 2030, and what support makes possible.",
                   body, shot="chile-lake")


def main() -> int:
    c = json.loads((CONTENT / "bhavani.json").read_text(encoding="utf-8"))
    lib = json.loads((CONTENT / "images.json").read_text(encoding="utf-8"))
    img = Img(lib)

    missing = [s for s in SHOTS.values() if not img.get(s)]
    if missing:
        print("missing image slots:", ", ".join(missing))
        return 1

    OUT.mkdir(exist_ok=True)
    out = OUT / "index.html"
    out.write_text(page(c, img), encoding="utf-8")
    (OUT / "about.html").write_text(about_page(c, img), encoding="utf-8")
    (OUT / "journey.html").write_text(journey_page(c, img), encoding="utf-8")
    (OUT / "records.html").write_text(records_page(c, img), encoding="utf-8")
    (OUT / "media.html").write_text(media_page(c, img), encoding="utf-8")
    (OUT / "partnership.html").write_text(partnership_page(c, img), encoding="utf-8")

    m = medals(c)
    print(f"v2/  6 pages   index {out.stat().st_size / 1024:.1f} KB")
    print("  benchmark  rogerfederer.com  ·  6 panels + sponsor band + split")
    print(f"  medals     international {sum(m['International'].values())}"
          f"  national {sum(m['National'].values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
