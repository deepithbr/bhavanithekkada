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
import math
import re
import pathlib
import sys

from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / "content"
# Where the pages land. V2 built into /v2 while it was under review; it is
# the site now, so `--root` writes it to the deploy root instead and swings
# the asset paths with it. Both modes still work: /v2 stays reachable for
# anyone holding a review link.
AT_ROOT = "--root" in sys.argv
OUT = ROOT if AT_ROOT else ROOT / "v2"
# `../assets/img` from a page one directory down, `assets/img` from the root.
IMG_BASE = "assets/img" if AT_ROOT else "../assets/img"
# The 404 needs absolute paths, because a 404 is served at any depth.
ABS = "/assets" if AT_ROOT else "/v2/assets"

FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Archivo:wght@400;500;600;700;800"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&family=Newsreader:opsz,wght@6..72,300..700"
    "&display=swap"
)

# The five pages the client asked for, and no more: home, about, the
# journey with the record at the end of it, media, partnership. Records is
# not a destination of its own; it is where the journey lands.
# Her eight destinations, 26 Aug: Home is the wordmark, Contact is the
# pill at the end of the row.
# Home leaves the row: her name in the bar is the way back, as on the
# reference. Contact stays the pill at the row's end.
NAV = [
    ("Journey", "journey.html"),
    ("Career", "achievements.html"),
    ("Speaking", "speaking.html"),
    ("Partnerships", "partnership.html"),
    ("Media", "media.html"),
    ("Journal", "journal.html"),
]

JOURNAL_DIR = CONTENT / "journal"

# Absolute origin for share cards: og:image must be absolute or crawlers
# ignore it. Update once the final domain exists.
ORIGIN = "https://bhavanithekkada.pages.dev"

# One photograph per panel. Named here rather than inline so the whole cast of
# the home page is visible in one place and can be swapped without reading any
# markup. Every one is from her own archive, rights settled.
SHOTS = {
    "hero": "hero-race-pro",
    "sport": "classic-tracks",
    "about": "portrait-studio",
    # Swapped with the Partnership banner at the client's request,
    # 30 Aug 2026, to see how each reads in the other place.
    "closer": "summit-solo",
}

# The four photographs in the media row. Journey takes its four from the story
# beats, so it always matches whatever the journey page shows.
MEDIA_TILES = ["khelo-medals", "chile-corralco", "race-worldcup", "nordic-overlook"]

TILE_SIZES = "(min-width:1000px) 22vw, (min-width:560px) 45vw, 92vw"

# Three across on a desktop, two on a tablet, one on a phone.
SKILL_SIZES = "(min-width:900px) 30vw, (min-width:600px) 45vw, 92vw"

# Five across on a desktop, two on a phone.
OPT_SIZES = "(min-width:1100px) 19vw, (min-width:640px) 32vw, 46vw"



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
        self.base = IMG_BASE

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


def nav_block(current=None, glass=False) -> str:
    """N9 edge-aligned.

    The benchmark hides its navigation behind a single MENU word. That is a
    step too far for a site nobody has visited before, so a link row stays,
    tracked-out at 12px, never competing with the panel titles beneath it.
    """
    items = "".join(
        f'<a href="{e(h)}"'
        + (' aria-current="page"' if h == current else "")
        + f'>{e(t)}</a>'
        for t, h in NAV
    )
    # Work with me rides inside the link row so the mobile menu carries it
    # too; the styling singles it out on desktop.
    wcur = ' aria-current="page"' if current == "contact.html" else ""
    items += f'<a class="nav-work" href="contact.html"{wcur}>Contact</a>'
    g = ' data-glass="true"' if glass else ""
    return f"""
<header class="nav" id="nav"{g}>
  <div class="wrap nav-inner">
    <a class="wordmark wordmark-name" href="index.html">Bhavani Thekkada</a>
    <nav class="nav-links" id="nav-links" aria-label="Primary">{items}</nav>
    <button class="nav-toggle" type="button" aria-expanded="false"
      aria-controls="nav-links">Menu</button>
  </div>
</header>"""


def statline(c) -> str:
    """Her career in four measured figures. Computed, never typed: the
    latitude span from the map pins, the medals from the results rows, the
    places from the pins, so the line can never drift from the site."""
    pts = c["internationalFootprint"]
    lats = [p["lat"] for p in pts]
    span = round(max(lats) - min(lats))
    meds = sum(1 for r in c["results"]["rows"] if r.get("medal"))
    # Southern-hemisphere pins carry negative latitude; -41degN is not a
    # place. Hemisphere comes from the sign.
    def hemi(v):
        v = round(v)
        return f"{abs(v)}&deg;{'S' if v < 0 else 'N'}"

    bits = [
        f"{hemi(min(lats))} to {hemi(max(lats))}",
        f"{span}&deg; of latitude",
        f"{meds} medals",
        f"{len(pts)} places",
    ]
    inner = "".join(f"<span>{x}</span>" for x in bits)
    return f'<p class="statline caption" data-rise>{inner}</p>'


def draw_mark(title, mark=None) -> str:
    """A headline with one phrase struck through with a drawn stroke.

    A path rather than a rule, because a ruled underline reads as a link
    and this is meant to look scratched into the snow. It draws itself
    when the section comes into view; the script sets the flag. The title
    is escaped first and the marker matched against the escaped text, so
    the phrase can never smuggle markup through.
    """
    out = e(title)
    if not mark:
        return out
    return out.replace(
        e(mark),
        f'<span class="mark-draw">{e(mark)}'
        '<svg class="draw-line" viewBox="0 0 300 14" '
        'preserveAspectRatio="none" aria-hidden="true" focusable="false">'
        '<path pathLength="1" fill="none" stroke="currentColor" '
        'stroke-width="2.6" stroke-linecap="round" '
        'd="M3,9.6 C38,4.4 74,11.4 112,7.1 C150,2.9 186,10.3 224,6.2 '
        'C252,3.2 276,8.2 297,4.6"/></svg></span>',
        1,
    )


def panel(img: Img, slot, title, sub, cta=None, size=None, level="h2",
          pos=None, kicker=None, align=None, mark=None) -> str:
    """The benchmark's one repeated shape.

    Photograph fills the fold, type centred over it, one outlined button
    underneath, a place-and-year caption last.
    """
    attrs = f' data-size="{size}"' if size else ""
    if align:
        attrs += f' data-align="{align}"'
    hero = size == "hero"
    btn = ""
    if cta:
        label, href = cta
        btn = f'<a class="btn" data-on="shot" href="{e(href)}">{e(label)}</a>'
    # Her 27 Aug design list: no place-and-date captions on photographs.
    cap = ""
    marked = draw_mark(title, mark)
    shot = img.tag(slot, "100vw", eager=hero)
    if pos:
        # Steer the cover crop for this panel only. The library's focal point
        # is right for every other container this photograph appears in.
        shot = shot.replace(
            f"object-position:{img.focal(slot)}", f"object-position:{pos}"
        )
    return f"""
<section class="panel"{attrs}>
  <div class="panel-shot">{shot}</div>
  <div class="wrap panel-body" data-rise>
    {f'<p class="caption">{e(kicker)}</p>' if kicker else ''}
    <{level}>{marked}</{level}>
    <p class="sub">{e(sub)}</p>
    {btn}
    {cap}
  </div>
</section>"""


# Three, not four. Four skis in the column left each one 137px wide and
# the photographs unreadable; three at 192px carry a subject.
MEDIA_STRIP = ["race-worldcup", "chile-corralco", "night-training"]


def media_strip(c, img) -> str:
    """The way through to Media, after the journey.

    The client's reference leans a pair of skis across the page. So the
    photographs are cut into ski silhouettes rather than set in tilted
    rectangles: pointed tip, parallel sides, rounded tail, leaning at one
    angle and stepped down the page. The proportion is stylised, nearer
    1:3.6 than a real ski's 1:15, because a true ski leaves a sliver of
    photograph and the photographs are the point of the section."""
    frames = "".join(
        f'<a class="frame" href="media.html" tabindex="-1" aria-hidden="true" '
        f'style="--i:{n}">{img.tag(slot, "(min-width:900px) 20vw, 44vw")}</a>'
        # Rights are settled before a photograph is published, here as
        # everywhere else on the site.
        for n, slot in enumerate(
            [x for x in MEDIA_STRIP
             if (img.get(x) or {}).get("rights") == "owned"]
        )
    )
    # One clip path, defined once, referenced by every frame. Normalised
    # coordinates so it stretches to whatever size the frame ends up.
    ski = """<svg class="ski-def" width="0" height="0" aria-hidden="true"
      focusable="false"><defs><clipPath id="ski"
      clipPathUnits="objectBoundingBox"><path d="M0.5,0
      C0.665,0.004 0.855,0.028 0.951,0.072
      C0.988,0.089 1,0.107 1,0.136
      L1,0.957 C1,0.981 0.989,0.994 0.962,0.997
      C0.892,1 0.677,1 0.5,1
      C0.323,1 0.108,1 0.038,0.997
      C0.011,0.994 0,0.981 0,0.957
      L0,0.136 C0,0.107 0.012,0.089 0.049,0.072
      C0.145,0.028 0.335,0.004 0.5,0 Z"/></clipPath></defs></svg>"""
    return f"""
<section class="media-strip" id="media">
  {ski}
  <div class="wrap media-strip-inner">
    <div class="media-say" data-rise>
      <p class="caption">Media</p>
      <h2>Press and photographs</h2>
      <p>Coverage from Indian and international outlets, and the season&rsquo;s
      photographs from her own archive.</p>
      <a class="btn" href="media.html">View media</a>
    </div>
    <div class="media-lean" data-rise>{frames}</div>
  </div>
</section>"""


