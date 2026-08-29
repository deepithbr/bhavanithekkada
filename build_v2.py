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
import re
import pathlib

from markdown_it import MarkdownIt

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

# The five pages the client asked for, and no more: home, about, the
# journey with the record at the end of it, media, partnership. Records is
# not a destination of its own; it is where the journey lands.
# Her eight destinations, 26 Aug: Home is the wordmark, Contact is the
# pill at the end of the row.
# Home leaves the row: her name in the bar is the way back, as on the
# reference. Contact stays the pill at the row's end.
NAV = [
    ("Story", "journey.html"),
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
    "closer": "holmenkollen",
}

# The four photographs in the media row. Journey takes its four from the story
# beats, so it always matches whatever the journey page shows.
MEDIA_TILES = ["khelo-medals", "chile-corralco", "race-worldcup", "nordic-overlook"]

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
    # One phrase in the title can carry a drawn underline. Escaped first,
    # then wrapped, so the marker can never smuggle markup through.
    marked = e(title)
    if mark:
        # The phrase takes its own line and a drawn stroke underneath: a
        # path rather than a rule, because a ruled underline reads as a
        # link and this is meant to look scratched into the snow. It draws
        # itself when the panel comes into view; the script sets the flag.
        marked = marked.replace(
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
    <p class="backing-more caption" data-rise>
      <a href="partnership.html">Partnership options &rarr;</a></p>
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
    return f"""
<section class="panel" data-size="hero">
  <div class="panel-shot">{tag}</div>
  <div class="wrap panel-body hero-min" data-rise>
    <h1 class="hero-punch"><span class="punch-eyebrow">Pioneering</span><span
      class="punch-big"><span class="hl">India&rsquo;s</span> path</span><span
      class="punch-big">on snow</span></h1>
    {chip}
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


def levels_band(c, link=True) -> str:
    """Level of competition: her three start-level cards verbatim, plus
    the two medal counts computed from the results rows so the band can
    never disagree with the tables on the Achievements page."""
    cards = levels_data(c)
    lis = "".join(
        f'<article class="level" data-rise>'
        f'<span class="level-n tally-total">{e(x["n"])}</span>'
        f'<h3>{e(x["k"])}</h3><p class="caption">{e(x["s"])}</p></article>'
        for x in cards
    )
    more = ('<p class="caption" style="margin-top:var(--space-md)">'
            '<a href="achievements.html">The full record, race by race '
            '&rarr;</a></p>') if link else ""
    return f"""
<section class="prose-fold" data-ground="ice" id="level">
  <div class="wrap">
    <div class="prose">
      <p class="caption">The record</p>
      <h2>Level of competition</h2>
    </div>
    <div class="levels">{lis}</div>
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
    fmts = "".join(
        f'<li class="fmt" data-rise>'
        f'<span class="fmt-n">{n + 1:02d}</span>'
        f'<p class="fmt-kind caption">{e(d.get("kind") or "")}</p>'
        f'<h3>{e(d["name"])}</h3>'
        f'<p>{e(d.get("note") or "")}</p></li>'
        for n, d in enumerate(ds[:4])
    )
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
    <ol class="sport-formats">{fmts}</ol>
  </div>
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
<meta property="og:image" content="{ORIGIN}/v2/assets/og/index.jpg">
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
{who_she_is(c, img)}
{sport_fold(c, img)}
{panel(img, SHOTS['closer'],
       'Join me on my journey to the 2030 French Alps Olympic Winter Games',
       'Cross-country skiing',
       ('View journey', 'journey.html'), pos='50% 46%',
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
<meta property="og:image" content="{ORIGIN}/v2/assets/og/{e(og or 'index')}.jpg">
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


def road_ahead(c) -> str:
    """The timeline keeps going. Her brief asks Journey to run past the
    present into the targets, and to close on the section she titled
    Beyond the Finish Line, so both live here rather than only on the
    partnership page."""
    t = c.get("targets") or {}
    cards = "".join(
        f'<article class="step step-future" data-rise>'
        f'<div class="step-copy">'
        f'<span class="ghost-year" aria-hidden="true">{e(i["year"])}</span>'
        f'<p class="caption">{e(i["year"])}</p>'
        f'<h3>{e(i["title"])}</h3><p>{e(i["line"])}</p></div></article>'
        for i in t.get("items", [])
    )
    bf = c.get("beyondFinishLine") or {}
    return f"""
<section class="prose-fold" id="road">
  <div class="wrap">
    <div class="prose">
      <h2>{e(t.get('kicker') or 'The road to 2030')}</h2>
      <p>{e(t.get('note') or '')}</p>
    </div>
    <div class="steps steps-future">{cards}</div>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="beyond">
  <div class="wrap prose">
    <h2>{e(bf.get('kicker') or 'Beyond the finish line')}</h2>
    <p class="pull">{e(bf.get('lede') or '')}</p>
    <p>{e(bf.get('line') or '')}</p>
  </div>
</section>"""


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
  <article class="step" id="beat-{e(b['id'])}" data-rise>
    {shot}
    <div class="step-copy">
      <span class="ghost-year" aria-hidden="true">{e(str(b['year'])[:4])}</span>
      <p class="caption">{e(b['year'])}</p>
      <h2>{e(b['heading'])}</h2>
      <p>{e(b['body'])}</p>
    </div>
  </article>""")
    body = (
        '<section class="prose-fold"><div class="wrap steps">'
        + "".join(items)
        + "</div></section>"
        + route_map(c)
        + road_ahead(c)
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

    europe = ["planica", "idre", "seefeld", "lygna", "trondheim", "ruka", "davos"]
    ex = sum(xy(p)[0] for p in europe) / len(europe)
    ey = sum(xy(p)[1] for p in europe) / len(europe)
    # The ring is measured, not guessed: radius reaches the farthest of the
    # seven plus clearance. The first guess of 7.5 left Trondheim and Ruka
    # sitting outside their own circle, visible the moment it rendered.
    er = max(
        ((xy(p)[0] - ex) ** 2 + (xy(p)[1] - ey) ** 2) ** 0.5 for p in europe
    ) + 2.2

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
        ("akureyri", -3.5, -2.5, "end", "Akureyri"),
        ("corralco", 3.5, 1.0, "start", "Chile"),
    ]
    texts = "".join(
        f'<text x="{xy(pid)[0] + dx:.1f}" y="{xy(pid)[1] + dy:.1f}" '
        f'text-anchor="{a}">{e(t)}</text>'
        for pid, dx, dy, a, t in labels
    )
    cluster = (
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{er:.1f}" class="ring"/>'
        f'<text x="{ex:.1f}" y="{ey + er + 3.5:.1f}" text-anchor="middle">'
        f"The European winter &middot; 7 venues</text>"
    )
    order = [p["place"] for p in c["internationalFootprint"]]
    roll = " &middot; ".join(order)
    # crop: lon -85..145 -> x 95..325, lat 70..-45
    vx, vw = 95, 230
    vy, vh = lat_top - 70, 115
    return f"""
<section class="prose-fold" data-ground="ice" id="route">
  <div class="wrap">
    <div class="prose"><h2>The route</h2></div>
    <figure class="route-map">
      <svg viewBox="{vx} {vy:.0f} {vw} {vh:.0f}" role="img"
           aria-label="World map marking the fourteen places she has raced or trained.">
        <path d="{w['path']}" class="land"/>
        {dots}{cluster}{texts}
      </svg>
      <figcaption class="caption">{roll}</figcaption>
    </figure>
  </div>
</section>"""


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
                   body, shot="podium-gulmarg-2023", current="media.html",
                   pos="50% 26%", og="media")


def partnership_page(c, img):
    p = c["partnership"]
    areas = "".join(
        f'<div class="fact"><dt class="caption">{e(a["title"])}</dt>'
        f'<dd>{e(a["body"])}</dd></div>'
        for a in p.get("areas", [])
    )
    t = c.get("targets", {}).get("finale", {})
    # The season-by-season road lives on Journey only; printing it here
    # too made the two pages repeat each other word for word, which the
    # client flagged. Partnership keeps the target and points across.
    # Her brief: show the partners she has, labelled, and no others. The
    # names sit here with the role each one actually plays, which is the
    # honest version of a logo band.
    support = "".join(
        f'<div class="fact"><dt class="caption">{e(p["name"])}</dt>'
        f'<dd>{e(p.get("role") or p.get("kind") or "")}</dd></div>'
        for p in (c["partnership"].get("current") or {}).get("list", [])
    )
    body = f"""
<section class="prose-fold">
  <div class="wrap prose">
    <p class="pull">From the coffee estates of Kodagu to international
    start lines, this journey has been built across continents and
    seasons. In a sport with limited pathways in India, I became the
    country&rsquo;s first woman to win an international cross-country
    skiing medal &mdash; and I&rsquo;m still building towards what comes
    next.</p>
    <p class="pull-cite caption">Bhavani Thekkada</p>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap">
    <div class="target" data-rise>
      <span class="target-year" aria-hidden="true">2030</span>
      <div class="prose">
        <h2>{e(t.get('title', 'Winter Olympics'))}</h2>
        <p class="pull">{e(t.get('line') or '')}</p>
        <p class="caption">{e(t.get('host') or '')} &middot; {e(t.get('dates') or '')}</p>
      </div>
    </div>
    <p class="caption" style="margin-top:var(--space-md)">
      <a href="journey.html#road">The season-by-season road, on My journey &rarr;</a></p>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap prose">
    <h2>What support funds</h2>
    <dl class="facts">{areas}</dl>
  </div>
</section>
<section class="prose-fold" id="current">
  <div class="wrap prose">
    <h2>Current support</h2>
    <dl class="facts">{support}</dl>
    <h3 style="margin-top:var(--space-lg)">Open to</h3>
    <p>{" &middot; ".join(e(x) for x in c["partnership"].get("openTo", []))}.</p>
  </div>
</section>
<section class="prose-fold" data-ground="ice" id="contact">
  <div class="wrap prose">
    <h2>Work with Bhavani</h2>
    <p>The case is on this page. The conversation starts on one, whatever
    shape the partnership takes.</p>
    <a class="btn" data-on="accent"
       href="contact.html?topic=Sponsorship">Start the conversation</a>
  </div>
</section>"""
    return subpage(c, img, "Partnership",
                   "The plan to 2030, and what support pays for.",
                   body, shot="summit-solo", current="partnership.html",
                   pos="50% 46%", og="partnership")


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
    body = levels_band(c, link=False) + record_fold(c) + f"""
<section class="prose-fold" id="official">
  <div class="wrap prose">
    <h2>The official record</h2>
    <p>Every FIS-scored start she has taken is published on her athlete
    page, independent of this site.</p>
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
    """Athlete, speaker, storyteller: her brief promotes this from a footnote
    on About to a section of its own, with one clear way to book her."""
    sp = c.get("speaking") or {}
    talks = "".join(
        f'<article class="talk" data-rise><span class="talk-n">{n:02d}</span>'
        f'<h3>{e(t["title"])}</h3><p>{e(t.get("body") or "")}</p>'
        f'<p class="caption">{e(t.get("from") or "")}</p></article>'
        for n, t in enumerate(sp.get("themes", []), 1)
    )
    aud = " &middot; ".join(e(a) for a in sp.get("audiences", []))
    body = f"""
<section class="prose-fold">
  <div class="wrap">
    <div class="prose">
      <p class="caption">Athlete &middot; Speaker &middot; Storyteller</p>
      <h2>The talks</h2>
      <p>{e(sp.get('close') or '')}</p>
    </div>
    <dl class="facts facts-row" style="margin-block:var(--space-lg)">
      <div class="fact"><dt class="caption">Flagbearer</dt>
        <dd>Led India in at the Asian Winter Games, Harbin 2025.</dd></div>
      <div class="fact"><dt class="caption">Two World Championships</dt>
        <dd>Planica 2023 and Trondheim 2025, on the FIS record.</dd></div>
      <div class="fact"><dt class="caption">Three World Cup starts</dt>
        <dd>Ruka, Trondheim and Davos, all inside one season.</dd></div>
    </dl>
    <div class="talks">{talks}</div>
  </div>
</section>
<section class="prose-fold" data-ground="ice">
  <div class="wrap prose">
    <h2>Audiences</h2>
    <p>{aud}.</p>
    <p>{e(sp.get('availability') or '')}</p>
    <a class="btn" data-on="accent"
       href="contact.html?topic=Speaking">Invite Bhavani to speak</a>
  </div>
</section>"""
    return subpage(c, img, "Speaking", sp.get("lede") or "", body,
                   shot="flag-almaty", current="speaking.html", og="speaking")


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
<link rel="icon" href="/v2/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="/v2/assets/css/v2.css?v={fingerprint()}">
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
    print(f"v2/  8 pages   index {out.stat().st_size / 1024:.1f} KB")
    print("  benchmark  rogerfederer.com  ·  6 panels + sponsor band + split")
    print(f"  medals     international {sum(m['International'].values())}"
          f"  national {sum(m['National'].values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
