#!/usr/bin/env python3
"""
Render index.html and assets/js/data.js from content/*.json.

The JSON files are the single source of truth. Nothing factual is written into
markup by hand, so a correction made in content/bhavani.json propagates to the
page, the structured data and the interactive components in one step.

    python build.py

No dependencies beyond the standard library.
"""

from __future__ import annotations

import hashlib
import html
import json
import pathlib
import shutil
import sys

from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "content"
OUT_HTML = ROOT / "index.html"

# Marks the first frame of the hero burst and the first press pair as visible.
#
# It is a constant rather than an inline literal because it contains escaped
# quotes, and a backslash inside an f-string expression is a syntax error before
# Python 3.12. That built fine locally and would have failed the first
# Cloudflare build against whatever Python their image ships. Pulling it out
# means the generator runs on any Python 3.8 and up.
ON_FIRST = ' data-on="true"'

# Three families from Google, and the wordmark face self-hosted.
#
# Black Rusher by Alpaprana Studio carries her name and nothing else. It is
# brush-written, so it is set in mixed case: brush capitals have no case
# contrast to work with and turn into a wall. Archivo still does every other
# heading, which keeps the brush reading as a signature rather than as the
# site's voice.
#
# It is not on Google Fonts, so it is subset and served from `assets/fonts/`.
# See the `@font-face` at the top of site.css and tools/make_wordmark_font.py.
#
# Two faces were here before it, and both are gone for reasons worth keeping:
# Yuji Syuku is Japanese and its Latin glyphs are not what it was drawn for,
# and Kaushan Script was rejected on looks.
FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Archivo:wdth,wght@62..125,400..900"
    "&family=IBM+Plex+Mono:wght@400;500"
    "&family=Newsreader:opsz,wght@6..72,300..600"
    "&display=swap"
)

# Relative to the page. The hero name is the largest thing on the first screen,
# so the file is fetched at the same time as the stylesheet rather than after
# the browser has parsed it and discovered the @font-face.
WORDMARK_FONT = "assets/fonts/black-rusher.woff2"

# Sections the fixed track rail marks, top to bottom.
RAIL_STOPS = [
    ("top", "Start"),
    ("journey", "Journey"),
    # The deck sits inside the journey section but is long enough to be its own
    # place on the rail, and the reader needs to know what they are looking at.
    ("deck", "Records"),
    ("footprint", "Map"),
    ("beyond", "Beyond"),
    ("record", "Record"),
    ("media", "Media"),
    ("ambition", "2030"),
    ("speaking", "Speaking"),
    ("partners", "Partners"),
    ("contact", "Work"),
]

# Seven of the nine chapters, in page order.
#
# `Contact` was the notable omission: a sponsor landing mid-page had no route to
# the ask except scrolling to the end, and a floating button is easy to read as
# decoration. `Athlete` became `Record`, which is what that section is.
NAV = [
    ("journey", "Journey"),
    ("record", "Record"),
    ("media", "Media"),
    ("ambition", "2030"),
    ("speaking", "Speaking"),
    ("partners", "Partners"),
    ("contact", "Contact"),
]

# Gallery running order: slot, span. Presentation only, so it lives here.
GALLERY = [
    ("hero-portrait", "tall"), ("khelo-ice-sculpture", "wide"),
    ("race-forest", ""), ("podium-gulmarg-2022", "wide"),
    ("roller-vidhana-soudha", ""), ("medals-detail", ""),
    ("track-texture", "tall"), ("khelo-ladakh-skis", ""),
    ("start-line-gulmarg", "wide"), ("race-orange-bib", ""),
    ("team-with-skis", "wide"), ("portrait-himachali", ""),
    ("lake-mountains", ""), ("trophy-karnataka", ""),
    ("ruapehu", "wide"), ("flag-almaty", ""),
    ("roller-road", ""), ("india-jacket-detail", ""),
    ("ski-city-overlook", "tall"), ("portrait-cap", ""),
]

# Label placement for the footprint plot. Presentation, keyed by place id.
# show=False keeps the point interactive but drops its permanent label, which is
# how the tight Alpine and Scandinavian cluster stays readable.
PLOT_LABELS = {
    "kodagu":     (8, 11, "start", True),
    "gulmarg":    (8, -7, "start", True),
    "akureyri":   (9, 3, "start", True),
    "planica":    (-9, 13, "end", True),
    "schuchinsk": (9, 3, "start", True),
    "idre":       (0, 0, "start", False),
    "seefeld":    (0, 0, "start", False),
    "lygna":      (0, 0, "start", False),
    "harbin":     (-9, 3, "end", True),
    "trondheim":  (-9, -6, "end", True),
    "antillanca": (0, 0, "start", False),
    "corralco":   (9, 4, "start", True),
    "ruka":       (9, 2, "start", True),
    "davos":      (0, 0, "start", False),
}

# Plot window, degrees. Plate carree, so latitude and longitude share a scale.
LON_MIN, LON_MAX = -95.0, 140.0
LAT_MIN, LAT_MAX = -52.0, 76.0
PLOT_W = 1000.0
PLOT_H = PLOT_W * (LAT_MAX - LAT_MIN) / (LON_MAX - LON_MIN)

NAMED_PARALLELS = [
    (66.5, "Arctic Circle"),
    (23.44, "Tropic of Cancer"),
    (0.0, "Equator"),
    (-23.44, "Tropic of Capricorn"),
]


# --------------------------------------------------------------------- utils

def e(s) -> str:
    """Escape for text nodes and quoted attributes."""
    return html.escape(str(s), quote=True) if s is not None else ""


# The path each section heading takes across the frame. Alternating left and
# right: a page where everything rises from below reads as one long vertical
# scroll no matter how different the sections are underneath.
#
# Horizontal only, deliberately. A heading is a full-width block stacked above
# another full-width block, so any vertical component sends it into whatever
# follows: the diagonals here used to close the gap under `beyond` and
# `speaking` by 13px and 9px at the ends of their travel. Sideways, they cannot
# reach anything.
SECTION_TRAVEL = {
    "journey": "l-r",
    "footprint": "r-l",
    "beyond": "l-r",
    "record": "r-l",
    "media": "l-r",
    "ambition": "r-l",
    "speaking": "l-r",
    "partners": "r-l",
    "contact": "l-r",
}


def lat_anchors(s: dict) -> str:
    """The three latitudes that define the span named in the heading."""
    if not s.get("anchors"):
        return ""
    rows = "".join(
        f'<li><span class="anch-lat mono">{abs(a["lat"]):.0f}&deg;'
        f'{"N" if a["lat"] >= 0 else "S"}</span>'
        f'<span class="anch-place">{e(a["place"])}<i>{e(a["country"])}</i></span>'
        f'<span class="anch-note mono">{e(a["note"])}</span></li>'
        for a in s["anchors"]
    )
    return f'<ul class="anchors">{rows}</ul>'


def section_head(c: dict, key: str) -> str:
    """
    The numbered heading block at the top of a section.

    Every one of these used to be typed out in this file, which put reader-facing
    copy in the template and let the numbering drift out of sequence unnoticed.
    They now come from `sections` in bhavani.json, and `check_sections` enforces
    the run.
    """
    s = c["sections"][key]
    lede = f'\n      <p class="lede">{e(s["lede"])}</p>' if s.get("lede") else ""
    aside = lat_anchors(s)
    aside = f"\n      {aside}" if aside else ""
    # Alternating so the headings do not all cross the frame the same way. The
    # amplitude is held down because this is the one element in each section a
    # reader needs to be able to fix on.
    path = SECTION_TRAVEL.get(key, "l-r")
    return f"""<div class="section-head" data-travel="{path}" style="--amp:0.45"
      data-aside="{str(bool(aside)).lower()}">
      <span class="idx mono">{e(s['index'])}</span>
      <h2>{e(s['title'])}</h2>{lede}{aside}
    </div>"""


def check_sections(c: dict) -> None:
    """Fail the build on a duplicated or skipped section number."""
    nums = [s["index"] for s in c["sections"].values()]
    if len(set(nums)) != len(nums):
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        raise SystemExit(f"build: duplicate section index {', '.join(dupes)}")
    # Numbered sections run from 01. They used to start at 02, which left the
    # reader meeting 02 first and hunting for a 01 that was never on the page.
    want = [f"{n:02d}" for n in range(1, 1 + len(nums))]
    if nums != want:
        raise SystemExit(f"build: section indices {nums} should run {want}")


def asset_version(*paths: pathlib.Path) -> str:
    """
    Short fingerprint of the linked assets, appended to their URLs.

    Without it a browser happily keeps serving a stylesheet or a script from
    cache after a rebuild, which reads as "the change did not work".
    """
    h = hashlib.sha1()
    for p in paths:
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


def load(name: str) -> dict:
    with (CONTENT / name).open(encoding="utf-8") as fh:
        return json.load(fh)


class Img:
    """Wraps the image library so markup never guesses at a path."""

    def __init__(self, lib: dict):
        self.base = lib["meta"]["basePath"]
        self.by_slot = {i["slot"]: i for i in lib["images"]}

    def get(self, slot):
        return self.by_slot.get(slot)

    def src(self, slot, width=None, up="") -> str:
        a = self.by_slot[slot]
        w = width if width in a["widths"] else a["widths"][-1]
        return f"{up}{self.base}/{a['file']}-{w}.webp"

    def srcset(self, slot, up="") -> str:
        a = self.by_slot[slot]
        return ", ".join(
            f"{up}{self.base}/{a['file']}-{w}.webp {w}w" for w in a["widths"]
        )

    def focal(self, slot) -> str:
        """
        `object-position` for a slot, from the focal point in images.json.

        Every crop on this site is `object-fit: cover`, so the focal point is
        the difference between a photograph of her and a photograph of her
        shoulder. Anything that builds an `<img>` by hand has to call this;
        skipping it silently falls back to dead centre, which is what the whole
        archive strip was doing.
        """
        a = self.by_slot.get(slot)
        if not a or not a.get("focal"):
            return "50% 50%"
        return f"{a['focal'][0] * 100:.1f}% {a['focal'][1] * 100:.1f}%"

    def tag(self, slot, sizes="100vw", cls="", loading="lazy", fetchpriority=None,
            up="") -> str:
        """
        `up` prefixes the paths for pages that are not at the site root.

        A journal entry lives at `journal/<slug>.html`, so its images need one
        level of `../`. Without this the markup is correct on the homepage and
        broken everywhere else, which is exactly how it failed the first time.
        """
        a = self.by_slot.get(slot)
        if not a:
            return ""
        w, h = a["natural"]
        pos = self.focal(slot)
        fp = f' fetchpriority="{fetchpriority}"' if fetchpriority else ""
        cl = f' class="{e(cls)}"' if cls else ""
        return (
            f'<img{cl} src="{e(self.src(slot, up=up))}" '
            f'srcset="{e(self.srcset(slot, up=up))}" '
            f'sizes="{e(sizes)}" width="{w}" height="{h}" alt="{e(a["alt"])}" '
            f'loading="{loading}" decoding="async"{fp} '
            f'style="object-position:{pos}">'
        )