def backing(c) -> str:
    """The wrap-up: one centred line, three marks, one way through.

    No descriptors. Each mark carries its own name, and what the support
    actually provides is on the Partnerships page, where someone has asked
    to read it.

    Only marks with written permission on file appear. Permission was
    confirmed on 11 Aug 2026 and is recorded in the content file."""
    cur = c["partnership"].get("current") or {}
    rows = [p for p in cur.get("list", []) if p.get("logo")]
    if not rows:
        return ""
    marks = "".join(
        f'<span class="backer-mark">'
        f'<img src="../assets/img/partners/{e(p["logo"])}" '
        f'alt="{e(p["name"])}" loading="lazy" decoding="async"></span>'
        for p in rows
    )
    return f"""
<section class="backing" id="backing" data-ground="ice">
  <div class="wrap">
    <h2 class="backing-head" data-rise>Supported by</h2>
    <div class="backers" data-rise>{marks}</div>
    <p class="backing-more" data-rise>
      <a class="btn" data-on="accent"
         href="partnership.html">Partner with her</a></p>
  </div>
</section>"""


def sponsors(c: dict) -> str:
    """The benchmark's sponsor band: logos and nothing else.

    No label. The first pass wrote CURRENT SUPPORT beside the marks and forced
    both to white on navy, which flattened the Reliance lockup and reduced the
    Karnataka crest to an unreadable silhouette. The client called it what it
    was. Federer's band carries no caption either: two logos on a quiet ground
    say whose support this is without a heading announcing it.

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
  <div class="wrap sponsors-inner">{logos}</div>
</aside>"""


# The hero rotation: four frames, each with its own crop, crossfading
# slowly. Not a carousel, no dots, no arrows: the frame changes the way
# stadium screens change, and reduced motion holds the first frame.
# Three frames, not four: the Worlds start, the flag, the motion. The
# Holmenkollen frame left the rotation because it closes the page and a
# hero should not preview its own ending.
# Three frames, face first: the Gulmarg portrait in the India suit
# opens so a visitor meets her before the venues, then the Worlds
# start, then the flag.
# The -cine slots are the same frames under one baked film grade
# (S-curve, navy shadows, unsharp, corner vignette), so the rotation
# reads as one production instead of three phone exposures.
HERO_SLIDES = [
    ("hero-portrait-cine", "50% 14%"),
    ("race-worldcup-cine", "50% 45%"),
    ("flag-harbin-cine", "50% 34%"),
]


def hero_panel(c, img) -> str:
    """The reference composition: her name holds the top-left as the
    wordmark, and the display slot on the photograph carries the
    punchline instead. Three short lines, the point of difference in
    accent, the credential chip beneath. The name is gone from here
    because it is already the first thing on the page."""
    # The level of competition, typed rather than listed: she is still
    # writing this record, so the hero writes it too. The ghost lines hold
    # the plate at its widest so nothing jitters while the caret works,
    # and the same five figures feed the Career page.
    lv = levels_data(c)
    ghosts = "".join(
        f'<span class="cred-ghost"><b>{int(x["n"]):02d}</b>'
        f'<span>{e(x["k"])}</span></span>'
        for x in lv
    )
    spoken = " ".join(f'{e(x["n"])} {e(x["k"])}.' for x in lv)
    first = lv[0]
    chip = f"""<div class="hero-foot">
      <div class="hero-chip">
        <p class="hero-cred" data-type="true" aria-hidden="true">
          <span class="cred-live"><b class="cred-n">{int(first["n"]):02d}</b><span
            class="cred-t">{e(first["k"])}</span><i class="cred-caret"></i></span>
          {ghosts}
        </p>
        <p class="vh">Level of competition. {spoken}</p>
      </div>
      <a class="hero-record" href="achievements.html">Full record <span
        aria-hidden="true">&rarr;</span></a>
    </div>"""

    slot = "hero-race-pro"
    tag = img.tag(slot, "100vw", eager=True)
    tag = tag.replace(
        f"object-position:{img.focal(slot)}", "object-position:48% 30%"
    )
    # Her copy, so it lives in the content file. The accent falls on one
    # phrase inside the first line; it is matched against the escaped text
    # and never against raw input.
    h = c["hero"]
    l1 = e(h.get("punchLine1") or "")
    acc = h.get("punchAccent")
    if acc:
        l1 = l1.replace(e(acc), f'<span class="hl">{e(acc)}</span>', 1)
    return f"""
<section class="panel" data-size="hero">
  <div class="panel-shot">{tag}</div>
  <div class="wrap panel-body hero-min" data-rise>
    <h1 class="hero-punch"><span class="punch-eyebrow">{e(h.get(
      'punchEyebrow') or '')}</span><span
      class="punch-big">{l1}</span><span
      class="punch-big">{e(h.get('punchLine2') or '')}</span></h1>
    {chip}
  </div>
</section>"""


# The ground under Career at a glance. Not a picture to look at: a roped
# line working up a slope with no path on it, dropped almost to black, so
# the card reads as depth behind the type rather than a second photograph
# competing with the hero one card above it.
GLANCE_SHOT = "ridge-sunrise"


def glance_fold(c, img) -> str:
    """The second card: her career stated before it is told.

    The hero is a photograph carrying four words. The story card after
    this one is a portrait beside running text. Between them the page
    needs a card that is neither, so this one is a line of hers set over a
    photograph. The line is a quotation and is signed rather than filed
    under a section label, and the stroke stays under the half that is
    about her. The two paragraphs sit in a pair of columns underneath at
    a size meant to be read rather than scanned, in one column on the left
    so the photograph keeps the half of the frame worth looking at.
    """
    h = c["hero"]
    shot = img.tag(GLANCE_SHOT, "100vw").replace(
        f'object-position:{img.focal(GLANCE_SHOT)}', "object-position:50% 42%"
    )
    shot = re.sub(r'alt="[^"]*"', 'alt=""', shot, count=1)
    shot = shot.replace("<img ", '<img aria-hidden="true" ', 1)
    # The quotation breaks where she breaks it, at the comma, so the
    # marked phrase starts its own line. Left inline it sat against the
    # comma and the two read as one word. If the phrase is ever absent
    # from the line the whole thing falls back to a single block.
    line = h.get("glanceHeadline") or ""
    mark = h.get("glanceMark")
    if mark and mark in line:
        lead, rest = line.split(mark, 1)
        quote = (f'<span class="q-a">&ldquo;{e(lead.rstrip())}</span>'
                 f'<span class="q-b">{draw_mark(mark + rest, mark)}'
                 f'&rdquo;</span>')
    else:
        quote = f'<span class="q-a">&ldquo;{draw_mark(line, mark)}&rdquo;</span>'
    return f"""
<section class="glance" id="glance">
  <div class="glance-shot">{shot}</div>
  <div class="wrap glance-body">
    <figure class="glance-quote" data-rise>
      <blockquote>
        <p class="glance-head">{quote}</p>
      </blockquote>
      <figcaption class="caption glance-by">{e(h.get(
        'glanceAttrib') or '')}</figcaption>
    </figure>
    <div class="glance-cols" data-rise>
      <p>{e(h.get('glanceBody') or '')}</p>
      <p>{e(h.get('glanceBody2') or '')}</p>
    </div>
  </div>
</section>"""


def who_she_is(c, img) -> str:
    """The story card. Her portrait pins and holds the viewport while
    the story and her three facts scroll through beside it; the facts
    live in the column so the text side is long enough to actually
    travel past the pinned photograph."""
    h = c["hero"]
    facts = "".join(
        f'<div class="fact"><dt class="caption">{e(x["k"])}</dt>'
        f'<dd>{e(x["v"])}</dd></div>'
        for x in h.get("profileFacts", [])
    )
    return f"""
<section class="split" id="who">
  <figure class="split-shot">{img.tag(SHOTS['about'], "(min-width:900px) 50vw, 100vw")}</figure>
  <div class="split-body" data-rise>
    <p class="caption">{e(h.get('profileKicker') or 'Who she is')}</p>
    <h2>{e(h['profileHeading'])}</h2>
    <p>{e(h['profileBody'])}</p>
    <p>{e(h['profileBody2'])}</p>
    <p>{e(h.get('profileBody3') or '')}</p>
    <p>{e(h.get('profileBody4') or '')}</p>
    {f'<p class="split-close">{e(h["profileClose"])}</p>'
     if h.get('profileClose') else ''}
    <dl class="facts">{facts}</dl>
  </div>
</section>"""


def who_facts(c) -> str:
    facts = "".join(
        f'<div class="fact"><dt class="caption">{e(x["k"])}</dt>'
        f'<dd>{e(x["v"])}</dd></div>'
        for x in c["hero"].get("profileFacts", [])
    )
    return f"""
<section class="prose-fold" id="who-facts">
  <div class="wrap">
    <dl class="facts facts-row">{facts}</dl>
  </div>
</section>"""


