# Design plan

## The idea

Her career is defined by distance, and cross-country skiing is the one sport that
measures exactly that. So the site is organised around distance rather than around
"journey".

The organising device is **temperature**. The page starts warm — the ink is
warm-black, the accents are the stone and moss greys sampled out of the Bengaluru
roller-ski photograph — and cools continuously as you scroll, ending at an
Arctic near-black at Ruka. Kodagu sits at 12°N and has never had snow. Ruka sits
at 66°N inside the Arctic Circle. The page travels that distance and the reader
feels it as a colour temperature shift rather than as a sentence claiming it.

## Palette, derived from the photographs

Sampled with `scratchpad/palette.py` and `accent.py` over the ten strongest
assets, not chosen from a mood board.

| Token | Value | Where it came from |
|---|---|---|
| `--ink` | `#06090F` | the cold blacks of `track-texture`, pushed deeper |
| `--navy` | `#0E1C33` | `team-with-skis` `#0E1C40` |
| `--india` | `#2056DE` | the actual race-suit blue, 26% of `hero-portrait` |
| `--glacier` | `#9DCCF3` | dominant sky/snow blue in `track-texture` |
| `--snow` | `#E6EFF4` | `hero-portrait` `#E0EEF0` |
| `--race` | `#C6E82B` | Fischer ski and Leki pole green, hue 72° |
| `--stone` | `#8E8474` | Kodagu warm neutral from `roller-vidhana-soudha` |
| `--moss` | `#5E735B` | same image, the plantation greens |
| `--saffron` | `#E4761B` | flag moments only, three uses on the whole page |

The accent matters most. Sampling proved that the only saturated non-blue family
present in real volume across her photographs is the yellow-green of her skis and
poles. It is the one colour on the site that is hers rather than the sport's, so
it carries the track head, the checkpoint markers and nothing else.

The blue dominance is the main design risk. Everything she is photographed in is
blue, which is precisely the "generic blue sports UI" the brief rules out. The
temperature gradient is the answer: blue is allowed to be the international
sections' colour because the earlier sections are demonstrably not blue.

## Type

- **Archivo** variable (`wght` 400–900, `wdth` 62–125) for display. Condensed
  where the PDF was condensed, but it can relax its width for headings, which the
  PDF's single compressed face could not.
- **Newsreader** variable for narrative body. A serif is what makes it read as
  documentary rather than as a sports landing page, and it is the fastest way to
  get away from the default AI pairing.
- **IBM Plex Mono** for every figure: times, ranks, distances, latitudes, section
  indices, dates. This is the race-bib and timing-sheet layer.

Not every heading is uppercase. The wordmark and section indices are; section
titles are sentence case.

## The Track

The first version was a progress bar with dots on it, which is what every site
has. What makes it hers is that the geometry changes with what the page is
saying, so the rail is a picture of the career rather than a measure of how far
you have scrolled.

Three terrain states, tied to real section offsets rather than to fractions of
the page:

- Above the career section there is no cut track at all, only a dotted line of
  travel down the centre at `x=38`. She has not reached snow yet.
- At the career section the single line splays over 14px into two parallel
  grooves at `x=30` and `x=46`, classic-track spacing. The track is now cut.
- From the footprint section down, short markers appear beside the right groove
  at 72px intervals, the way course boards sit beside a race piste. Drawn across
  the grooves instead of beside them they read as ladder rungs.

The progress head is two skis, not one line. Each is a 20px segment on its own
groove, and they trade the lead by up to 7px as you scroll, which is the
diagonal stride. The offset comes from scroll distance, not from a timer, so it
only moves when the reader moves. Before the splay both skis sit on the centre
line together.

In the career section the same two grooves widen into the page and become the
timeline spine, with milestones branching right off it. On mobile the rail is
hidden and that spine is the Track.

The rail's SVG deliberately has no `viewBox`, so its user units are CSS pixels
and the terrain can be laid out directly against measured section offsets.

Understandable with motion off: position is derived from scroll offset, not
animated, so under `prefers-reduced-motion` it still shows where you are.

## The footprint plot

Not a world map with pins. An equirectangular plot: x is longitude, y is
latitude, with a labelled graticule and named marks for the Arctic Circle and the
Tropic of Cancer. Because the whole point is the 105° of latitude between Corralco
and Ruka, plotting latitude directly says the thing a coastline map would bury.