# ----------------------------------------------------------------- fragments

def head(c: dict, img: Img, version: str) -> str:
    seo = c["seo"]
    ident = c["identity"]
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": ident["fullName"],
        "alternateName": ident["shortName"],
        "birthDate": ident["birthDate"],
        "nationality": {"@type": "Country", "name": ident["nation"]},
        "jobTitle": "Cross-country skier",
        "url": seo["siteUrl"],
        "image": seo["siteUrl"].rstrip("/") + "/" + seo["ogImage"],
        "sameAs": [c["sources"]["fis"]["sourceUrl"]],
    }
    og = seo["siteUrl"].rstrip("/") + "/" + seo["ogImage"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(seo['title'])}</title>
<meta name="description" content="{e(seo['description'])}">
<link rel="canonical" href="{e(seo['siteUrl'])}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{e(seo['title'])}">
<meta property="og:description" content="{e(seo['description'])}">
<meta property="og:image" content="{e(og)}">
<meta property="og:url" content="{e(seo['siteUrl'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#06090f">
<!-- The palette is authored dark and tuned against the photographs. Dark Reader
     and similar extensions otherwise rewrite every colour, which turns the hero
     scrim into an opaque panel over the athlete. This is their documented opt-out. -->
<meta name="darkreader-lock">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- No `?v=` here. The @font-face in site.css requests this file without a query,
     and a preload whose URL does not match byte for byte is not a preload: the
     browser fetches it twice and warns that the first was unused. The file is
     versioned by its own name if it ever changes. -->
<link rel="preload" as="font" type="font/woff2" crossorigin
      href="{e(WORDMARK_FONT)}">
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="preload" as="image" href="{e(img.src('hero-portrait', 960))}"
      imagesrcset="{e(img.srcset('hero-portrait'))}" imagesizes="(min-width:900px) 52vw, 100vw">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/css/site.css?v={version}">
<script>document.documentElement.classList.add("js")</script>
<script type="application/ld+json">{json.dumps(schema, indent=None)}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>"""


def rail() -> str:
    """
    Fixed left rail: paired grooves, a scroll-linked cut, checkpoint nodes.

    The grooves are a stretched SVG, which is safe because they are straight
    lines. The nodes are positioned elements instead, so they stay circular, and
    JS places them at each section's real scroll offset rather than spacing them
    evenly down the rail.
    """
    # Anchors, not divs.
    #
    # The rail already showed where the reader was and marked what they had
    # passed, so it read as navigation and behaved as decoration: eleven dots
    # that look like stops and do nothing when you press them. Every `data-stop`
    # is already an element id, so the href costs nothing and works with
    # JavaScript off, from the keyboard, and on a long-press menu.
    nodes = "".join(
        f'<a class="node" href="#{e(sid)}" data-stop="{e(sid)}">'
        f'<i></i><span class="rail-label mono">{e(label.upper())}</span></a>'
        for sid, label in RAIL_STOPS
    )
    # No viewBox: SVG user units are CSS pixels, so main.js can lay the terrain
    # out against real section offsets without a scaling factor in the way.
    return f"""
<div class="track-rail" aria-hidden="true">
  <svg class="rail-svg" id="rail-svg">
    <path class="approach" id="terrain-approach"></path>
    <path class="groove" id="terrain-groove-a"></path>
    <path class="groove" id="terrain-groove-b"></path>
    <g class="ticks" id="terrain-ticks"></g>
    <path class="cut" id="cut-a"></path>
    <path class="cut" id="cut-b"></path>
    <path class="ski" id="ski-a"></path>
    <path class="ski" id="ski-b"></path>
  </svg>
  <div class="rail-nodes" id="rail-nodes">{nodes}</div>
</div>"""


def nav(c: dict, has_journal: bool = False) -> str:
    ident = c["identity"]
    links = "".join(
        f'<li><a href="#{e(i)}" data-nav="{e(i)}">{e(l)}</a></li>' for i, l in NAV
    )
    panel = "".join(f'<a href="#{e(i)}">{e(l)}</a>' for i, l in NAV)
    # The Journal only appears once something is published. An empty section in
    # the navigation advertises that nothing is there.
    if has_journal:
        links += '<li><a href="journal.html">Journal</a></li>'
        panel += '<a href="journal.html">Journal</a>'

    # The governing body's record, out of the hero and into the header where a
    # reference link belongs. Marked as leaving the site, since it does.
    fis = c["hero"]["ctaTertiary"]
    links += (
        f'<li class="nav-out"><a href="{e(fis["href"])}" target="_blank" '
        f'rel="noopener">{e(fis["label"])} <span aria-hidden="true">&#8599;</span></a></li>'
    )
    panel += (
        f'<a href="{e(fis["href"])}" target="_blank" rel="noopener">'
        f'{e(fis["label"])} &#8599;</a>'
    )
    return f"""
<header class="nav" id="nav">
  <a class="nav-mark" href="#top">{e(ident['wordmark'])}<span>{e(ident['descriptor'])}</span></a>
  <nav aria-label="Sections">
    <ul class="nav-links">{links}</ul>
  </nav>
  <button class="nav-toggle" id="nav-toggle" aria-expanded="false"
          aria-controls="nav-panel" aria-label="Open menu"><span></span></button>
</header>
<div class="nav-panel" id="nav-panel" data-open="false">{panel}</div>
<div class="nowbar" id="nowbar" data-shown="false" aria-hidden="true">
  <span class="now-idx mono"></span>
  <span class="now-name"></span>
</div>
<a class="float-cta" id="float-cta" href="#contact" data-shown="false">
  <span aria-hidden="true">+</span> Work with Bhavani</a>"""


def hero(c: dict, img: Img) -> str:
    h = c["hero"]
    # Title case, not the stored all-caps. The wordmark face is brush-written and
    # capitals give it no ascenders or descenders to swing off, which is where
    # all of its character lives.
    first, _, rest = c["identity"]["wordmark"].title().partition(" ")

    # A slow cross-fade, not the shutter burst this used to be. The burst held
    # each frame for an eighth of a second, which read as a glitch rather than a
    # film and made the name underneath hard to hold. Frames now breathe in and
    # out over several seconds, which is what video will do when there is video,
    # so swapping this for a <video> later changes the markup and nothing else.
    #
    # Larger variants than the burst used, because a frame on screen for five
    # seconds is looked at, and 480px was visibly soft at that duration.
    fade = ""
    b = h.get("burst")
    if b and b.get("frames"):
        # Each frame crops to its own focal point. These were the other images
        # built by hand rather than through img.tag, so all seven inherited one
        # hardcoded `50% 26%` from the stylesheet: right for the portrait it was
        # written for, wrong for the six that followed it. The ice sculpture
        # wants 72% across and was being cut at 50%.
        shots = "".join(
            f'<img src="{e(img.src(s, 1200))}" alt="" '
            f'aria-hidden="true" decoding="async" fetchpriority="low" '
            f'style="object-position:{img.focal(s)}"'
            f'{ON_FIRST if i == 0 else ""}>'
            for i, s in enumerate(b["frames"])
            if img.get(s)
        )
        fade = f'<div class="herofade" id="hero-fade" data-ms="4600">{shots}</div>'

    return f"""
<section class="hero" id="top">
  <div class="hero-media">{img.tag('hero-portrait', '(min-width:900px) 52vw, 100vw', loading='eager', fetchpriority='high')}{fade}</div>
  <div class="hero-inner wrap">
    <p class="eyebrow">{e(h['eyebrow'])}</p>
    <h1><span class="l1">{e(first)}</span> <span class="l2">{e(rest)}</span></h1>
    <p class="hero-line">{e(h['line'])}</p>
    <!--
      The credentials.

      This was one grey sentence with middots in it, at caption size, and it
      read as a caption: the eye went name, tagline, and then straight past it.
      Three separate items now, each on its own accent bar, in the accent
      colour, so the first screen answers "and what has she done" without the
      reader having to look for the answer.
    -->
    <ul class="hero-cred">
      <li>World Cup starter</li>
      <li>2 World Championships</li>
      <!--
        Client's call, taken against advice and recorded here so the next person
        knows it was a decision and not an oversight.

        This slot has held "International medallist", then "First Indian woman
        to medal". It now states a ranking. Nothing on the FIS record supports
        it: FIS publishes no per-nation cross-country ranking, and no article in
        the press list uses the phrase. It is also the kind of claim that goes
        stale with a points list rather than staying true.

        The medal claim is not lost. It is the first line of the next section,
        in full, with the FIS-scored qualifier that makes it defensible.
      -->
      <li>India's No. 1 cross-country skier</li>
    </ul>
    <!--
      No call to action here at all now.

      It was three buttons, then one link reading "Start at Kodagu". Both
      versions had the same two faults. The link pointed at `#journey`, so a
      reader who took it skipped the claim, the profile, the proof plates and
      the explanation of the sport, which is every piece of evidence the page
      has. And it sat directly above "Scroll to explore", so the first screen
      gave two different instructions to do the same thing.

      The cue below does the job on its own, and the page below it is worth
      arriving at in order.
    -->
  </div>
  <a class="hero-cue" id="hero-cue" href="#profile">
    <span class="mono">Scroll to explore</span>
    <span class="hero-cue-line" aria-hidden="true"></span>
  </a>
</section>"""


def profile(c: dict, img: Img) -> str:
    """
    The introduction, arriving from the bottom-right corner.

    This paragraph used to sit in the hero under the name, where it competed
    with the wordmark and was read by nobody. On its own it becomes the first
    thing the page says after the title card, and entering from the corner means
    the first scroll is answered by movement rather than by more page.
    """
    h = c["hero"]
    facts = "".join(
        f'<div><dt class="mono">{e(x["k"])}</dt><dd>{e(x["v"])}</dd></div>'
        for x in h["profileFacts"]
    )
    return f"""