def levels_data(c):
    """The five level-of-competition figures, in one place.

    The hero types them and the Career page tabulates them; both read
    this, so the two can never disagree. The medal counts are computed
    from the results rows rather than typed."""
    rows = [r for r in c["results"]["rows"] if r.get("medal")]
    intl = sum(1 for r in rows if "international" in r.get("tags", []))
    natl = len(rows) - intl
    cards = list(c.get("levels", []))
    cards.append({"n": str(intl), "k": "International medals",
                  "s": "FIS & international competition"})
    cards.append({"n": str(natl), "k": "National medals",
                  "s": "National & Khelo India competitions"})
    return cards


# One photograph per figure, in the order levels_data returns them:
# her three start-level cards from the content file, then the two medal
# counts computed from the results rows. Every one of them is owned, and
# each answers the figure it sits under. Holmenkollen stands in for the
# World Championships rows, which have no owned frame of their own.
SLAB_SHOTS = ["race-worldcup", "holmenkollen", "flag-harbin",
              "nordic-podium", "contingent-2021"]

SLAB_SIZES = "(min-width:900px) 16vw, 44vw"

# Behind the season band: a long line of skiers spread across an open
# ridge, which is the nearest owned frame to what the band is about.
SEASON_SHOT = "snow-ridge-line"


def record_slabs(c, img, head=True, link=True) -> str:
    """The level of competition, as the client's slab reference.

    Five leaning plates alternating navy and race-suit blue, each
    holding one figure reversed out of it, the label set underneath the
    way the reference sets its athletes' names. Same figures as the
    Career page, from the same helper, so the two can never disagree;
    the medal counts are still computed from the results rows.

    The lean is a skew on the plate with the figure counter-skewed
    inside it, so the type stays upright while the shape leans. Below
    the row breakpoint the skew and the stagger both come off: five
    leaning plates on a phone are unreadable, and a plain two-up grid
    keeps the alternating fills, which is the part of the reference
    that carries the idea.
    """
    cards = levels_data(c)
    lis = "".join(
        f'<li class="slab" data-fill="{"accent" if n % 2 else "deep"}"'
        f' data-rise><span class="slab-plate">'
        f'<span class="slab-shot">{img.tag(SLAB_SHOTS[n], SLAB_SIZES)}</span>'
        f'<b class="slab-n tally-total">{e(x["n"])}</b></span>'
        f'<span class="slab-k">{e(x["k"])}</span>'
        f'<span class="slab-s caption">{e(x["s"])}</span></li>'
        for n, x in enumerate(cards)
        if n < len(SLAB_SHOTS)
    )
    top = ('<div class="slabs-head" data-rise>'
           '<p class="caption">Level of competition</p>'
           '<h2>The record</h2></div>') if head else ""
    # Pointing at the page you are already standing on is furniture.
    more = ('<p class="caption slabs-more"><a href="achievements.html">Every '
            'start, race by race &rarr;</a></p>') if link else ""
    return f"""
<section class="slabs" id="level"{'' if head else ' data-bare'}>
  <div class="wrap">
    {top}
    <ol class="slab-row">{lis}</ol>
    {more}
  </div>
</section>"""

def sport_fold(c, img) -> str:
    """The sport, rebuilt to the client's poster reference: one horizontal
    band rather than a stack of cards.

    A photograph of her cut into an angled slab on the left, with a pale
    wedge offset behind it the way the poster sets its subject inside a
    shape. The name of the sport is the poster's own lockup, a wide-tracked
    display word over a small-caps line. Her four ways of racing run as a
    single row beneath, each tagged with what it actually is, so the
    technique-and-format distinction from her earlier brief survives inside
    one row of four."""
    sp = c["sport"]
    ds = sp.get("disciplines", [])
    # The poster's signature move: the wedge cuts through the athlete, so
    # the part inside it is fully exposed and the part outside falls away
    # to a ghost on the ice ground. Two copies of one frame, aligned on the
    # same focal point; the browser decodes the file once.
    slot = "double-pole"
    base = img.tag(slot, "(min-width: 900px) 42vw, 100vw").replace(
        f"object-position:{img.focal(slot)}", "object-position:54% 30%"
    )
    ghost = base.replace("<img ", '<img class="cut-ghost" aria-hidden="true" ', 1)
    ghost = re.sub(r'alt="[^"]*"', 'alt=""', ghost, count=1)
    main = base.replace("<img ", '<img class="cut-main" ', 1)
    shot = ghost + main
    # Her note of 30 Aug: the numbering goes. Without it the four cards
    # repeated TECHNIQUE, TECHNIQUE, RACE FORMAT, RACE FORMAT down the row,
    # which the numerals had been masking. So they group instead: one label
    # per pair, which is the section's own headline said as a layout.
    order, groups = [], {}
    for d in ds[:4]:
        k = d.get("kind") or "Way of racing"
        if k not in groups:
            order.append(k)
            groups[k] = []
        groups[k].append(d)
    count = {1: "One", 2: "Two", 3: "Three", 4: "Four"}
    ways = "".join(
        f'<div class="way" data-rise>'
        f'<p class="caption way-label">{e(count.get(len(groups[k]), len(groups[k])))} '
        f'{e(k.lower())}{"s" if len(groups[k]) != 1 else ""}</p>'
        + "".join(
            f'<div class="fmt"><h3>{e(d["name"])}</h3>'
            f'<p>{e(d.get("note") or "")}</p></div>'
            for d in groups[k]
        )
        + "</div>"
        for k in order
    )
    # Where her season goes, and why it has to. It closes the card
    # because it is the consequence of everything above it: two
    # techniques and two formats, raced in a country with a short
    # season, which is what puts her on four continents a year.
    season = ""
    if sp.get("seasonHeading"):
        ridge = img.tag(SEASON_SHOT, "100vw").replace(
            f'object-position:{img.focal(SEASON_SHOT)}',
            "object-position:50% 46%")
        ridge = re.sub(r'alt="[^"]*"', 'alt=""', ridge, count=1)
        ridge = ridge.replace("<img ", '<img aria-hidden="true" ', 1)
        places = "".join(
            f'<li>{e(x)}</li>' for x in sp.get("seasonPlaces", []))
        season = f"""
<aside class="sport-season" data-rise>
  <div class="season-shot">{ridge}</div>
  <div class="wrap season-inner">
    <h3 class="season-head">{e(sp['seasonHeading'])}</h3>
    <div class="season-say">
      <p>{e(sp.get('seasonBody') or '')}</p>
      <p>{e(sp.get('seasonBody2') or '')}</p>
    </div>
    {f'<ol class="season-places">{places}</ol>' if places else ''}
  </div>
</aside>"""
    return f"""
<section class="sport-band" id="sport" data-ground="ice">
  <div class="wrap">
    <div class="sport-top">
      <figure class="sport-cut" data-rise>
        <div class="cut-plate">{shot}</div>
      </figure>
      <div class="sport-say" data-rise>
        <p class="caption sport-kicker">{e(sp.get('kicker') or 'The sport')}</p>
        <h2 class="sport-word"><span>Cross-country</span><span>skiing</span></h2>
        <p class="sport-word-sub">A Nordic discipline</p>
        <p class="sport-lede">{e(sp.get('nordicIntro') or '')}</p>
        <p class="sport-lede sport-lede-2">{e(sp.get('lede') or '')}</p>
        <p class="sport-bridge">{e(sp.get('context') or '')}</p>
      </div>
    </div>
    <div class="sport-ways">{ways}</div>
  </div>
  {season}
</section>"""


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


def records(c, img) -> str:
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
    total = sum(sum(v.values()) for v in m.values())
    return f"""
<section class="record-band" id="records">
  <div class="record-copy" data-rise>
    <h2>The record</h2>
    <p class="sub">{total} medals. Two divisions.</p>
    <div class="tally">{''.join(cards)}</div>
    <a class="btn" data-on="accent" href="journey.html#records">View all results</a>
  </div>
  <figure class="record-shot">
    {img.tag('nordic-podium', "(min-width:900px) 42vw, 100vw")}
  </figure>
</section>"""


def tiles(title, sub, cta, items, ground=None, kicker=None) -> str:
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
      <div>
      {f'<p class="caption">{e(kicker)}</p>' if kicker else ''}
      <h2>{e(title)}</h2>
      <p class="sub">{e(sub)}</p>
      </div>
      <a class="btn" data-on="accent" href="{e(href)}">{e(label)}</a>
    </div>
    <div class="tiles">{cards}</div>
  </div>
</section>"""


def media_tiles(c: dict, img: Img) -> str:
    items = [
        f"""<figure class="tile" data-rise>
      <span class="tile-shot">{img.tag(s, TILE_SIZES)}</span>
    </figure>"""
        for s in MEDIA_TILES
    ]
    stories = sum(1 for pr in c["press"] if pr.get("title"))
    photos = sum(
        1 for a in img.by_slot.values()
        if a.get("rights") == "owned" and a.get("category") in ("race", "training")
    )
    return tiles(
        "Six seasons, photographed",
        f"{stories} stories in print, {photos} photographs from her own archive.",
        ("View media", "media.html"),
        items,
        ground="ice",
        kicker="The archive",
    )


def footer(c: dict) -> str:
    # Her item 6: the block beneath every page goes. What survives is what
    # her document's Contact section lists: Instagram, email, copyright.
    # The page links live in the navigation alone.
    ct = c["contact"]
    return f"""