It is titled as a plot rather than dressed up as a map, so there is no uncanny
"map missing its continents" effect. A visually-hidden table carries every point
for screen readers and for motion-free use.

## Layout rules

- No cards. Full-bleed image bands, hairline rules, and a strict left-ranged grid.
- Results are a real `<table>`, styled as a start list. That is what the data is.
- Section markers are mono indices (`01`…`10`) plus a large ranged-left year or
  title. The PDF's oversized medal clip-art has no equivalent here; medals appear
  as one-character marks in a results row.
- Rounded corners appear nowhere except the two pill filters, which need to read
  as controls.

## One chronology, two tempos

The story and the career used to be separate sections. Both opened in 1995, so
the reader walked 1995 to 2022 as narrative and was then sent back to 1995 to
walk it again as a list, with Kodagu, the NCC parade and the New Zealand
certification told twice. A rewind in the middle of the site.

They are now one section, `Kodagu to Davos`, in two movements:

- 1995 to 2022 as pinned chapters, image-led, about a screen per beat. This is
  the half that has to persuade.
- 2022 to 2026 as the track-spine timeline, dense and scannable. This is the
  half that has to be checkable.

The three duplicated milestones are gone from the timeline, which now starts
where FIS starts scoring her, in January 2022.

A hinge sits between the movements and states why the tempo changes: before that
date there is no official record to point at, and after it every start is
counted. The temperature ladder runs inside the section rather than between two
of them, warm through the chapters and cool from the hinge down.

At 9.8 screens it is about 40% of the page. That is defensible only because the
tempo genuinely changes; if both halves ran at chapter pace it would drag.

## Pinned chapters, and why not the way Leclerc does it

The story section pins its media column and cross-fades a frame per beat while
the text advances beside it. That pacing was taken from `charlesleclerc.com`,
which is the reference the client pointed at.

What was not taken is how that site achieves it. Measured on the live page:

```
document scrollHeight   720px   ← exactly one viewport
scrollTo(0, 3000)       →  0    ← the document cannot move
```

On desktop it does not scroll at all. Every chapter is absolutely positioned at
`top: 0`, stacked, and cross-faded by a wheel handler. That costs the scrollbar,
keyboard paging, find-in-page, scroll restoration, and any deep link into the
middle of the page. The brief bans scroll hijacking outright, and their own
mobile build abandons it in favour of tall spacers with pinned panels.

So the honest version is what is built here: `position: sticky` on the media
column, real document scroll, one beat per screen at `min-height: 88vh`. The
pinning is CSS and works before any script runs. JavaScript only decides which
frame is showing, and the first frame is marked in the markup, so a reader
without JavaScript sees a photograph rather than an empty pane. Below 900px it
collapses to a plain stack in reading order.

Two beats have no photograph that honestly belongs to them, the 2016 Republic
Day parade and watching Pyeongchang in 2018. Those frames show the year set
large instead of borrowing an image from somewhere else.

## Motion

One orchestrated hero entrance: the image settles from a 6% scale, the two lines
of the name clip up 110ms apart, and the supporting metadata follows. Nothing
else in the hero moves.

Everything below the hero uses exactly two reveals, declared as `data-anim` in
the markup:

- `up` for text, rows and cards. Rise 16px and fade, 620ms.
- `clip` for photographs. Wipe up from the lower 22% of the frame, 780ms.

What keeps 84 animated elements from becoming noise is the constraints, not the
count. Each element runs once and is then unobserved. Nothing scales, rotates or
blurs. The stagger is 55ms and caps at six steps, so a row of gallery tiles
ripples but a fourteen-item timeline does not, because those items are far apart
vertically and each arrives alone. Long lists carry no stagger at all.

Two section-level moves carry the descent:

- Each section paints a band of the previous section's ground across its own top
  edge, so the warm-to-cold temperature change reads as a slope rather than as a
  hard step at every boundary. Pure CSS, no scroll cost.
- The hairline rule above each section heading draws in from the left over 900ms,
  which echoes the track being cut rather than simply appearing.

No parallax, no scroll hijack, no autonomous loops, nothing that delays reading.
All of it sits behind `prefers-reduced-motion` and behind the `anim-off` escape
hatch, and the resting state of every animated element is visible.