<section class="profile" id="profile" aria-label="Who she is">
  <div class="wrap">
    <!--
      A shorter path and a faster fade than the page default. This card follows
      the headline band, and at the standard amplitude it was still invisible
      well after the figures above it had left, which read as a blank screen.
    -->
    <div class="profile-card" data-travel="br-tl" style="--amp:0.55">
      <!--
        `portrait-studio`, which is the frame this slot had been waiting for.

        Every earlier candidate came from the portfolio PDFs and every one of
        them failed the same way: `portrait-cap` is cut at its own right edge,
        `portrait-himachali` puts her chin on the bottom edge of the source so
        no crop can lift her off it, and `portrait-team-kit` sits her at 18%
        across with the rest of the frame empty. The note here used to say what
        the slot actually needed was one head-and-shoulders frame shot for a
        portrait crop. This is that frame: upper body, plain ground, eyes level
        and open, nothing across her face. It also comes from her own archive
        rather than the portfolio, so it is the first image in this slot with
        settled rights.
      -->
      <div class="profile-shot">
        {img.tag('portrait-studio', '(min-width:900px) 30vw, 70vw')}
      </div>
      <div class="profile-copy">
        <p class="eyebrow">Who she is</p>
        <h2>{e(h['profileHeading'])}</h2>
        <p>{e(h['profileBody'])}</p>
        <p>{e(h['profileBody2'])}</p>
      </div>
      <!-- The fact strip spans the whole card rather than sitting in the copy
           column, so it reads as the record under an article. -->
      <dl class="profile-facts">{facts}</dl>
    </div>
  </div>
</section>"""


def sport(c: dict) -> str:
    """
    What the sport actually is.

    The site assumed the reader knew. Most people in India have never watched a
    cross-country race, and "10 km interval start" means nothing without this.
    """
    s = c["sport"]
    # The disciplines cross the frame rather than sit in a row. Odd cards travel
    # right to left and even ones left to right, so they pass each other on the
    # way through and the band reads as movement instead of a table with the
    # rules taken out.
    items = "".join(
        f'<li>'
        f'<div class="drift" data-travel="{"l-r" if i % 2 else "r-l"}" '
        f'style="--amp:{1.0 + 0.3 * (i % 3):.1f}">'
        f'<span class="sport-n mono">{i + 1:02d}</span>'
        f'<b>{e(x["name"])}</b><p>{e(x["note"])}</p></div></li>'
        for i, x in enumerate(s["disciplines"])
    )
    return f"""
<section class="sport" id="sport" aria-label="About the sport">
  <div class="wrap">
    <div class="sport-head" data-travel="tl-br" style="--amp:0.5">
      <span class="eyebrow">{e(s['kicker'])}</span>
      <p class="lede">{e(s['lede'])}</p>
    </div>
  </div>
  <ul class="sport-pairs">{items}</ul>
  <div class="wrap">
    <p class="sport-year" data-travel="r-l" style="--amp:0.6">{e(s['yearNote'])}</p>
  </div>
</section>"""


def headline(c: dict, img: Img) -> str:
    """
    What she has done, said once and said large.

    Everything she has achieved lived on this page as small plates in a band
    less than half a screen tall, or as coloured dots inside a filterable table.
    A sponsor deciding in eight seconds never saw any of it. This is the first
    thing after the title card and it exists to be read at a glance.

    The sourcing is not printed here. It lives in `content/bhavani.json` and in
    the `withheld` ledger, which records that two independent outlets carry the
    claim and that no governing body publishes a register of national firsts.
    On the page it read as the site auditing itself in front of the reader,
    which is not what a headline is for.
    """
    h = c["headline"]
    # `h["figures"]` is deliberately not rendered.
    #
    # It was three cards reading 3 World Cup starts, 2 World Championships and
    # 2 international bronze. The proof band one screen below opens with six
    # cards, and three of them are those same three with the same sub-copy and
    # the same years. Stating a fact twice is emphasis; stating a whole set
    # twice in one screen is padding, and it spends credibility the FIS record
    # earns for nothing.
    #
    # The six-card set survives because it is the complete one. This section
    # now ends on the prose, which was always stronger without cards under it.
    # The data stays in the file: it is the same figures, and a future summary
    # or share card can read it from here.
    # The right half of this band was empty, and the claim is about a podium, so
    # a podium is what goes there. It rises and dissolves as the section passes
    # rather than sitting still, which keeps it from reading as a second hero.
    #
    # `podium-first` deliberately, not `medals-detail`: those are her national
    # medals on Khelo India lanyards, and putting them beside a sentence about a
    # FIS race would imply the wrong medals.
    shot = (
        f'<div class="hl-shot" data-dissolve aria-hidden="true">'
        f'{img.tag("podium-first", "(min-width:900px) 32vw, 0px")}</div>'
        if img.get("podium-first")
        else ""
    )
    return f"""
<section class="headline" id="headline" aria-label="Career at a glance">
  {shot}
  <div class="wrap">
    <h2 class="hl-claim" data-travel="r-l" style="--amp:0.5">{e(h['claim'])}</h2>
    <!--
      Horizontal only. On `bl-tr` this paragraph rose 130px into the claim above
      it as the claim was still leaving. Stacked blocks can travel sideways past
      each other safely; they cannot travel vertically past each other.
    -->
    <p class="hl-line" data-travel="l-r" style="--amp:0.55">{e(h['line'])}</p>
  </div>
</section>"""


def proof(c: dict) -> str:
    """
    Race bibs, not a list.

    The first thing after the hero was six flat rows, which is where a reader
    decides whether to keep going. A bib is the sport's own object for carrying a
    number, and it avoids reproducing any event's trademarked logo.
    """
    # One path for all six, and the amplitude lives in CSS. Six different
    # diagonals were written for the six-across desktop row, but at that width
    # the depth transform overrides travel entirely, so the paths only ever
    # fired in the stacked layouts -- where neighbouring plates in the same grid
    # row crossed into each other's column, by up to 269px at 375 wide. Plates
    # on a shared path stay parallel at every column count. The desktop row
    # keeps its per-plate depth, which is where the variety was wanted.
    # The plates come up one after another, like a row of bulbs being switched
    # on. It rides the existing reveal system rather than a new observer: the
    # article carries `data-anim`, initReveal flips `data-shown` when it enters
    # view, and CSS staggers off `--i`. That inherits the reduced-motion bypass
    # and the safety net that stops a dead observer leaving the row dark.
    #
    # The light sits on the article, never on the `li`. The `li` is a travel
    # element whose opacity is already driven by `--o`, and two rules writing
    # the same property is how this kind of thing breaks.
    plates = "".join(
        f"""<li data-travel="r-l">
      <article class="bib" data-anim="bulb" style="--i:{i}">
        <span class="bib-count">{e(p['count'])}</span>
        <span class="bib-unit mono">{e(p['unit'])}</span>
        <span class="bib-rule"></span>
        <h3 class="bib-label">{e(p['label'])}</h3>
        <p class="bib-detail">{e(p['detail'])}</p>
        <span class="bib-year mono">{e(p['year'])}</span>
      </article>
    </li>"""
        for i, p in enumerate(c["proofOfLevel"])
    )
    return f"""
<section class="proof" id="proof" aria-label="Level of competition">
  <div class="wrap">
    <h2 class="vh">Career highlights</h2>
    <ul class="bibs">{plates}</ul>
  </div>
</section>"""


# How each chapter is sized and where it sits vertically on the rail. Uniform
# panels would turn the horizontal run into a conveyor belt, which is the same
# monotony as the vertical scroll it replaces. Big frames land on the chapters
# that carry the most weight; the small ones are the connective years.
PANEL_SHAPE = [
    ("lg", "low"),
    ("sm", "high"),
    ("md", "mid"),
    ("lg", "high"),
    ("sm", "low"),
    ("md", "mid"),
]


def story(c: dict, img: Img) -> str:
    """
    The journey runs sideways.

    A vertical column of chapters is the shape the client kept objecting to, and
    they are right: six beats stacked downward read as one more scroll however
    the panels are decorated. So the section pins and the chapters travel right
    to left across the frame while the page scrolls down, which is the Lando
    Norris pattern (measured on landonorris.com: pin plus translateX, not
    `overflow-x`, so the scrollbar and keyboard paging both survive).

    Everything is still real document scroll on `position: sticky`. No wheel
    handler, no hijack. Under reduced motion, and with JS off, the track drops
    back to a readable wrapped column and the runway collapses to nothing.
    """
    s = c["story"]
    panels = []

    for i, b in enumerate(s["beats"]):
        a = img.get(b["image"]) if b["image"] else None
        size, lift = PANEL_SHAPE[i % len(PANEL_SHAPE)]

        if a:
            media = (
                f'<figure class="jp-media">'
                f'{img.tag(b["image"], "(min-width:900px) 42vw, 82vw")}'
                f'<figcaption class="mono">{e(a["location"] or "")}</figcaption>'
                f"</figure>"
            )
        else:
            # No photograph honestly belongs to this beat. A year set large beats
            # borrowing a frame from somewhere else.
            media = (
                f'<div class="jp-media is-plate" aria-hidden="true">'
                f'<span class="plate-year">{e(b["year"])}</span></div>'
            )

        # A chapter with no photograph already carries its year, set large, in
        # place of the picture. Printing it again underneath showed the same
        # four digits twice in a row.
        year = "" if a is None else f'<p class="jp-year mono">{e(b["year"])}</p>'

        panels.append(
            f"""<article class="jpanel" data-size="{size}" data-lift="{lift}"
      data-chapter="{i}" id="beat-{e(b['id'])}">
      {media}
      <div class="jp-copy">
        {year}
        <h3>{e(b['heading'])}</h3>
        <p class="jp-body">{e(b['body'])}</p>
      </div>
    </article>"""
        )

    ticks = "".join(
        f'<li><span class="mono">{e(b["year"])}</span></li>' for b in s["beats"]
    )

    # Opens the merged section. career() closes it, so the two movements share
    # one <section> and one heading.
    return f"""