<footer class="foot">
  <div class="wrap">
    <div class="foot-rows" style="margin-top:0;border-top:none">
      <div class="foot-links">
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
<meta name="color-scheme" content="only light">
<title>Bhavani Thekkada | Indian cross-country skier</title>
<meta name="description" content="{e(desc)}">
<meta property="og:type" content="profile">
<meta property="og:title" content="Bhavani Thekkada | Indian cross-country skier">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{ORIGIN}{ABS}/og/index.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="assets/css/v2.css?v={v}">
<link rel="preload" as="image" href="../assets/img/{SHOTS['hero']}-1600.webp">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{nav_block(current="index.html", glass=True)}
<main id="main">
<div class="stack">
{hero_panel(c, img)}
{glance_fold(c, img)}
{who_she_is(c, img)}
{sport_fold(c, img)}
{panel(img, SHOTS['closer'],
       'Join me on my journey to the 2030 French Alps Olympic Winter Games',
       'Cross-country skiing',
       ('View journey', 'journey.html'), pos='50% 52%',
       size='closer', mark='Olympic Winter Games')}
{media_strip(c, img)}
{backing(c)}
</div>
</main>
{footer(c)}
<script src="assets/js/v2.js?v={v}" defer></script>
</body>
</html>
"""


def subpage(c, img, title, lede, body_html, shot=None, current=None,
            pos=None, og=None):
    """One interior page. Same language as the index, one idea per page.

    Every interior page is the same three moves: a short photographic header,
    the content, the footer. Nothing on these pages scrolls sideways, pins,
    or animates beyond the standard rise.
    """
    v = fingerprint()
    head_shot = ""
    if shot:
        tag = img.tag(shot, "100vw", eager=True)
        if pos:
            # A header band shows less than half the frame, so each page says
            # which slice. The library focal point serves the tiles; a 46svh
            # strip needs its own judgement, made against the render.
            tag = tag.replace(
                f"object-position:{img.focal(shot)}", f"object-position:{pos}"
            )
        head_shot = "<div class=\"panel-shot\">" + tag + "</div>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="only light">
<title>{e(title)} | Bhavani Thekkada</title>
<meta name="description" content="{e(lede)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(title)} | Bhavani Thekkada">
<meta property="og:description" content="{e(lede)}">
<meta property="og:image" content="{ORIGIN}{ABS}/og/{e(og or 'index')}.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="assets/css/v2.css?v={v}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{nav_block(current)}
<main id="main">
<section class="panel" data-size="head">{head_shot}
  <div class="wrap panel-body">
    <a class="crumb caption" href="index.html">&larr; Home</a>
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
  <div class="wrap about-split">
    <figure class="about-shot" data-rise>
      {img.tag('portrait-studio', "(min-width:860px) 38vw, 92vw")}
    </figure>
    <div class="prose" data-rise>
      <h2>{e(h['profileHeading'])}</h2>
      <p class="pull">{e(h['standfirst'])}</p>
      <p class="pull-cite caption">Reported by the Associated Press</p>
      <p>{e(h['profileBody'])}</p>
      <p>{e(h['profileBody2'])}</p>
    </div>
  </div>
  <div class="wrap" style="margin-top:var(--space-lg)">
    <dl class="facts facts-row">{facts}</dl>
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
    # Speaking has its own page now; About keeps the anchor old links used
    # and points across.
    sp = c.get("speaking", {})
    if sp:
        body += f"""
<section class="prose-fold" id="speaking">
  <div class="wrap prose">
    <h2>Speaking</h2>
    <p>{e(sp.get('lede') or '')}</p>
    <a class="btn" href="speaking.html">The talks, in full</a>
  </div>
</section>"""
    return subpage(c, img, "About", h["line"], body, shot="first-skis-2018",
                   current="about.html", pos="50% 8%", og="about")


NUMBER_WORDS = [
    "no", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
]


def spell(n: int) -> str:
    """Small counts as words, the way the rest of the site sets them."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def road_ahead(c, map_html="") -> str:
    """Where the page lands: one heading and the map.

    The four target cards ran under it until 30 Aug, and the map argued
    the case for 2030 until 31 Aug. Both went at the client's
    instruction, and the heading followed the second of them. Every line
    of that copy is still in the content file.

    The heading then had a second problem she spotted herself: Kodagu is
    on the map and she has never raced there, so "Where she races" was
    wrong about one of the fifteen dots. It counts them instead, and the
    count is computed rather than typed."""
    # One home and fourteen start lines. Counted from the pins rather
    # than typed, so the heading cannot drift from the map: the origin is
    # the pin carrying kind "origin" and the rest is everything else.
    pins = c["internationalFootprint"]
    starts = sum(1 for p in pins if p.get("kind") != "origin")
    head = (c["sections"]["footprint"].get("mapHeading")
            or "One home, {n} start lines").replace("{n}", spell(starts))
    return f"""
<section class="prose-fold" id="road">
  <div class="wrap">
    <div class="prose">
      <h2>{e(head)}</h2>
    </div>
    {map_html}
  </div>
</section>"""


# The winding path. These are the numbers the fallback path is drawn
# from and the numbers each marker is placed at; on a screen wide enough
# for the route, script rebuilds the path in pixels from where the
# markers actually landed, so the two can never disagree.
# A ski track, not a zigzag. The client's note of 31 Aug: mostly
# straight, drifting, "just enough of a curve to give it the feeling of a
# real ski trail". So a slow sine rather than a swing between two
# positions: a centre line, how far it wanders either side, and how many
# years one full wave takes.
JR_XC = 30.0                  # the track's centre line, in percent
JR_XA = 5.0                   # how far it drifts either side
JR_XP = 6.0                   # years per full wave
JR_STEP = 100.0               # vertical distance between one year and the next
JR_PAD = 70.0                 # air above the first marker and below the last

JR_SHOT = "(min-width:900px) 20vw, 88vw"

# The scenery behind the route: her own frames, in the order the journey
# runs. Trees, then trees under snow, then the mountains, then the open
# high ground. Each one is pinned to an edge of the screen and to a
# point down the track. None of them is used as a card on this page, so
# nothing appears twice.
# Three columns, three lists, nothing shared between them. The middle
# and the outer columns used to draw from overlapping lists of different
# lengths, which put the same photograph in two columns side by side; a
# stagger only changes when that happens, not whether. Disjoint makes it
# impossible.
#
# The sort is deliberate too. The middle runs behind the route and is
# all trail and trees with nobody in it, so it reads as texture rather
# than as a figure standing behind the copy; the frames with someone in
# them are out at the edges.
JR_SCENERY_L = ["snow-ridge-line", "lake-mountains", "chile-lake",
                "nz-snowfarm"]
JR_SCENERY_MID = ["track-solo-pines", "track-texture", "classic-tracks"]
JR_SCENERY_R = ["race-forest", "nordic-overlook", "night-training"]

JR_SCENE_SIZES = "34vw"
JR_SCENE_SIZES_MID = "40vw"

# The three numbers that make the scenery continuous, and they have to
# agree with each other or it either gaps or stacks.
#
#   JR_ROW_REM      one year of track. Must match .jr height in the
#                   stylesheet: calc(var(--jr-n) * 17rem).
#   JR_SCENE_REM    one frame.
#   JR_SCENE_STEP   frame top to frame top. The 25rem the frame has over
#                   the step is the crossfade, and the stylesheet puts
#                   the mask stops at exactly that: 25 of 75 is 33.3%.
#
# Because the step and the fade are the same 25rem, one frame's fade-out
# lands exactly on the next one's fade-in. Complementary ramps, so the
# pair composites to less than either at full strength.
JR_ROW_REM = 8.5
JR_SCENE_REM = 90.0
JR_SCENE_STEP = 60.0

# Everything below the timeline that the scenery still has to cover: the
# prose above the route, the map section under it, and the page padding.
# Over-covering is free, because a frame past the host's clip never
# intersects the viewport and so is never fetched.
JR_HOST_EXTRA = 120.0

# How far each column is offset from the left one, as a fraction of the
# step. The lists no longer share a file, so this is only about the three
# columns not changing frame in unison.
JR_SCENE_STAGGER = 0.5
JR_SCENE_MID_STAGGER = 0.25


def scenery_layer(img, rows: int) -> str:
    """Three columns of weather behind the page.

    Each column has its own list and the three share nothing, so the
    same photograph can never appear in two of them at once. Every
    column is stepped so one frame's fade-out lands on the next one's
    fade-in, and the three are offset from each other so they do not
    change frame in unison.
    """
    tall = JR_ROW_REM * rows + JR_HOST_EXTRA
    scenes = []
    # From one frame above the host. The middle and right columns are
    # staggered below the left, so starting at zero left the top of the
    # page thin: sampling coverage every sixty pixels put the right
    # column at 0 and the middle at 0.09 for the first few hundred.
    k = -1
    while True:
        top = k * JR_SCENE_STEP - JR_SCENE_STEP * 0.4
        if top >= tall:
            break
        scenes.append((JR_SCENERY_L[k % len(JR_SCENERY_L)], "l",
                       top, JR_SCENE_SIZES))
        scenes.append((JR_SCENERY_MID[k % len(JR_SCENERY_MID)], "c",
                       top + JR_SCENE_STEP * JR_SCENE_MID_STAGGER,
                       JR_SCENE_SIZES_MID))
        scenes.append((JR_SCENERY_R[k % len(JR_SCENERY_R)], "r",
                       top + JR_SCENE_STEP * JR_SCENE_STAGGER,
                       JR_SCENE_SIZES))
        k += 1
    return ('<div class="jr-scenery" aria-hidden="true">' + "".join(
        f'<span class="jr-scene" data-edge="{edge}" style="--top:{top:.1f}rem">'
        f'{decor(img, slot, sizes)}</span>'
        for slot, edge, top, sizes in scenes) + "</div>")