<section id="journey">
  <div class="wrap">
    {section_head(c, "journey")}
  </div>
  <div class="jrail" id="jrail" style="--panels:{len(panels)}">
    <div class="jrail-stage">
      <div class="jrail-track" id="jrail-track">{''.join(panels)}</div>
      <div class="jrail-foot" aria-hidden="true">
        <ol class="jrail-ticks">{ticks}</ol>
        <div class="jrail-bar"><span id="jrail-fill"></span></div>
      </div>
    </div>
  </div>"""


def career(c: dict, img: Img) -> str:
    """
    The record, dealt rather than listed.

    A vertical timeline of eleven rows is a list with a line drawn down it. Each
    result now arrives as its own card from the lower right, squares up in the
    middle of the frame, then settles back into the stack as the next one comes
    in, so the reader takes one race at a time and the pile behind them is the
    career accumulating.

    Everything is transform and opacity driven by scroll offset, on a real
    runway with `position: sticky`. Under reduced motion the runway collapses
    and the cards fall back to a plain readable column.
    """
    ms = []
    for i, m in enumerate(c["careerMilestones"]):
        result = (
            f'<p class="deck-result mono">{e(m["result"])}</p>' if m["result"] else ""
        )
        # Only two of the eleven produced a podium. Rendering the discs on every
        # card would make the highlight meaningless, so a card without medals
        # simply does not carry the block.
        medals = ""
        if m.get("medals"):
            rows = "".join(
                f'<li data-metal="{e(x["metal"])}">'
                f'<span class="medal-disc" aria-hidden="true"></span>'
                f'<b>{e(x["metal"].title())}</b>'
                f'<span class="mono">{e(x["event"])}</span></li>'
                for x in m["medals"]
            )
            medals = f'<ul class="deck-medals">{rows}</ul>'
        podium = " has-medals" if m.get("medals") else ""
        golds = " has-gold" if any(
            x["metal"] == "gold" for x in m.get("medals", [])
        ) else ""

        # Five of the eleven milestones already carried a photograph in the
        # content file that this template never rendered. Those five get it;
        # the other six stay type-only rather than borrowing a frame from a
        # different race, which is the same rule the journey chapters follow.
        shot = ""
        if m.get("image") and img.get(m["image"]):
            shot = (
                f'<div class="deck-shot">'
                f'{img.tag(m["image"], "(min-width:900px) 26vw, 70vw")}</div>'
            )

        ms.append(
            f"""<article class="deck-card{podium}{golds}{' has-shot' if shot else ''}"
      data-card="{i}" data-phase="{e(m['phase'])}" id="ms-{e(m['id'])}">
      {shot}
      <div class="deck-body">
        <span class="deck-index mono">{i + 1:02d} / {len(c['careerMilestones']):02d}</span>
        <p class="deck-year">{e(m['year'])}</p>
        <h3>{e(m['title'])}</h3>
        <span class="deck-place mono">{e(m['location'])}</span>
        <p class="deck-line">{e(m['line'])}</p>
        {medals}
        {result}
      </div>
    </article>"""
        )

    # The latitude stat used to sit here, saying "105 degrees" two screens above
    # a map headed "107 degrees". Same argument, two numbers, no explanation of
    # why they differ. The map can show it and this could only assert it, so the
    # map keeps it and this is gone, along with the empty `.wrap` that was left
    # behind holding nothing.

    # The hinge now rides inside the pinned deck instead of scrolling past above
    # it. Eleven cards used to deal past with nothing on screen naming what they
    # were, which is the same fault the photo scrub had. Pinned, the title holds
    # for the whole run.
    s = c["sections"]["journey"]
    hinge = f"""
      <div class="deck-head">
        <h3>{e(s['hinge'])}</h3>
        <p>{e(s['hingeNote'])}</p>
      </div>"""

    t = c["targets"]
    # Marked as targets in the markup, the label and the copy. A stated intention
    # rendered like a result is the exact failure this content model exists to
    # prevent, and the 2030 line is the one a reader is most likely to misread.
    # All four years stay on screen together. They used to dissolve one at a
    # time, which meant three of the four were faded to nothing at any moment
    # and the road to 2030 could not be read as a plan. Now the block pins,
    # every year is visible, and each one lights in turn as the reader advances.
    # The last one, the Olympics, comes toward the reader and dissolves, which
    # is the point the whole section has been building to.
    last = len(t["items"]) - 1
    tiles = "".join(
        f'<li class="target" style="--n:{i}"'
        f'{" data-zoom=\"true\"" if i == last else ""}>'
        f'<span class="target-year mono">{e(x["year"])}</span>'
        f'<h4>{e(x["title"])}</h4><p>{e(x["line"])}</p></li>'
        for i, x in enumerate(t["items"])
    )
    # The finale. 2030 was the fourth of four equal tiles, which made the thing
    # the whole section aims at the same size as the steps toward it. At the end
    # of the run the three earlier years shrink back into a strip and this card
    # takes the middle of the frame, carrying enough detail to earn the room.
    f = t["finale"]
    fsteps = "".join(
        f'<div><dt class="mono">{e(x["k"])}</dt><dd>{e(x["v"])}</dd></div>'
        for x in f["steps"]
    )
    # The stat rail down the right edge. Every figure on it is proved somewhere
    # else on this page, which is the whole point: a card that states a target
    # is a claim, and a card that states a target next to the record behind it
    # is an argument. The mockup this came from carried "100+ races" and "six
    # years", neither of which the results table supports, so both are gone.
    fstats = "".join(
        f'<li><b>{e(x["n"])}</b><span>{e(x["k"])}</span></li>' for x in f["stats"]
    )
    # The backdrop, from her own library rather than the stock silhouette on the
    # reference card. Ruapehu is a 3315x948 banner of the mountain with her in
    # it, which is the right shape for a card edge and the right subject for a
    # panel about a summit four years out.
    back = (
        f'<div class="tf-back" aria-hidden="true">{img.tag(f["backdrop"], "45vw")}</div>'
        if f.get("backdrop") and img.get(f["backdrop"])
        else ""
    )
    # The link out is gone at the client's request and the slogan replaces it.
    # Recorded because it is a deliberate trade: this card no longer offers a
    # route to the partnership section, so the only path there is the nav.
    finale = f"""
        <div class="target-final">
          <div class="tf-inner">
            {back}
            <div class="tf-main">
              <span class="eyebrow">{e(f['eyebrow'])}</span>
              <p class="tf-year">{e(f['year'])}</p>
              <h4>{e(f['title'])}</h4>
              <p class="tf-where mono">{e(f['host'])} &middot; {e(f['dates'])}</p>
              <!--
                Two-part statement, matching the reference card. The lead is the
                three short sentences and is set larger; the line under it
                carries the argument.
              -->
              <p class="tf-lead">{e(f['lead'])}</p>
              <p class="tf-line">{e(f['line'])}</p>
              <dl class="tf-steps">{fsteps}</dl>
              <p class="tf-banner mono">{e(f['banner'])}</p>
            </div>
            <ul class="tf-stats">{fstats}</ul>
          </div>
        </div>"""
    # No separate hinge screen. There was one, and it read as a disconnected
    # slide between two sections rather than as part of either. The treatment it
    # used, a small label over a large statement over the disclosure on an
    # accent rule, belongs to this heading instead: it is the same job, done as
    # the opening of the section it introduces.
    # No heading inside this block any more.
    #
    # Once the forward-looking half became its own chapter, the chapter heading
    # and this one sat one directly under the other, both introducing the same
    # four tiles: "What she is chasing" followed immediately by "The road to
    # 2030". The chapter heading won, took the better title, and this block
    # starts straight in on the years.
    targets = f"""
      <div class="targets-run" id="targets-run" style="--steps:{len(t['items'])}">
        <div class="targets">
          <ol class="target-list">{tiles}</ol>
          {finale}
        </div>
      </div>"""

    b = c["beyondFinishLine"]
    pts = "".join(
        f'<li>'
        f'<h4>{e(x["title"])}</h4>'
        f'<p>{e(x["body"])}</p></li>'
        for i, x in enumerate(b["points"])
    )
    mission = f"""
      <div class="mission" data-anim="up">
        <!-- Container travels, items do not. See the note on `.hl-figs`. -->
        <ul class="mission-points" data-travel="b-t" style="--amp:0.5">{pts}</ul>
      </div>"""

    # The pull quote runs sideways while the page runs down, over a pinned frame.
    # It is the emotional peak of the page and the only place the type is allowed
    # to be this large. Horizontal travel is set in CSS from the string length so
    # the line always clears the viewport whatever it says.
    quote = f"""
    <div class="quote" id="quote">
      <div class="quote-stage">
        <div class="quote-bg" aria-hidden="true">{img.tag('race-forest', '100vw')}</div>
        <span class="quote-kicker mono">{e(b['kicker'])}</span>
        <p class="quote-line" id="quote-line">{e(b['lede'])}</p>
      </div>
    </div>"""

    # Returns two sections, not one.
    #
    # Chapter one used to carry the timeline, the eleven-start deck, the road to
    # 2030, the Olympic target and the ambition cards together. That put the
    # climax of the site 40% down the page: a reader who stopped there had seen
    # where the story ends without seeing the evidence, the recognition or the
    # ask, and everything after it read as appendix.
    #
    # The backward-looking half stays here and ends on the record. The
    # forward-looking half goes back to `main()` separately and is placed after
    # the press, so the running order becomes who she is, what she races, how
    # she got here, the record, who else says so, what she is chasing, what she
    # offers, what she needs, how to reach her. Each chapter now raises the
    # question the next one answers.
    journey_html = f"""
  <div class="movement-record">
    <div class="deck" id="deck" style="--cards:{len(ms)}">
      <div class="deck-stage">
        {hinge}
        <div class="deck-cards">{''.join(ms)}</div>
      </div>
    </div>
  </div>
</section>"""

    ambition_html = f"""
<section id="ambition">
  <div class="wrap">
    {section_head(c, "ambition")}
    {targets}
  </div>
  {quote}
  <div class="wrap">
    {mission}
  </div>
</section>"""

    return journey_html, ambition_html


# Labels drawn permanently on the map. Everything else would collide in the
# European cluster, so the rest appear on hover or focus. These four are the ones
# that carry the section's argument: the extremes and the two home dots.
ATLAS_ANCHORS = {"kodagu", "ruka", "corralco", "harbin"}


def footprint(c: dict, world: dict, img: Img) -> str:
    pts = c["internationalFootprint"]
    lat_top = world["latTop"]
    height = lat_top - world["latBottom"]

    def px(lon, lat):
        return lon + 180.0, lat_top - lat

    grat = []
    for lon in range(0, 361, 30):
        grat.append(f'<line class="grat" x1="{lon}" y1="0" x2="{lon}" y2="{height:.0f}"/>')
    for lat in range(-45, 76, 15):
        y = lat_top - lat
        grat.append(f'<line class="grat" x1="0" y1="{y:.1f}" x2="360" y2="{y:.1f}"/>')

    named = []
    for lat, name in NAMED_PARALLELS:
        y = lat_top - lat
        named.append(
            f'<line class="grat-named" x1="0" y1="{y:.1f}" x2="360" y2="{y:.1f}"/>'
            f'<text class="grat-label" x="3" y="{y - 2:.1f}">{e(name)}</text>'
        )

    pins, cards = [], []
    for p in pts:
        x, y = px(p["lon"], p["lat"])
        label = (
            f'<text class="pin-label" x="{x + 4.5:.1f}" y="{y + 1.4:.1f}">{e(p["place"])}</text>'
            if p["id"] in ATLAS_ANCHORS else ""
        )
        years = ", ".join(p["years"])
        pins.append(
            f'<g class="pin" data-place="{e(p["id"])}" data-kind="{e(p["kind"])}" '
            f'data-x="{x / 360 * 100:.3f}" data-y="{y / height * 100:.3f}" '
            f'tabindex="0" role="button" '
            f'aria-label="{e(p["place"])}, {e(p["country"])}. {e(p["event"])}, {e(years)}. '
            f'{e(p["best"])}">'
            f'<circle class="halo" cx="{x:.2f}" cy="{y:.2f}" r="4.6"/>'
            f'<circle class="dot" cx="{x:.2f}" cy="{y:.2f}" r="1.7"/>'
            f'{label}</g>'
        )

        # Ten of the fourteen venues have no photograph that honestly belongs to
        # them. Rather than leave the slot blank, they get a zoomed crop of the
        # same coastline path, centred on the venue. It is drawn from data
        # already on the page, costs nothing extra to ship because it reuses the
        # single land path through <use>, and carries none of the trademark
        # problems that come with reproducing an event's logo.
        zw, zh = 46.0, 34.5
        mini = (
            f'<figure class="card-shot card-mini">'
            f'<svg viewBox="{x - zw / 2:.2f} {y - zh / 2:.2f} {zw} {zh}" '
            f'preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<use href="#world-land"/>'
            f'<circle class="mini-dot" cx="{x:.2f}" cy="{y:.2f}" r="1.15"/>'
            f'<circle class="mini-ring" cx="{x:.2f}" cy="{y:.2f}" r="3.2"/>'
            f"</svg>"
            f'<figcaption class="mono">{abs(p["lat"]):.1f}&deg;'
            f'{"N" if p["lat"] >= 0 else "S"} &middot; {abs(p["lon"]):.1f}&deg;'
            f'{"E" if p["lon"] >= 0 else "W"}</figcaption>'
            f"</figure>"
        )
        shot = mini
        if p.get("image") and img.get(p["image"]):
            a = img.get(p["image"])
            where = a.get("location") or ""
            # The card already names the place underneath. Repeating it in the
            # image caption reads as a stutter, so the caption only appears when
            # the photograph was taken somewhere other than the marker.
            if where and p["place"].lower() in where.lower():
                where = ""
            credit = (
                f'<figcaption class="mono">{e(where)}</figcaption>' if where else ""
            )
            shot = (
                f'<figure class="card-shot">'
                f'{img.tag(p["image"], "(min-width:900px) 320px, 90vw")}{credit}</figure>'
            )
        hemi = "N" if p["lat"] >= 0 else "S"
        cards.append(
            f'<article class="atlas-card" data-card="{e(p["id"])}" hidden>{shot}'
            f'<div class="card-body">'
            f'<p class="card-place">{e(p["place"])}<span>{e(p["country"])}</span></p>'
            f'<p class="card-event">{e(p["event"])}</p>'
            f'<p class="card-best">{e(p["best"])}</p>'
            f'<p class="card-meta mono">{e(years)} &middot; '
            f'{abs(p["lat"]):.1f}&deg;{hemi}</p>'
            f'</div></article>'
        )

    south = min(pts, key=lambda p: p["lat"])
    north = max(pts, key=lambda p: p["lat"])
    resting = (
        f'<article class="atlas-card is-resting" data-card="__resting">'
        f'<div class="card-body">'
        f'<p class="card-place">{len(pts)} places<span>Six seasons</span></p>'
        # Carries the one fact worth keeping from the latitude stat that used to
        # sit two screens above this and make the same argument with a different
        # number. The map is the better home for it: this can show the spread on
        # its own axis, where the stat could only assert it.
        #
        # It used to close on "and has never had snow", which was the fifth
        # telling of that line on the page and the second inside this chapter.
        # It survives in the Kodagu panel, where it is the origin, and in the
        # profile, where the version about her parents is the better fact.
        f'<p class="card-event">From {abs(south["lat"]):.0f}&deg;S at '
        f'{e(south["place"])} to {abs(north["lat"]):.0f}&deg;N at {e(north["place"])}. '
        f'Kodagu sits almost exactly halfway between the two, at 12&deg;N.</p>'
        f'<p class="card-meta mono">Select a marker for the result</p>'
        f'</div></article>'
    )

    rows = "".join(
        f"<tr><td>{e(p['place'])}, {e(p['country'])}</td><td>{e(p['event'])}</td>"
        f"<td>{e(', '.join(p['years']))}</td>"
        f"<td>{e(p['best'])}</td>"
        f"<td>{p['lat']:.1f}&deg;{'N' if p['lat'] >= 0 else 'S'}</td></tr>"
        for p in pts
    )

    return f"""
<section id="footprint">
  <div class="wrap">
    {section_head(c, "footprint")}
    <div class="atlas" id="atlas" data-anim="up">
      <div class="atlas-scroll">
        <svg class="atlas-map" id="atlas-map" viewBox="0 0 360 {height:.0f}"
             role="img" aria-labelledby="atlas-title">
          <title id="atlas-title">World map marking every place she has raced. The same
          information is listed in the table below.</title>
          <defs><path id="world-land" d="{world['path']}"/></defs>
          <use class="land" href="#world-land"/>
          <g>{''.join(grat)}</g>
          <g>{''.join(named)}</g>
          <g class="pins">{''.join(pins)}</g>
        </svg>
        <ul class="plot-legend">
          <li><i data-kind="origin"></i> Home</li>
          <li><i data-kind="domestic"></i> India</li>
          <li><i></i> FIS and championships</li>
          <li><i data-kind="race"></i> World Cup and podium</li>
        </ul>
      </div>
      <aside class="atlas-panel" id="atlas-panel">{resting}{''.join(cards)}</aside>
    </div>
    <p class="vh" id="plot-readout" role="status" aria-live="polite"></p>
    <details class="atlas-list">
      <summary>All {len(pts)} locations as a list</summary>
      <!--
        The table needs 423px of intrinsic width for its five mono columns. At
        375 it got 327 and the surplus was destroyed rather than scrolled,
        because `html` carries `overflow-x: clip` to contain the travel
        animations. The Latitude column, which is the entire point of this
        chapter, was off the right edge of the phone with no way to reach it.

        `tabindex` makes the scroller keyboard-reachable, which a plain
        overflow container is not.
      -->
      <div class="plot-scroll" tabindex="0" role="region"
           aria-label="Race locations table, scrolls sideways">
        <table class="plot-table">
          <caption class="vh">Every race location, with event, best result and latitude</caption>
          <thead><tr><th scope="col">Location</th><th scope="col">Event</th>
          <th scope="col">Years</th><th scope="col">Best result</th>
          <th scope="col">Latitude</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </details>
  </div>
</section>"""


def beyond(c: dict, img: Img) -> str:
    peaks = c["mountainAchievements"]
    tallest = max(p["metres"] for p in peaks)
    cards = "".join(
        f"""<article class="peak">
      {img.tag(p['image'], '(min-width:760px) 46vw, 100vw') if p['image'] and img.get(p['image']) else ''}
      <p class="metres mono">{p['metres']:,}&#8202;m</p>
      <div class="scale" aria-hidden="true"><i style="width:{p['metres'] / tallest * 100:.1f}%"></i></div>
      <h3>{e(p['peak'])}</h3>
      <p class="country mono">{e(p['country'])}</p>
      <p>{e(p['note'])}</p>
    </article>"""
        for i, p in enumerate(peaks)
    )
    # Grouped into the route she actually took: climbing qualified her to
    # instruct, instructing put her on skis, skiing took her abroad. As one flat
    # list of seven it read as a CV dump and said none of that.
    steps = []
    for i, ph in enumerate(c["certificationPhases"]):
        items = [x for x in c["certifications"] if x["phase"] == ph["id"]]
        if not items:
            continue
        # A credential row: what it is and who issued it. Only one of the seven
        # certificates has a year recorded, so a year column would print six
        # blanks and look broken. The span of years lives on the card head
        # instead, where it covers the whole step.
        rows = "".join(
            f'<li><b>{e(x["title"])}</b>'
            f'<span class="cs-by mono">{e(x["body"])}</span></li>'
            for x in items
        )
        # Four identical black rectangles carrying only text is what made this
        # bland however well it moved. Each step now carries the photograph of
        # where it happened and is built like the credential it describes.
        shot = (
            f'<div class="cstep-shot">'
            f'{img.tag(ph["image"], "(min-width:820px) 34vw, 86vw")}'
            f'<span class="cstep-where mono">{e(ph["where"])}</span></div>'
            if ph.get("image") and img.get(ph["image"])
            else ""
        )
        steps.append(
            f'<li class="cstep" style="--n:{i}">'
            f"{shot}"
            f'<div class="cstep-body">'
            f'<span class="cstep-num" aria-hidden="true">{e(ph["index"])}</span>'
            f'<div class="cstep-head">'
            f'<span class="cstep-idx mono">Step {e(ph["index"])}</span>'
            f'<span class="cstep-years mono">{e(ph["years"])}</span></div>'
            f'<h4>{e(ph["label"])}</h4>'
            f'<p class="cstep-note">{e(ph["note"])}</p>'
            f'<ul class="cstep-items">{rows}</ul></div></li>'
        )
    certs = "".join(steps)
    return f"""
<section id="beyond">
  <div class="wrap">
    {section_head(c, "beyond")}
    <!--
      Container travels, cards do not. See the note on `.hl-figs`.
      Amplitude 0.3, not 0.5: at 0.5 the block rose 85px into a section heading
      whose bottom margin is 72px, so the two met by 13px at the ends of their
      travel. The heading cannot move down to meet it, since headings are
      horizontal-only for exactly this reason.
    -->
    <div class="peaks" data-travel="b-t" style="--amp:0.3">{cards}</div>
  </div>
  <div class="croute-run" id="croute-run" style="--steps:{len(steps)}">
    <div class="croute-stage">
      <div class="croute-head">
        <span class="eyebrow">Qualifications</span>
        <h3>In the order she earned them</h3>
      </div>
      <ol class="croute">{certs}</ol>
    </div>
  </div>
</section>"""


# Short names for the source column. `portfolio` is deliberately empty.
#
# It was briefly "Athlete", to stop the domestic rows looking unsourced. That
# stamped the word down fifteen rows and made those results read as second
# class next to FIS and Khelo India, and a source column is read as naming a
# publication, so it answered a different question than the header asks.
#
# The disclosure moved to the table's caption instead, which now says what a
# blank cell means. Once, under the table, rather than fifteen times inside it.
SOURCE_LABEL = {
    "fis": "FIS",
    "awg-wikipedia": "Asian Winter Games",
    "kiwg-2026": "Khelo India",
    "ap": "AP",
    "portfolio": "",
}


def result_row(r: dict, sources: dict) -> str:
    """Must match the row markup in main.js, which re-renders on interaction."""
    s = sources.get(r["sourceRef"], {})
    # The medal is named, not just coloured.
    #
    # It was a 9px dot with the word available only to screen readers, so a
    # sighted reader got a coloured circle and no key, and a touch reader had no
    # hover to fall back on. Naming it costs one word and removes the puzzle.
    medal = (
        f'<span class="medal-dot" data-medal="{e(r["medal"])}"></span>'
        f'<span class="medal-name">{e(r["medal"])}</span>'
        if r["medal"] else ""
    )
    # A source with a URL is a link a journalist can follow. One without is
    # still worth naming: these rows are domestic races nobody published, and
    # the blank cell read as missing data when the real answer is that she is
    # the source. Saying so is both honest and more useful than an empty cell.
    label = SOURCE_LABEL.get(r["sourceRef"], e(s.get("sourceName", "")))
    if s.get("sourceUrl"):
        link = (f'<a class="src-flag" href="{e(s["sourceUrl"])}" '
                f'target="_blank" rel="noopener">{label}</a>')
    elif label:
        link = (f'<span class="src-flag is-unlinked" '
                f'title="{e(s.get("sourceName", ""))}">{label}</span>')
    else:
        link = ""
    return f"""<tr>
          <td class="c-year">{e(r['year'] or '—')}</td>
          <td class="c-event">{e(r['event'])}<small>{e(r['detail'])}</small></td>
          <td class="c-place">{e(r['place'])}</td>
          <td class="c-mark">{e(r['mark'] or '—')}</td>
          <td class="c-medal">{medal}</td>
          <td>{link}</td>
        </tr>"""


def record(c: dict) -> str:
    res = c["results"]
    filters = "".join(
        f'<button type="button" data-filter="{e(f["id"])}" '
        f'aria-pressed="{"true" if f["id"] == "all" else "false"}">{e(f["label"])}</button>'
        for f in res["filters"]
    )
    seeded = "".join(
        result_row(r, c["sources"]) for r in res["rows"] if r["featured"]
    )
    return f"""