# A 43-byte transparent GIF. It is what a narrow screen loads instead
# of a photograph it is never going to show.
BLANK_GIF = ("data:image/gif;base64,"
             "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def decor(img, slot, sizes, gate="(min-width:900px)") -> str:
    """A photograph carrying no information, and only where it is shown.

    No alt and no announcement: the route and the captions say
    everything this page says, and a screen reader being told about a
    forest six times on the way down is noise.

    And no download either, below the gate. display:none is not a
    reliable brake on a lazy image, so the srcset sits behind a media
    condition and the img's own src is a transparent GIF. A narrow
    screen takes the 43 bytes; a wide one never looks at them.
    """
    a = img.by_slot.get(slot)
    if not a:
        return ""
    w, h = a["natural"]
    srcset = ", ".join(f"{img.base}/{a['file']}-{x}.webp {x}w"
                       for x in a["widths"])
    return (f'<picture>'
            f'<source media="{e(gate)}" srcset="{e(srcset)}" '
            f'sizes="{e(sizes)}" type="image/webp">'
            f'<img src="{BLANK_GIF}" alt="" aria-hidden="true" '
            f'width="{w}" height="{h}" loading="lazy" decoding="async">'
            f'</picture>')


def journey_line(c, img) -> str:
    """Her years as a drawn route, a photograph and a line at each stop.

    The shape of her reference: a ski track drifting down the page with
    the years marked along it and their taglines beside them.
    Two things it does not do, both asked for. The photograph and the
    write-up are held back for a click, so the page reads as one line a
    year. And past 2026 the track carries on dashed and fades out,
    because that part is a plan and not a record.

    Every marker is a real button carrying aria-expanded, and the whole
    thing is an ordered list, because a chronology is one.
    """
    t = c["story"].get("timeline") or {}
    ys = t.get("years") or []
    if not ys:
        return ""

    n = len(ys)
    total = JR_PAD * 2 + JR_STEP * (n - 1)

    def px(i):
        # The drift, sampled a year at a time. Consecutive years move a
        # few per cent at most, so the cubic through them reads as a
        # track wandering down a slope rather than a line changing its
        # mind every row.
        return JR_XC + JR_XA * math.sin(2.0 * math.pi * i / JR_XP)

    def py(i):
        return JR_PAD + JR_STEP * i

    def run(a, z):
        """Node a to node z as S-bends, handles half a step long.

        Vertical handles mean the curve leaves one marker straight down
        and arrives at the next straight down, so both halves of every
        bend match and the join is invisible.
        """
        d = f"M{px(a):.1f},{py(a):.1f}"
        for i in range(a, z):
            h = JR_STEP * 0.5
            d += (f" C{px(i):.1f},{py(i) + h:.1f} "
                  f"{px(i + 1):.1f},{py(i + 1) - h:.1f} "
                  f"{px(i + 1):.1f},{py(i + 1):.1f}")
        return d

    last_past = max((i for i, y in enumerate(ys)
                     if y.get("kind") != "ahead"), default=n - 1)

    paths = f'<path class="jr-run" d="{run(0, last_past)}"/>'
    if last_past < n - 1:
        # The dashes start at the last year that happened, so the change
        # of line lands on 2026 and not in the gap after it.
        paths += (f'<path class="jr-run jr-ahead" '
                  f'd="{run(last_past, n - 1)}"/>')
    tx, ty = px(n - 1), py(n - 1)
    paths += (f'<path class="jr-tail" d="M{tx:.1f},{ty:.1f} '
              f'C{tx:.1f},{ty + 34:.1f} 50,{ty + 28:.1f} '
              f'50,{ty + JR_PAD:.1f}"/>')

    items = []
    marked = False
    for i, y in enumerate(ys):
        ahead = y.get("kind") == "ahead"
        # The first two markers have no room above them and the last two
        # none below, so their panels anchor to their own edge.
        vpos = "top" if i < 2 else ("bottom" if i >= n - 2 else "mid")
        pid = f"jr-p-{e(y['year'])}"

        # Back in the panel, where it was before 31 Aug. The page is a
        # year and a line; the frame and the write-up wait for a click.
        shot = ""
        if y.get("image"):
            shot = ('<figure class="jr-pop-shot">'
                    + img.tag(y["image"], JR_SHOT) + "</figure>")
        where = f' &middot; {e(y["place"])}' if y.get("place") else ""
        # Said once, on the first year that has not happened, because a
        # line going dashed under it is a convention and not a caption.
        note = ""
        if ahead and not marked and t.get("aheadNote"):
            marked = True
            note = f'<span class="jr-ahead-note">{e(t["aheadNote"])}</span>'

        items.append(f"""
      <li class="jr-node" data-vpos="{vpos}"
          data-kind="{'ahead' if ahead else 'past'}" data-lit="false"
          style="--x:{px(i):.2f}%;--y:{py(i) / total * 100:.3f}%">
        <button class="jr-hit" type="button" aria-expanded="false"
                aria-controls="{pid}">
          <span class="jr-card">{note}
            <span class="jr-year">{e(y['year'])}</span>
            <span class="jr-line">{e(y.get('line') or '')}</span>
          </span>
        </button>
        <div class="jr-pop" id="{pid}" role="group"
             aria-label="{e(y['year'])} in detail">
          {shot}
          <div class="jr-pop-copy">
            <p class="caption jr-pop-where">{e(y['year'])}{where}</p>
            <h3>{e(y.get('title') or '')}</h3>
            <p>{e(y.get('detail') or '')}</p>
          </div>
        </div>
        <span class="jr-dot" aria-hidden="true"></span>
      </li>""")

    return f"""
<section class="prose-fold jr-fold" id="years">
  <div class="wrap">
    <div class="prose">
      <h2 class="jr-head">{e(t.get('heading') or '')}</h2>
    </div>
    <div class="jr" style="--jr-n:{n};--jr-xc:{JR_XC}%">
      <svg class="jr-path" viewBox="0 0 100 {total:.0f}"
           preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="jr-fade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" class="jr-fade-a"/>
            <stop offset="1" class="jr-fade-b"/>
          </linearGradient>
          <clipPath id="jr-clip">
            <rect class="jr-clip-r" x="-10" y="0" width="120"
                  height="{total:.0f}"/>
          </clipPath>
        </defs>
        <g clip-path="url(#jr-clip)">{paths}</g>
      </svg>
      <ol class="jr-nodes">{''.join(items)}</ol>
      {f'<p class="jr-tail-note caption">{e(t["tailNote"])}</p>'
       if t.get('tailNote') else ''}
    </div>
  </div>
</section>"""


def journey_page(c, img):
    # The scenery is a page-level backdrop now rather than a decoration
    # inside the timeline, so everything below the header shares a host
    # it can be positioned against and clipped by.
    body = (
        '<div class="jr-host">'
        + scenery_layer(img, len(c["story"].get("timeline", {})
                                 .get("years") or []))
        + journey_line(c, img)
        # One heading, not two. The map and the target cards were two
        # sections both about what comes next, and after the client
        # renamed the map to The road to 2030 the page carried that
        # heading twice.
        + road_ahead(c, route_map(c))
        + "</div>"
    )
    return subpage(c, img, c["sections"]["journey"]["title"],
                   "A journey across continents, seasons, and start lines.", body,
                   shot="ridge-sunrise",
                   current="journey.html", pos="50% 62%", og="journey")


def route_map(c) -> str:
    """The route, drawn, second attempt after actually looking at the first.

    The first render labelled nine pins at a type size that came out at 22
    CSS pixels, stacked SCHUCHINSK over HARBIN over GULMARG, and let the six
    European dots fuse into one blue smear. Three decisions fix it, made by
    eye against the rendered page rather than by hope:

    The frame crops to her world, longitude -85 to 145 and latitude -45 to
    70, which spends no width on the Pacific and makes every pin a third
    larger for free.

    Europe is named as one thing. Seven venues sit inside a circle a few
    units wide, and seven leader lines in that space is a diagram of string.
    A ring marks the cluster and one label counts it; the fourteen names are
    all listed under the map in racing order, so nothing is lost.

    Labels are 2.8 units, hand-placed, with the collisions checked on
    screen: the eastern pair stack vertically instead of overwriting each
    other, and Chile's two venues share one label because their dots touch.
    """
    w = json.loads((CONTENT / "worldmap.json").read_text(encoding="utf-8"))
    lat_top = w["latTop"]
    pts = {p["id"]: p for p in c["internationalFootprint"]}

    def xy(pid):
        p = pts[pid]
        return p["lon"] + 180.0, lat_top - p["lat"]

    # No connecting line. Her route doubles back across continents, so drawn
    # honestly it reads as string rather than a journey; the client called it
    # odd and was right. The story lives in the order instead: the pins
    # appear one at a time, Kodagu first and Chile near the end, which is the
    # same narrative without the geometry.
    dots = "".join(
        f'<circle cx="{xy(p["id"])[0]:.1f}" cy="{xy(p["id"])[1]:.1f}" r="1.6" '
        f'class="pin" data-stop="{i}"/>'
        for i, p in enumerate(c["internationalFootprint"])
    )
    # dx, dy, anchor per label, tuned against the render
    labels = [
        ("kodagu", 3.5, 4.5, "start", "Kodagu"),
        ("gulmarg", 3.5, -1.5, "start", "Gulmarg"),
        ("schuchinsk", 0, -3.5, "middle", "Schuchinsk"),
        ("harbin", 0, 5.5, "middle", "Harbin"),
        # Beside its pin. Above, its ascender crossed the frame at 70N;
        # below, it ran into the Scandinavian group label.
        ("akureyri", -3.5, 1.0, "end", "Akureyri"),
        ("corralco", 3.5, 1.0, "start", "Chile"),
        ("snowfarm", -3.5, 1.0, "end", "New Zealand"),
        # Alone out east, so it is labelled where it stands.
        ("ruka", 3.5, 1.0, "start", "Ruka"),
    ]
    texts = "".join(
        f'<text x="{xy(pid)[0] + dx:.1f}" y="{xy(pid)[1] + dy:.1f}" '
        f'text-anchor="{a}">{e(t)}</text>'
        for pid, dx, dy, a, t in labels
    )

    # The two European groups. Three venues each, inside about three units
    # of map, which is closer than a label can be placed. One leader out to
    # open water per group and a label naming all three: every place is on
    # the map by name, and there are two lines rather than six.
    #
    #   ids            the venues in the group, in the order the label reads
    #   lx, ly, anchor where the label sits, tuned against the render
    #   fx, fy         where the leader leaves the label
    clusters = [
        (["trondheim", "lygna", "idre"], 168.0, 26.5, "end", 170.0, 25.6),
        (["davos", "seefeld", "planica"], 191.0, 46.5, "middle", 191.0, 45.0),
    ]
    leads = ""
    for ids, lx, ly, anc, fx, fy in clusters:
        pts_ = [xy(i) for i in ids]
        cx_ = sum(q[0] for q in pts_) / len(pts_)
        cy_ = sum(q[1] for q in pts_) / len(pts_)
        # Stop the leader short of the dots rather than into them.
        vx_, vy_ = cx_ - fx, cy_ - fy
        d_ = (vx_ ** 2 + vy_ ** 2) ** 0.5 or 1.0
        ex_, ey_ = cx_ - vx_ / d_ * 3.4, cy_ - vy_ / d_ * 3.4
        name = " &middot; ".join(
            pts[i]["place"] for i in ids)
        leads += (f'<path class="map-lead" d="M{fx:.1f},{fy:.1f} '
                  f'L{ex_:.1f},{ey_:.1f}"/>'
                  f'<text x="{lx:.1f}" y="{ly:.1f}" '
                  f'text-anchor="{anc}">{name}</text>')
    # No destination and no planned stops, from 31 Aug. The map was doing
    # two jobs: marking where she has raced, and arguing a case about
    # 2030 with a ringed point in the Alps, a leader naming La Clusaz and
    # three hollow rings for stops she has not made. The second job went
    # at the client's instruction. The lines went the same way on the
    # same day, for the same reason: the places are the content.

    order = [p["place"] for p in c["internationalFootprint"]]
    roll = " &middot; ".join(order)
    # crop: lon -85..178 -> x 95..358, lat 70..-50. It ran to 145 east
    # and stopped in the Pacific short of New Zealand, and to 45 south,
    # which cut the bottom off the Snow Farm at 44.6.
    vx, vw = 95, 263
    vy, vh = lat_top - 70, 120
    return f"""
    <figure class="route-map" id="route">
      <svg viewBox="{vx} {vy:.0f} {vw} {vh:.0f}" role="img"
           aria-label="World map marking the fifteen places she has raced
           or trained, from Ruka inside the Arctic Circle to the Snow Farm
           in New Zealand. The three Scandinavian venues and the three
           Alpine ones sit too close to label separately and are named as
           two groups; all fifteen are listed under the map.">
        <path d="{w['path']}" class="land"/>
        <g class="past">{dots}{texts}{leads}</g>
      </svg>
      <figcaption class="caption">{roll}</figcaption>
    </figure>"""


def record_fold(c) -> str:
    """Where the journey lands: the record, at the foot of the story.

    A heading, a count, and the rows. No sentences, per the client's note
    that the two divisions should carry numerically.
    """
    rows = [r for r in c["results"]["rows"] if r.get("medal")]
    intl = [r for r in rows if "international" in r.get("tags", [])]
    natl = [r for r in rows if "international" not in r.get("tags", [])]

    def grouped(rs):
        """One line per campaign, not one per medal.

        Twenty national rows rendered as a ledger and the client called it a
        crawl. Grouped by event and year they read as a record: the campaign
        on the left, its medals as counted dots on the right."""
        order, groups = [], {}
        for r in rs:
            key = (str(r["year"]), r["event"], r["place"])
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(r["medal"])
        out = []
        for year, event, place in order:
            meds = groups[(year, event, place)]
            counts = {}
            for m in meds:
                counts[m] = counts.get(m, 0) + 1
            dots = "".join(
                f'<span class="medal" data-medal="{k}"><i></i><b>{v}</b>{k}</span>'
                for k in ("gold", "silver", "bronze") if (v := counts.get(k))
            )
            out.append(
                f'<tr><td class="caption">{e(year)}</td>'
                f'<td><b>{e(event)}</b><span>{e(place)}</span></td>'
                f'<td class="c-meds">{dots}</td></tr>'
            )
        return f'<table class="medals"><tbody>{"".join(out)}</tbody></table>'

    # Her item 7: the tables run the full content width, the heading
    # keeps the prose measure.
    return f"""
<section class="prose-fold" id="records">
  <div class="wrap">
    <div class="prose"><h2>International <span class="count">{len(intl)}</span></h2></div>
    {grouped(intl)}
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap">
    <div class="prose"><h2>National <span class="count">{len(natl)}</span></h2></div>
    {grouped(natl)}
  </div>
</section>"""


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

    # No sentences. The client asked for the two divisions to carry
    # numerically, so each block is a heading, a count, and the rows.
    m = medals(c)
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <h2>International <span class="count">{sum(m['International'].values())}</span></h2>
    {table(intl)}
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap prose">
    <h2>National <span class="count">{sum(m['National'].values())}</span></h2>
    {table(natl)}
  </div>
</section>"""
    return subpage(c, img, "The record", "Every medal, in two divisions.",
                   body, shot="nordic-podium")


def media_page(c, img):
    """Press as cards, not a list of links.

    Each card is the thumbnail the press entry already carries, the
    publication, the year, and the headline. The whole card is the link. Two
    columns, so ten stories read as a page of stories rather than a wall of
    blue text. The fields are `publication` and `title`: the first pass read
    `outlet` and `headline`, which do not exist, so every outlet line
    rendered empty.
    """
    press = []
    for pr in c["press"]:
        head = pr.get("title") or ""
        if not head:
            continue
        outlet = pr.get("publication") or ""
        year = str(pr.get("date") or "")[:4]
        meta = f" {chr(183)} ".join(x for x in (outlet, year) if x)
        url = pr.get("url") or ""
        thumb = ""
        if pr.get("image") and img.get(pr["image"]):
            thumb = (f'<span class="press-shot">'
                     f'{img.tag(pr["image"], "(min-width:760px) 30vw, 90vw")}</span>')
        thumb = ""
        if pr.get("image") and img.get(pr["image"]):
            thumb = (f'<span class="press-shot">'
                     f'{img.tag(pr["image"], "(min-width:760px) 30vw, 90vw")}</span>')
        inner = (f'{thumb}<span class="press-body">'
                 f'<span class="caption">{e(meta)}</span>'
                 f'<b>{e(head)}</b></span>')
        press.append(
            f'<li data-rise><a href="{e(url)}" rel="noopener" target="_blank">{inner}</a></li>'
            if url else f'<li data-rise><p>{inner}</p></li>'
        )
    lib = json.loads((CONTENT / "images.json").read_text(encoding="utf-8"))
    # Each tile is a link to the full frame. The grid crops to 3:4 for order;
    # a click opens the photograph whole, in a lightbox when JavaScript runs
    # and as the plain image file when it does not.
    gallery = "".join(
        f'<a class="tile" href="../assets/img/{a["file"]}-{a["widths"][-1]}.webp" '
        f'data-full data-cap="{e((img.caption(a["slot"]) or "").replace("&middot;", chr(183)))}">'
        f'<span class="tile-shot">{img.tag(a["slot"], TILE_SIZES)}</span>'
        f'<figcaption class="caption">'
        f'{img.caption(a["slot"]) or "From the archive"}</figcaption></a>'
        for a in lib["images"]
        if a.get("rights") == "owned" and a.get("category") in ("race", "training")
    )
    body = f"""
<section class="prose-fold">
  <div class="wrap">
    <div class="prose"><h2>Press</h2></div>
    <ul class="press-grid">{''.join(press)}</ul>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap">
    <div class="prose"><h2>Photographs</h2></div>
    <div class="masonry" style="margin-top:var(--space-md)">{gallery}</div>
  </div>
</section>"""
    return subpage(c, img, "Media",
                   "The papers that told her story, and the archive that shows it.",
                   # A podium snapshot read as an amateur frame at banner
                   # size. This is the one cinematic photograph in the
                   # archive: floodlit night training, dark and lit from
                   # below, and the only banner on the site that is not
                   # daylight on snow. The band lands on the lit group,
                   # which sits at 0.45 to 0.85 of a portrait frame.
                   body, shot="night-training", current="media.html",
                   pos="50% 60%", og="media")


def partnership_page(c, img):
    """Four things and nothing else, to the client's brief of 30 Aug 2026:
    what support funds, who supports her now, a line on each of them, and
    what she is open to. Work with Bhavani closes it.

    Removed with that brief: the coffee-estates standfirst, which the
    homepage already carries in its own words, and the 2030 target block,
    which repeated the Journey page. Both stay in the content file."""
    p = c["partnership"]
    # A mosaic, to the client's reference: pale text tiles and photographic
    # ones in one column flow, with the second area carrying its text over
    # a frame. The photo-only tiles are texture and say nothing the text
    # tiles do not, so they are hidden from screen readers.
    def tile(n, a):
        sl = a.get("image")
        if sl and (img.get(sl) or {}).get("rights") == "owned":
            return (f'<article class="fund fund-shot" data-rise>'
                    f'<span class="fund-img">{img.tag(sl, TILE_SIZES)}</span>'
                    f'<span class="fund-n" aria-hidden="true">{n:02d}</span>'
                    f'<h3>{e(a["title"])}</h3><p>{e(a["body"])}</p></article>')
        return (f'<article class="fund" data-rise>'
                f'<span class="fund-n" aria-hidden="true">{n:02d}</span>'
                f'<h3>{e(a["title"])}</h3><p>{e(a["body"])}</p></article>')

    def plate(t):
        sl = t["slot"]
        tag = img.tag(sl, TILE_SIZES)
        if t.get("pos"):
            tag = tag.replace(f"object-position:{img.focal(sl)}",
                              f"object-position:{t['pos']}")
        return (f'<figure class="fund fund-plate" aria-hidden="true" '
                f'data-rise>{tag}</figure>')

    plain = [
        plate(t) for t in p.get("tileShots", [])
        if (img.get(t["slot"]) or {}).get("rights") == "owned"
    ]
    rows = [tile(n, a) for n, a in enumerate(p.get("areas", []), 1)]
    # Interleaved so no column is all type or all photograph.
    order = [rows[0]] + plain[:1] + rows[1:3] + plain[1:2] + rows[3:]
    areas = "".join(order)
    # Her brief: show the partners she has, labelled, and no others. The
    # names sit here with the role each one actually plays, which is the
    # honest version of a logo band.
    support = "".join(
        f'<article class="backer backer-row" data-rise>'
        f'<span class="backer-mark">'
        f'<img src="../assets/img/partners/{e(x["logo"])}" '
        f'alt="{e(x["name"])}" loading="lazy" decoding="async"></span>'
        f'<div><h3>{e(x["name"])}</h3>'
        f'<p>{e(x.get("role") or x.get("kind") or "")}</p></div></article>'
        for x in (p.get("current") or {}).get("list", [])
        if x.get("logo")
    )
    # Rights are settled before a photograph is published, here as
    # everywhere else; a category without an owned frame still lists.
    def opt(x):
        sl = x.get("image")
        shot = ""
        if sl and (img.get(sl) or {}).get("rights") == "owned":
            shot = (f'<span class="opt-shot">{img.tag(sl, OPT_SIZES)}</span>')
        cls = " opt-shot-tile" if shot else ""
        return f'<li class="opt{cls}">{shot}<span>{e(x["label"])}</span></li>'

    open_to = "".join(opt(x) for x in p.get("openTo", []))
    body = f"""
<section class="prose-fold">
  <div class="wrap">
    <div class="prose"><h2>What support funds</h2></div>
    <div class="funds">{areas}</div>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="current">
  <div class="wrap prose">
    <h2>Current support</h2>
    <div class="backers backers-stack">{support}</div>
  </div>
</section>
<section class="prose-fold" id="open">
  <div class="wrap">
    <div class="prose">
      <h2>Open to</h2>
      <p>She is actively looking for partners in these areas for the
      seasons between here and 2030.</p>
    </div>
    <ol class="open-tiles">{open_to}</ol>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="contact">
  <div class="wrap prose">
    <h2>Work with Bhavani</h2>
    <p>Partner with Bhavani across sport, storytelling and the pathway
    she is building in India.</p>
    <a class="btn" data-on="accent"
       href="contact.html?topic=Sponsorship">Start the conversation</a>
  </div>
</section>"""
    return subpage(c, img, "Partnership",
                   # A banner line should set the horizon, not index the
                   # page. Four seasons is the figure the site already
                   # uses for the run to 2030. The second clause is gone:
                   # 'the people who get her there' was a dangling
                   # fragment, and 'get her there' quietly promised an
                   # arrival that is not settled.
                   "The four seasons between here and the 2030 Games.",
                   body, shot="holmenkollen", current="partnership.html",
                   # Measured against the frame rather than guessed. The
                   # banner shows a 14% band of a portrait source, and
                   # with object-position p the band starts at 0.858p. Her
                   # head top is at 38%, shoulders 45%, the INDIA wordmark
                   # 52%. An anchor of 38% put the band ON her head and
                   # showed nothing else; 44% starts it at 0.377, so her
                   # head sits at the top edge and the band runs down her
                   # back to the wordmark.
                   pos="52% 44%", og="partnership")


def enquiry_block(c, heading="Work with Bhavani") -> str:
    """The one form, shared by Partnership and Work with me.

    Same pipeline V1 ships: POST to /api/enquiry (the Cloudflare Pages
    function backed by Resend) with a mailto fallback if the function is
    missing, unconfigured or offline. Organisation is optional and the
    function already accepts it; the topics match her brief word for word.
    Each required field carries its own error line, wired to aria-invalid
    by the script, so a miss is named at the field and not only in the
    general note."""
    return f"""
<section class="prose-fold" id="contact">
  <div class="wrap prose">
    <h2>{e(heading)}</h2>
    <p>Speaking, sponsorship, media and brand collaborations. One form,
    straight to her.</p>
    <form class="enquiry" id="enquiry" method="post" action="/api/enquiry" novalidate>
      <div class="field">
        <label class="caption" for="f-name">Name</label>
        <input id="f-name" name="name" type="text" autocomplete="name">
      </div>
      <div class="field">
        <label class="caption" for="f-org">Organisation
          <span class="opt">optional</span></label>
        <input id="f-org" name="organisation" type="text"
          autocomplete="organization">
      </div>
      <div class="field">
        <label class="caption" for="f-email">Email</label>
        <input id="f-email" name="email" type="email" autocomplete="email"
          required aria-describedby="f-email-err">
        <p class="field-err caption" id="f-email-err" hidden>An email address
        is needed for the reply.</p>
      </div>
      <div class="field">
        <label class="caption" for="f-topic">Topic</label>
        <select id="f-topic" name="topic">
          <option>Sponsorship</option>
          <option>Speaking</option>
          <option>Media</option>
          <option>Brand collaboration</option>
          <option>Other</option>
        </select>
      </div>
      <div class="field field-wide">
        <label class="caption" for="f-msg">Message</label>
        <textarea id="f-msg" name="message" rows="5" required
          aria-describedby="f-msg-err"></textarea>
        <p class="field-err caption" id="f-msg-err" hidden>A line or two about
        what you have in mind.</p>
      </div>
      <!-- honeypot, same contract as the function expects -->
      <input class="vh" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
      <div class="field-wide">
        <button class="btn" data-on="accent" type="submit">Send enquiry</button>
        <p class="caption" id="enquiry-note" aria-live="polite"></p>
      </div>
    </form>
  </div>
</section>"""


def parse_post(path):
    """Front-matter and markdown, same file format V1's journal reads.

    Her writing space is a folder of markdown files. She writes or dictates a
    post, it lands in content/journal as a dated file, and both sites can
    carry it; nothing about the format belongs to either build. Files with
    `draft: true` stay off the public page until she has made the words hers.
    """
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None
    try:
        _, fm, body = raw.split("---", 2)
    except ValueError:
        return None
    meta = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return {
        "slug": path.stem,
        "title": meta.get("title", path.stem),
        "date": meta.get("date", ""),
        "summary": meta.get("summary", ""),
        "image": meta.get("image", ""),
        "draft": meta.get("draft", "false").lower() == "true",
        "body": body.strip(),
    }


def load_posts():
    if not JOURNAL_DIR.exists():
        return []
    posts = [
        p for p in (parse_post(f) for f in sorted(JOURNAL_DIR.glob("*.md"))
                    if not f.name.startswith("_"))
        if p and not p["draft"]
    ]
    return sorted(posts, key=lambda x: x["date"], reverse=True)


def pretty_date(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        months = ("January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December")
        return f"{d} {months[m - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def achievements_page(c, img):
    """Her Achievements destination: the medal tables that used to close
    Journey, and the official FIS trail for anyone verifying them."""
    fis = c["hero"]["ctaTertiary"]["href"]
    # Her record down the middle with photographs either side, the way the
    # client's reference lays out a story page. The rails are decorative
    # duplicates of nothing: they carry no information the tables do not,
    # so they are hidden from screen readers and out of the tab order, and
    # they only appear where there is real margin to put them in.
    def rail(slots, side):
        shots = "".join(
            f'<figure class="rail-shot" data-rise style="--n:{n}">'
            f'{img.tag(sl, "20vw")}</figure>'
            for n, sl in enumerate(slots)
            if (img.get(sl) or {}).get("rights") == "owned"
        )
        return f'<aside class="rail rail-{side}" aria-hidden="true">{shots}</aside>'

    # The summary band runs clean across the page: the client does not want
    # photographs beside the figures. The rails start at the tables, so
    # nothing is in the margins until you have scrolled past the summary,
    # and each frame is lazy-loaded and revealed on arrival rather than
    # fetched with the page.
    body = (
        record_slabs(c, img, head=False, link=False)
        + '<div class="rail-layout">'
        # Ordered to match the tables beside them: the three international
        # frames come first, then the three from home. Reading down the
        # page with the right rail offset, that is Corralco, Trondheim,
        # Harbin, then Khelo India, Gulmarg, Gulmarg.
        + rail(["chile-corralco", "flag-harbin", "podium-gulmarg-2023"], "left")
        + '<div class="rail-main">'
        + record_fold(c)
        + "</div>"
        + rail(["race-worldcup", "contingent-2021", "team-gulmarg"], "right")
        + "</div>"
    ) + f"""
<section class="prose-fold" id="official">
  <div class="wrap prose">
    <h2>The official record</h2>
    <p>Every FIS-scored start she has taken is published on her athlete
    page.</p>
    <a class="btn" data-on="accent" href="{e(fis)}" rel="noopener"
       target="_blank">Open her FIS profile</a>
  </div>
</section>"""
    return subpage(c, img, "Achievements",
                   "A record of medals, milestones, and verified results.", body,
                   shot="khelo-medals", current="achievements.html",
                   # The library focal sits at 31%, which is her eye line.
                   # A banner this wide shows only a fifth of a portrait
                   # source, so 31% starts the band across her face and
                   # cuts the cap off. Her head sits at 19-24%; anchoring
                   # at 20% keeps it whole with air above it.
                   pos="50% 20%", og="achievements")


def speaking_page(c, img):
    """Built to the client's reference: an outlined headline over the
    photograph, then six photographic cards staggered in two columns with
    the word set over the frame, and one call to action at the end.

    Her eight audiences are folded into the cards rather than listed on
    their own, so each card says what it is about and who it is for."""
    sp = c.get("speaking") or {}
    cards = "".join(
        f'<article class="say" data-rise>'
        f'<span class="say-shot">{img.tag(t["image"], SKILL_SIZES)}</span>'
        f'<div class="say-body">'
        f'<h2>{e(t["word"])}</h2>'
        f'<p>{t.get("line") or ""}</p>'
        f'<p class="say-for caption">{e(t.get("audience") or "")}</p>'
        f'</div></article>'
        for t in sp.get("skills", [])
        if (img.get(t.get("image")) or {}).get("rights") == "owned"
    )
    # The band sits between the header and the cards, so its job is to set
    # the cards up. The first pass restated her journey, which the
    # homepage hero already says and which tells a booker nothing about
    # what they are buying. This names the trade instead: her decade, and
    # what it is worth to the room she is standing in.
    inv = sp.get("invite") or {}
    body = f"""
<section class="statement-band">
  <div class="wrap">
    <p class="head-stack" data-rise>
      <span class="head-out">What she brings</span>
      <span class="head-in">Six things a decade on snow is worth to a
        room<i aria-hidden="true">.</i></span></p>
  </div>
</section>
<section class="prose-fold">
  <div class="wrap">
    <div class="says">{cards}</div>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="book">
  <div class="wrap prose">
    <h2>{e(inv.get('heading') or 'What to invite her for')}</h2>
    <p class="book-body">{e(inv.get('body') or '')}</p>
    <a class="btn" data-on="accent"
       href="contact.html?topic=Speaking">Invite Bhavani to speak</a>
  </div>
</section>"""
    return subpage(c, img, "Speaking", sp.get("lede") or "", body,
                   shot="flag-almaty", current="speaking.html", og="speaking",
                   pos="58% 44%")


def contact_page(c, img):
    """Her ninth destination, renamed Contact on the 26 Aug structure:
    one route in for everything."""
    return subpage(c, img, "Contact",
                   "Speaking, sponsorship, media and brand collaborations.",
                   enquiry_block(c), shot="lake-mountains",
                   current="contact.html", og="contact")


def journal_page(c, img, posts):
    """Her space. A list of entries in her own voice, newest first.

    While the list is empty the page says so plainly instead of pretending:
    two entries exist as drafts and go live the day she signs off the words.
    """
    if posts:
        items = "".join(
            f"""<a class="entry" href="journal-{e(p['slug'])}.html" data-rise>
          <span class="caption">{e(pretty_date(p['date']))}</span>
          <h2>{e(p['title'])}</h2>
          <p>{e(p['summary'])}</p>
        </a>"""
            for p in posts
        )
        body = f'<section class="prose-fold"><div class="wrap prose">{items}</div></section>'
    else:
        body = """
<section class="prose-fold">
  <div class="wrap prose">
    <p>Race reports, training notes and the road to 2030, written from
    inside the season. The first entries land here soon.</p>
  </div>
</section>"""
    return subpage(c, img, "Journal", "The season, written from inside it.",
                   body, shot="classic-tracks", current="journal.html",
                   pos="50% 40%", og="journal")


def journal_post_page(c, img, post):
    md = MarkdownIt()
    hero = ""
    if post["image"] and img.get(post["image"]):
        hero = post["image"]
    body = f"""
<div class="read-progress" aria-hidden="true"><i id="read-bar"></i></div>
<article class="prose-fold">
  <div class="wrap prose post">
    <p class="caption">{e(pretty_date(post['date']))}</p>
    {md.render(post['body'])}
    <p><a class="link-out" href="journal.html">All entries</a></p>
  </div>
</article>"""
    return subpage(c, img, post["title"], post["summary"], body,
                   shot=hero or "classic-tracks", current="journal.html")


def sync_assets() -> None:
    """At the root the pages ask for `assets/css/v2.css`, and V2's stylesheet
    lives under `v2/assets`. Mirror the parts V2 owns into the shared tree:
    its CSS, its script, the display font and the share cards. `assets/img`
    is already shared and is left alone."""
    import shutil

    src = ROOT / "v2" / "assets"
    dst = ROOT / "assets"
    for rel in ("css/tokens.css", "css/v2.css", "js/v2.js",
                "fonts/black-rusher.woff2", "favicon.svg"):
        f = src / rel
        if f.exists():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / rel)
    og = src / "og"
    if og.exists():
        shutil.copytree(og, dst / "og", dirs_exist_ok=True)

    # The stylesheet pulls tokens.css in with a bare `@import url(...)`,
    # and that URL carries no version. The page link does: v2.css?v=HASH
    # changes whenever any of the three files change. So a token edit
    # refetched the stylesheet and then reused the cached tokens, and
    # `_headers` caches /assets/* for a year as immutable, which means a
    # colour or a type-scale change could sit invisible on a returning
    # visitor's machine until the cache expired.
    #
    # Measured: after darkening --color-ink-3 and raising --text-xs the
    # rebuilt page still reported 12px at 3.87:1 in the browser while the
    # file on disk said otherwise.
    #
    # Inlining it at the root fixes the versioning and drops a serialised
    # round trip: an @import cannot start until the file importing it has
    # arrived.
    css = dst / "css" / "v2.css"
    tok = dst / "css" / "tokens.css"
    if css.exists() and tok.exists():
        text = css.read_text(encoding="utf-8")
        line = '@import url("tokens.css");'
        if line in text:
            css.write_text(
                text.replace(line, tok.read_text(encoding="utf-8"), 1),
                encoding="utf-8")


def main() -> int:
    if AT_ROOT:
        # Before fingerprinting, or the hash is taken over the old files.
        sync_assets()
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
    (OUT / "achievements.html").write_text(achievements_page(c, img), encoding="utf-8")
    (OUT / "journey.html").write_text(journey_page(c, img), encoding="utf-8")
    (OUT / "media.html").write_text(media_page(c, img), encoding="utf-8")
    (OUT / "partnership.html").write_text(partnership_page(c, img), encoding="utf-8")
    (OUT / "speaking.html").write_text(speaking_page(c, img), encoding="utf-8")
    (OUT / "contact.html").write_text(contact_page(c, img), encoding="utf-8")
    (OUT / "404.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="only light">
<title>Page not found | Bhavani Thekkada</title>
<link rel="icon" href="{ABS}/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="{ABS}/css/v2.css?v={fingerprint()}">
</head>
<body>
<main id="main" class="panel" data-ground="paper" style="min-height:100svh">
  <div class="wrap panel-body">
    <p class="caption">404</p>
    <h1>Off the course</h1>
    <p class="sub">This page does not exist. The site does.</p>
    <div class="masthead-cta">
      <a class="btn" data-on="accent" href="/v2/index.html">Back to the start</a>
      <a class="btn" href="/v2/journey.html">The journey</a>
      <a class="btn" href="/v2/contact.html">Contact</a>
    </div>
  </div>
</main>
</body>
</html>
""", encoding="utf-8")
    posts = load_posts()
    (OUT / "journal.html").write_text(journal_page(c, img, posts), encoding="utf-8")
    for post in posts:
        (OUT / f"journal-{post['slug']}.html").write_text(
            journal_post_page(c, img, post), encoding="utf-8")

    m = medals(c)
    where = "root" if AT_ROOT else "v2/ "
    print(f"{where}  8 pages   index {out.stat().st_size / 1024:.1f} KB")
    print("  benchmark  rogerfederer.com  ·  6 panels + sponsor band + split")
    print(f"  medals     international {sum(m['International'].values())}"
          f"  national {sum(m['National'].values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