<section id="record">
  <div class="wrap">
    {section_head(c, "record")}
    <div class="filters" role="group" aria-label="Filter results">{filters}</div>
    <table class="results" id="results-table" aria-describedby="results-note">
      <!--
        The note used to live here as a `vh` caption, so it reached screen
        readers and no sighted reader at all. It is now a paragraph after the
        table, tied back with `aria-describedby` so it is still the table's
        description and is only announced once.

        Not a visible `<caption>`: with `caption-side: bottom` and a max-width
        it shrink-wrapped to 72px on a phone and stacked into 23 lines.
      -->
      <thead>
        <tr>
          <th scope="col">Year</th><th scope="col">Event</th>
          <th scope="col">Location</th><th scope="col">Result</th>
          <th scope="col"><span class="vh">Medal</span></th>
          <th scope="col">Source</th>
        </tr>
      </thead>
      <tbody id="results-body">{seeded}</tbody>
    </table>
    <p class="results-note" id="results-note">{e(res['note'])}</p>
    <div class="record-more">
      <button class="btn" type="button" id="results-toggle" aria-expanded="false">
        View full achievement record</button>
    </div>
  </div>
</section>"""


def media(c: dict, img: Img) -> str:
    """
    Press and the photographic archive in one place.

    They used to be two sections, which meant two nav entries for one idea.
    Bhavani asked for a single Media section filtered across everything, and she
    is right: a separate Gallery page was the weakest item in the old structure.
    One filter row now spans written coverage and photographs together.
    """
    # Coverage arrives two at a time, one from each side.
    #
    # Every row used to travel on its own, alternating left and right at a 468px
    # swing, so neighbouring rows sheared past each other while the reader was
    # trying to scan down a column of outlet names. Motion is worst exactly
    # there: this is the block someone skims for "Associated Press" and "The
    # Hindu".
    #
    # Now the pair is the unit. The two rows come in from opposite edges, close
    # on their resting positions as the pair reaches the middle of the frame,
    # and from that point sit still and scroll out like ordinary text. The
    # offset is one-sided, so nothing moves laterally once it is readable, and
    # the two rows are pushed apart rather than through each other, which is
    # what made the old arrangement collide.
    #
    # Each row carries a thumbnail from her own photo library, matched to what
    # the piece is about. Never the outlet's own article image: we have no
    # licence to those, and this section states outright that no publisher
    # photography is reproduced here.
    #
    # The slot is always emitted, even with nothing in it. The row is a grid and
    # its children are auto-placed, so an entry with no thumbnail used to drop
    # the whole row one column to the left: publication, headline, date and
    # context all started 104px inboard of every other row. Three of the
    # thirteen entries have no picture yet, which was enough to make the list
    # look like two different components.
    def press_row(p: dict, side: int) -> str:
        has_image = p.get("image") and img.get(p["image"])
        inner = img.tag(p["image"], "72px") if has_image else ""
        empty = "" if has_image else " is-empty"
        thumb = f'<span class="press-thumb{empty}">{inner}</span>'
        return (
            f'<div class="press-item" data-side="{side}">'
            f'<a href="{e(p["url"])}" target="_blank" rel="noopener">'
            f"{thumb}"
            f'<span class="press-pub">{e(p["publication"])}</span>'
            f'<span class="press-title">{e(p["title"])}</span>'
            f'<span class="press-date mono">{e(p["date"] or "")}</span>'
            f'<span class="press-context">{e(p["context"])}</span>'
            f"</a></div>"
        )

    rows = c["press"]
    press = "".join(
        f'<li class="press-pair" data-travel="b-t" style="--amp:0.4">'
        + "".join(press_row(p, -1 if n == 0 else 1)
                  for n, p in enumerate(rows[i:i + 2]))
        + "</li>"
        for i in range(0, len(rows), 2)
    )

    tiles, cats = [], []
    for i, (slot, _span) in enumerate(GALLERY):
        a = img.get(slot)
        if not a:
            continue
        cat = a.get("category") or "other"
        if cat not in cats:
            cats.append(cat)
        tiles.append(
            f'<button type="button" data-i="{i}" data-cat="{e(cat)}" '
            f'data-anim="clip" style="--i:{i % 4}" '
            f'aria-label="Open image: {e(a["alt"])}">'
            f'{img.tag(slot, "(min-width:1100px) 22vw, (min-width:700px) 30vw, 46vw")}'
            f'<span class="gal-cat mono">{e(cat)}</span></button>'
        )

    # No filter row.
    #
    # It offered All, Press and Photos over a list whose every item is tagged
    # `press`, because the photographs are not in that list at all: they are the
    # scrub below and the grid inside the disclosure. So All and Press returned
    # the identical ten rows and Photos returned nothing. Measured:
    #
    #     All 10, Press 10, Photos 0
    #
    # A control with one working state, one duplicate and one that empties the
    # page is worse than no control, and ten rows never needed filtering.
    chips = ""

    # ---- the scrubbed archive ----------------------------------------------
    # Twenty tiles in a grid is a wall you scan. Paired over a pinned ground and
    # advanced by scroll, the same photographs become a sequence you move
    # through, and the location and year get to carry weight instead of sitting
    # in a hover label.
    pairs, i = [], 0
    slots = [s for s, _ in GALLERY if img.get(s)]
    while i < len(slots):
        a_slot = slots[i]
        b_slot = slots[i + 1] if i + 1 < len(slots) else None
        a = img.get(a_slot)
        bits = [x for x in (a.get("location"), a.get("year")) if x]
        cap = " &middot; ".join(bits) if bits else a.get("category", "").title()
        # These two are hand-built rather than going through img.tag, and they
        # were the only images on the site missing their focal point. Every
        # frame in the archive was cropping from dead centre: the hero portrait
        # sat at 50% instead of 32%, which on a 960x1707 source in a 404x538
        # box is the difference between her face and her collar.
        b_tag = (
            f'<img class="shot-b" src="{e(img.src(b_slot, 480))}" alt="" '
            f'aria-hidden="true" loading="lazy" decoding="async" '
            f'style="object-position:{img.focal(b_slot)}">'
            if b_slot else ""
        )
        pairs.append(
            f'<figure class="scrub-frame" data-frame="{len(pairs)}"'
            f'{ON_FIRST if not pairs else ""}>'
            f'<img class="shot-a" src="{e(img.src(a_slot, 960))}" '
            f'alt="{e(a["alt"])}" loading="lazy" decoding="async" '
            f'style="object-position:{img.focal(a_slot)}">'
            f"{b_tag}"
            f'<figcaption class="mono">{cap}</figcaption></figure>'
        )
        i += 2

    # Without a heading the scrub read as photographs appearing for no stated
    # reason. It stays pinned with the frames so the reader always knows what
    # they are looking at.
    scrub = f"""
    <div class="scrub" id="scrub" style="--steps:{len(pairs)}">
      <div class="scrub-stage">
        <div class="scrub-ground" aria-hidden="true">
          {img.tag('track-texture', '100vw')}
        </div>
        <div class="scrub-head">
          <span class="eyebrow">The archive</span>
          <h3>Six seasons, photographed</h3>
        </div>
        <div class="scrub-frames">{''.join(pairs)}</div>
        <p class="scrub-count mono" id="scrub-count" aria-hidden="true">
          01 / {len(pairs):02d}</p>
      </div>
    </div>"""

    return f"""
<section id="media">
  <div class="wrap">
    {section_head(c, "media")}
    <ul class="press-list" id="press-list">{press}</ul>
  </div>
  {scrub}
  <div class="wrap">
    <details class="atlas-list" id="gal-all">
      <summary>All {len(tiles)} photographs as a grid</summary>
      <div class="gal" id="gal">{''.join(tiles)}</div>
    </details>
    <p class="vh" id="gal-status" role="status" aria-live="polite"></p>
  </div>
</section>

<div class="lb" id="lightbox" role="dialog" aria-modal="true" aria-label="Image viewer" data-open="false">
  <div class="lb-bar">
    <span class="mono" id="lb-count">1 / {len(tiles)}</span>
    <button class="lb-close" id="lb-close" aria-label="Close viewer">&#10005;</button>
  </div>
  <div class="lb-stage"><img id="lb-img" alt=""></div>
  <div class="lb-foot">
    <div>
      <p class="lb-cap" id="lb-cap"></p>
      <span class="lb-credit mono" id="lb-credit"></span>
    </div>
    <div class="lb-nav">
      <button id="lb-prev" aria-label="Previous image">&#8592;</button>
      <button id="lb-next" aria-label="Next image">&#8594;</button>
    </div>
  </div>
</div>"""


def season_calendar(s: dict) -> str:
    """
    The shape of a season, October to March.

    A sponsor's first question is what the money is actually for, and a list of
    four categories does not answer it. Every span here is read off her own FIS
    record rather than a generic calendar.
    """
    n = len(s["months"])
    months = "".join(
        f'<span class="cal-month mono">{e(m)}</span>' for m in s["months"]
    )
    bands = "".join(
        f'<li class="cal-band" data-kind="{e(b["kind"])}" '
        f'style="--from:{b["from"] / n * 100:.2f}%;--span:{(b["to"] - b["from"]) / n * 100:.2f}%">'
        f'<span class="cal-bar"></span>'
        f'<span class="cal-label">{e(b["label"])}</span>'
        f'<span class="cal-need mono">{e(b["need"])}</span>'
        f"</li>"
        for b in s["bands"]
    )
    return f"""
    <figure class="calendar" data-anim="up">
      <figcaption class="cal-note mono">{e(s['note'])}</figcaption>
      <div class="cal-scale" aria-hidden="true">{months}</div>
      <ul class="cal-bands">{bands}</ul>
    </figure>"""


def speaking(c: dict) -> str:
    s = c["speaking"]
    # The travel goes on the container, not on the cards.
    #
    # Moving them individually collided twice over. Horizontally, two cards
    # sharing a row went 208px in opposite directions across a 64px gutter, so
    # one card's body text ran under the other's heading. Vertically was no
    # better: a card entering is pushed down while the card above it is leaving
    # and pushed up, which closed a 48px row gap by 144px.
    #
    # Any grid of siblings does this. The block moves as one piece instead, and
    # the layout inside it can never change.
    # Each talk closes on the thing in her record it is drawn from.
    #
    # Deliberately not more motion. This section sits between the photo scrub,
    # which is the heaviest movement on the page, and the season calendar, and
    # it is the one place a reader is asked to sit and read four things. It was
    # animated once and the cards collided; the complaint that followed was that
    # there were too many moving elements, not too few.
    #
    # What the cards actually lacked was evidence. A title and a sentence say
    # what a talk is about. The line underneath says it is backed by something
    # she did, and every one of those facts is already stated and sourced
    # elsewhere on this page.
    themes = "".join(
        f'<article class="theme">'
        f'<span class="theme-idx mono">{i + 1:02d}</span>'
        f'<h3>{e(x["title"])}</h3><p>{e(x["body"])}</p>'
        f'<p class="theme-from mono">{e(x["from"])}</p></article>'
        for i, x in enumerate(s["themes"])
    )
    # Four talks, one statement, one way to ask. That is the whole section.
    #
    # It carried a formats table and a three-point case for booking her, and
    # both are gone. The formats named a keynote, a school assembly, a fireside
    # and a half-day workshop; I wrote those, and nothing in the source material
    # or the press says she has delivered any of them, so the block implied a
    # speaking history that has not been established. The three-point case was
    # advocacy, and a page that states facts everywhere else has no business
    # arguing on her behalf here.
    #
    # `s["audiences"]` stays unrendered for the reason it was dropped before: a
    # list reading "Corporates, Schools, Universities" tells a reader nothing
    # they had not worked out. It stays in the file in case a list of real past
    # audiences ever replaces it, which would be evidence.
    return f"""
<section id="speaking">
  <div class="wrap">
    {section_head(c, "speaking")}
    <!-- 0.3 for the same reason as `.peaks`: it was meeting the heading above. -->
    <div class="themes" data-travel="b-t" style="--amp:0.3">{themes}</div>
    <!--
      The closing statement, centred and travelling up. It earns the three words
      in the section title and replaces two columns that were arguing for her.
    -->
    <div class="speak-end">
      <p class="speak-close" data-travel="b-t" style="--amp:0.5">{e(s['close'])}</p>
      <div class="hero-ctas">
        <!--
          Lands in Work with me and arms the enquiry form with the right
          subject, so a school arrives at a form that already knows what it is
          there for. `data-topic` is read by initEnquiry; without JavaScript it
          is still an ordinary anchor to the section.
        -->
        <a class="btn btn-primary" href="{e(s['cta']['href'])}"
           data-topic="{e(s['cta']['topic'])}">{e(s['cta']['label'])}</a>
      </div>
      <p class="speak-avail mono">{e(s['availability'])}</p>
    </div>
  </div>
</section>"""


def partners(c: dict) -> str:
    p = c["partnership"]
    # Each need can carry a `cost`, and renders it when one is there.
    #
    # Nothing here invents a figure. A sponsor cannot approve "travel", so this
    # section is describing four costs and pricing none of them, which is the
    # largest gap left on the site. The slot exists so the numbers can be
    # dropped into `content/bhavani.json` the day Bhavani supplies them, without
    # anybody touching markup. Until then the cards read exactly as before.
    areas = "".join(
        f"""<article class="area" data-travel="{("br-tl", "bl-tr")[i % 2]}"
      style="--amp:0.85">
      <span class="idx mono">{e(a['index'])}</span>
      <h3>{e(a['title'])}</h3>
      <p>{e(a['body'])}</p>
      {f'<p class="area-cost mono">{e(a["cost"])}</p>' if a.get("cost") else ''}
    </article>"""
        for i, a in enumerate(p["areas"])
    )
    cal = season_calendar(p["season"]) if p.get("season") else ""

    # Permission to use both marks was confirmed on 11 Aug 2026. Each entry
    # renders its logo when the file is present and falls back to the name set in
    # the display face when it is not, so the section is correct either way and
    # upgrades itself the moment the artwork lands.
    cur = p["current"]
    rows = []
    for i, x in enumerate(cur["list"]):
        name = e(x["name"])
        body = f"<b>{name}</b>"
        logo = x.get("logo")
        if logo and (ROOT / "assets" / "img" / "partners" / logo).exists():
            # No per-logo scale. The two marks have very different aspect ratios
            # and hand-tuned heights are exactly what made the row look
            # lopsided. Identical plates and `object-fit: contain` do the
            # normalising, which is more correct and one less thing to get wrong
            # when a third partner arrives.
            body = (
                f'<span class="partner-plate">'
                f'<img class="partner-logo" src="assets/img/partners/{e(logo)}" '
                f'alt="{name}" loading="lazy" decoding="async">'
                f"</span>"
            )
        # What each supporter actually does. Two logos and a category label is a
        # wall; naming the work is what tells the next sponsor the first two
        # were real arrangements rather than decoration.
        role = x.get("role")
        role_html = f'<p class="partner-role">{e(role)}</p>' if role else ""
        rows.append(
            f'<li data-anim="up" style="--i:{i}">{body}'
            f'<span class="mono">{e(x["kind"])}</span>{role_html}</li>'
        )
    names = "".join(rows)
    # `p["openTo"]` is deliberately not rendered.
    #
    # Five chips reading Sponsorship, Brand partnerships, Campaigns, Product
    # collaborations and Athlete partnerships. Every athlete alive is open to all
    # five, so they told a sponsor nothing and spent five items of attention
    # doing it. Same fault as the "Where she speaks" chips that came out of the
    # speaking section, and the same decision applies here.
    current = f"""
    <div class="current-partners">
      <h3 class="eyebrow">{e(cur['note'])}</h3>
      <ul class="partner-names">{names}</ul>
    </div>"""

    return f"""
<section id="partners">
  <div class="wrap">
    {section_head(c, "partners")}
    {current}
    <!--
      What support buys, then when it lands. The calendar used to come first,
      which told a reader when money was needed before they knew there were four
      separate things it was needed for. The bar is the better exhibit but it
      only means something once the costs have names.
    -->
    <!--
      The four needs had no heading at all, so they read as a continuation of
      the current-supporters list above them. A sponsor scanning could not tell
      where "who already backs her" ended and "what is still unfunded" began.
    -->
    <h3 class="eyebrow">What support funds</h3>
    <div class="areas">{areas}</div>
    {cal}
    <div class="hero-ctas" style="margin-top:2.5rem">
      <!-- Same route as the speaking button: into Work with me, with the
           enquiry subject already set. It used to be a mailto, which skipped
           the page's own form and arrived unlabelled. -->
      <a class="btn btn-primary" href="{e(p['cta']['href'])}"
         data-topic="{e(p['cta']['topic'])}">{e(p['cta']['label'])}</a>
    </div>
    <!--
      The budget disclosure that used to sit here is gone. It answered a
      question nobody had asked and drew attention to a figure that is not on
      the page. The reasoning is still recorded in `withheld`.
    -->
  </div>
</section>"""


def contact(c: dict) -> str:
    k = c["contact"]
    # One route in, sorted at the door. Beats five separate enquiry forms, which
    # is the other way this usually gets built.
    topics = "".join(f"<option>{e(t)}</option>" for t in k["categories"])
    ig_row = ""
    if k["instagramHandle"]:
        target = (
            f'href="{e(k["instagramUrl"])}" target="_blank" rel="noopener"'
            if k["instagramVerified"]
            else f'href="{e(k["instagramUrl"])}" target="_blank" rel="noopener" '
                 f'title="Link constructed from the handle and not yet confirmed"'
        )
        ig_row = f"""<li><a {target}>
        <span class="k">Instagram</span><span class="v">@{e(k['instagramHandle'])}</span></a></li>"""
    return f"""
<section id="contact">
  <div class="wrap">
    {section_head(c, "contact")}
    <div class="contact-grid">
      <ul class="contact-lines">
        <li><a href="mailto:{e(k['email'])}"><span class="k">Email</span>
          <span class="v">{e(k['email'])}</span></a></li>
        <!--
          The phone number is deliberately not published. It is still in
          `contact.phone` for whoever handles enquiries, but a personal mobile
          on a page built to attract strangers is a decision that cannot be
          taken back once it has been crawled. Email and the form are the two
          routes in, and both reach the same inbox.
        -->
        {ig_row}
      </ul>
      <form class="enquiry" id="enquiry" novalidate>
        <label>Name<input type="text" name="name" autocomplete="name"></label>
        <label>Organisation<input type="text" name="org" autocomplete="organization"></label>
        <label>Email<input type="email" name="email" autocomplete="email"></label>
        <label>What is this about?<select name="topic" id="enquiry-topic">{topics}</select></label>
        <label>Message<textarea name="message" rows="4"></textarea></label>
        <!--
          The honeypot. Off-screen, hidden from assistive tech and out of the
          tab order, so no person ever meets it. A bot fills every field it
          finds, so anything arriving with this one set is discarded server
          side. Cheaper than a CAPTCHA and it asks nothing of the reader.
        -->
        <label class="hp" aria-hidden="true">Website
          <input type="text" name="website" tabindex="-1" autocomplete="off"></label>
        <button class="btn" type="submit">Send enquiry</button>
        <!--
          This note used to open "This form is a prototype. It has no backend
          and does not send anything." Every sponsor, school and festival
          producer who reached the end of the page was told the way in was
          broken. The form is not broken: it opens the reader's own mail client
          with all five fields already written into the message. That is worth
          describing as behaviour rather than apologising for.
        -->
        <!--
          The note is empty until the form has something to report.
          Explaining the delivery mechanism before anyone has pressed anything
          answered a question nobody had asked and made the section end on
          plumbing. initEnquiry still writes into it: "Sending…", then either
          the sent confirmation or the mail-client fallback.
        -->
        <p class="note" id="enquiry-note" aria-live="polite"></p>
      </form>
    </div>
  </div>
</section>"""


def footer(c: dict) -> str:
    return f"""
<footer class="foot">
  <div class="wrap foot-inner">
    <span>&copy; {e(c['meta']['lastReviewed'][:4])} {e(c['identity']['fullName'])}</span>
    <!--
      "Results follow her FIS record" removed at the client's request. The
      provenance is not lost: the FIS athlete biography is still linked from the
      nav as the last item, and every result row still carries its sourceRef.
    -->
    <a href="#top">Back to start</a>
  </div>
  <!--
    The rights line lived here for one round and is gone at the client's
    request. It said that headlines link out and that no article text or
    publisher photography is reproduced. Both are still true of how the press
    list is built, and the constraint is enforced in press_row, which never
    emits an outlet's own article image. It is simply no longer stated on the
    page. Restore this if scanned tear sheets are ever cleared and published,
    because at that point the claim would stop being true as written.
  -->
</footer>"""


# ------------------------------------------------------------------ journal

JOURNAL_DIR = CONTENT / "journal"


def parse_post(path: pathlib.Path) -> dict | None:
    """
    One markdown file with a frontmatter block into a post dict.

    Deliberately not YAML. The frontmatter is `key: value` lines and nothing
    else, so Bhavani can edit it without learning a syntax and a stray colon
    cannot break the build.
    """
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return None
    _, fm, body = raw.split("---", 2)

    meta: dict[str, str] = {}
    for line in fm.strip().splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip().lower()] = v.strip()

    if not meta.get("title") or not meta.get("date"):
        return None

    md = MarkdownIt("commonmark")
    html_body = md.render(body.strip())

    summary = meta.get("summary", "")
    if not summary:
        for para in body.strip().split("\n\n"):
            if para.strip() and not para.startswith(("#", "-", "```")):
                summary = " ".join(para.split())
                break

    return {
        "slug": path.stem,
        "title": meta["title"],
        "date": meta["date"],
        "summary": summary,
        "image": meta.get("image") or None,
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "draft": meta.get("draft", "false").lower() == "true",
        "html": html_body,
    }


def load_posts(include_drafts: bool = False) -> list[dict]:
    if not JOURNAL_DIR.exists():
        return []
    posts = []
    for p in sorted(JOURNAL_DIR.glob("*.md")):
        if p.name.startswith("_"):
            continue
        post = parse_post(p)
        if post and (include_drafts or not post["draft"]):
            posts.append(post)
    return sorted(posts, key=lambda x: x["date"], reverse=True)


def pretty_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        months = ("January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December")
        return f"{d} {months[m - 1]} {y}"
    except (ValueError, IndexError):
        return iso


def sub_page(c: dict, version: str, title: str, body: str, depth: int = 0) -> str:
    """
    Shell for pages that are not the homepage.

    `depth` is how many folders down the page sits, so asset paths resolve from
    both `journal.html` and `journal/<slug>.html` without absolute URLs. That
    keeps the whole site portable to any subdirectory.
    """
    up = "../" * depth
    seo = c["seo"]
    ident = c["identity"]
    links = "".join(
        f'<li><a href="{up}index.html#{sid}">{e(label)}</a></li>'
        for sid, label in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | {e(ident['shortName'])}</title>
<meta name="description" content="{e(seo['description'])}">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Was a second, hand-maintained copy of the font URL that had already drifted
     out of step with FONTS. It now renders from the same constant, so a font
     change is one edit rather than two. -->
<link rel="stylesheet" href="{e(FONTS)}">
<link rel="stylesheet" href="{up}assets/css/site.css?v={version}">
<script>document.documentElement.classList.add("js")</script>
</head>
<body class="subpage">
<a class="skip" href="#main">Skip to content</a>
<header class="nav is-solid" id="nav">
  <a class="nav-mark" href="{up}index.html">{e(ident['wordmark'])}<span>{e(ident['descriptor'])}</span></a>
  <nav aria-label="Sections"><ul class="nav-links">{links}
    <li><a href="{up}journal.html" aria-current="page">Journal</a></li></ul></nav>
</header>
<main id="main">{body}</main>
<footer class="foot">
  <div class="wrap foot-inner">
    <span>&copy; {e(c['meta']['lastReviewed'][:4])} {e(ident['fullName'])}</span>
    <a href="{up}index.html">Back to the site</a>
  </div>
</footer>
<script defer src="{up}assets/js/main.js?v={version}"></script>
</body>
</html>
"""


def journal_index(c: dict, img: Img, posts: list[dict], version: str) -> str:
    if posts:
        cards = "".join(
            f"""<li class="jcard">
        <a href="journal/{e(p['slug'])}.html">
          {('<div class="jcard-shot">' + img.tag(p['image'], '(min-width:900px) 34vw, 100vw') + '</div>') if p['image'] and img.get(p['image']) else ''}
          <time class="mono" datetime="{e(p['date'])}">{e(pretty_date(p['date']))}</time>
          <h2>{e(p['title'])}</h2>
          <p>{e(p['summary'])}</p>
        </a>
      </li>"""
            for p in posts
        )
        listing = f'<ul class="jlist">{cards}</ul>'
    else:
        listing = """<p class="jempty">Nothing published yet. The first entries go up
      during the next race block.</p>"""

    body = f"""
<section id="journal-top">
  <div class="wrap">
    <div class="section-head" data-anim="up" data-aside="false">
      <span class="idx mono">10</span>
      <h2>Journal</h2>
      <p class="lede">Racing, training, travel and the parts of a season that do not
      appear in a results table. Written by Bhavani.</p>
    </div>
    {listing}
  </div>
</section>"""
    return sub_page(c, version, "Journal", body, depth=0)


def journal_post(c: dict, img: Img, p: dict, prev_p, next_p, version: str) -> str:
    shot = ""
    if p["image"] and img.get(p["image"]):
        shot = f'<figure class="jhero">{img.tag(p["image"], "100vw", up="../")}</figure>'
    tags = "".join(f'<li>{e(t)}</li>' for t in p["tags"])
    nav_links = []
    if next_p:
        nav_links.append(
            f'<a class="jnav-prev" href="{e(next_p["slug"])}.html">'
            f'<span class="mono">Previous</span>{e(next_p["title"])}</a>'
        )
    if prev_p:
        nav_links.append(
            f'<a class="jnav-next" href="{e(prev_p["slug"])}.html">'
            f'<span class="mono">Next</span>{e(prev_p["title"])}</a>'
        )
    body = f"""
<article class="post">
  <div class="wrap">
    <p class="post-back"><a href="../journal.html">&#8592; All journal entries</a></p>
    <time class="mono post-date" datetime="{e(p['date'])}">{e(pretty_date(p['date']))}</time>
    <h1>{e(p['title'])}</h1>
    {f'<ul class="jtags">{tags}</ul>' if tags else ''}
  </div>
  {shot}
  <div class="wrap post-body">{p['html']}</div>
  <div class="wrap"><nav class="jnav">{''.join(nav_links)}</nav></div>
</article>"""
    return sub_page(c, version, p["title"], body, depth=1)


# -------------------------------------------------------------------- build

def data_script(c: dict, lib: dict) -> str:
    by_slot = {i["slot"]: i for i in lib["images"]}
    gal = []
    for slot, span in GALLERY:
        a = by_slot.get(slot)
        if not a:
            continue
        gal.append({
            "slot": slot,
            "alt": a["alt"],
            "credit": a["credit"],
            "year": a["year"],
            "location": a["location"],
            "category": a["category"],
            "full": f"{lib['meta']['basePath']}/{a['file']}-{a['widths'][-1]}.webp",
        })

    payload = {
        "results": c["results"],
        "sources": c["sources"],
        "footprint": c["internationalFootprint"],
        "gallery": gal,
        "railStops": [s for s, _ in RAIL_STOPS],
    }
    # Travels inside the document rather than as a second file, so it can never
    # be served stale against a fresh index.html and the page needs no server.
    # `<` is escaped so a string in the data can never close the script element.
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    blob = blob.replace("<", "\\u003c")
    return f'<script type="application/json" id="site-data">{blob}</script>'


def main() -> int:
    c = load("bhavani.json")
    lib = load("images.json")
    world = load("worldmap.json")
    img = Img(lib)
    check_sections(c)

    # The canonical link and the Open Graph tags need an absolute address, and
    # it changes the day a custom domain is attached. Overridable so that does
    # not mean editing JSON:  python build.py --site-url https://example.com
    if "--site-url" in sys.argv:
        url = sys.argv[sys.argv.index("--site-url") + 1].rstrip("/") + "/"
        c["seo"]["siteUrl"] = url
        print(f"site url  {url}")
    version = asset_version(ROOT / "assets" / "css" / "site.css",
                            ROOT / "assets" / "js" / "main.js")

    posts = load_posts(include_drafts="--drafts" in sys.argv)

    # `career()` returns two sections: the record, which closes chapter one, and
    # the ambition block, which is placed much later. See the note there.
    journey_html, ambition_html = career(c, img)

    page = "".join([
        head(c, img, version),
        rail(),
        nav(c, has_journal=bool(posts)),
        '\n<main id="main">',
        hero(c, img),
        headline(c, img),
        profile(c, img),
        proof(c),
        sport(c),
        story(c, img),
        journey_html,
        footprint(c, world, img),
        beyond(c, img),
        record(c),
        media(c, img),
        # The turn. Everything before it happened; everything in it is intended.
        # It sits after the press so a reader reaches the goal having already
        # seen the evidence and who else vouches for it, and immediately before
        # the offer and the ask, which are the two questions it raises.
        ambition_html,
        speaking(c),
        partners(c),
        contact(c),
        "\n</main>",
        footer(c),
        "\n",
        data_script(c, lib),
        f'\n<script defer src="assets/js/main.js?v={version}"></script>\n</body>\n</html>\n',
    ])

    OUT_HTML.write_text(page, encoding="utf-8")

    # ---- journal -----------------------------------------------------------
    jdir = ROOT / "journal"
    if jdir.exists():
        shutil.rmtree(jdir)
    (ROOT / "journal.html").write_text(
        journal_index(c, img, posts, version), encoding="utf-8"
    )
    if posts:
        jdir.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(posts):
            prev_p = posts[i - 1] if i > 0 else None
            next_p = posts[i + 1] if i + 1 < len(posts) else None
            (jdir / f"{p['slug']}.html").write_text(
                journal_post(c, img, p, prev_p, next_p, version), encoding="utf-8"
            )
    drafts = len(load_posts(include_drafts=True)) - len(load_posts())
    print(f"journal    {len(posts)} published, {drafts} draft"
          f"{'' if drafts == 1 else 's'}")

    # Superseded by the inline data script. Removed so a stale copy cannot be
    # picked up by an older cached index.html.
    legacy = ROOT / "assets" / "js" / "data.js"
    if legacy.exists():
        legacy.unlink()

    print(f"index.html   {len(page) / 1024:6.1f} KB   assets v{version}")
    print(f"milestones {len(c['careerMilestones'])}  results {len(c['results']['rows'])}  "
          f"places {len(c['internationalFootprint'])}  images {len(lib['images'])}  "
          f"withheld {len(c['withheld'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
