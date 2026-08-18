# Reference synthesis

One reference so far: `charlesleclerc.com`, supplied by the client as the quality
bar. Studied live on 11 Aug 2026 by driving the site and reading its DOM, rather
than from screenshots, so the numbers below are measured.

---

## How the site is built

```
document scrollHeight   720px   ← exactly one viewport, on desktop
scrollTo(0, 3000)       →  0    ← the document cannot move
18 sections, 320 elements carrying will-change
Tailwind. No GSAP, no Locomotive, no Lenis, no Swiper.
```

On desktop it does not scroll. Every chapter is absolutely positioned at
`top: 0`, stacked, and cross-faded by a wheel handler. On mobile the hijack is
abandoned in favour of `h-[400vh]` spacers with pinned panels, which is the
honest version of the same effect.

The repeating unit is a triplet:

1. a `400vh` spacer, mobile only, which is the scroll runway
2. a pinned full-viewport backdrop carrying one pull quote
3. content panels that scroll past it

Two of those pull quotes: "It's the mind that makes the difference" and "It's
more about hard work than talent."

---

## The full run, top to footer

Scrolled end to end on 11 Aug 2026. In order:

1. Hero. `BEYOND SPEED` in giant condensed type, locked in place while clips
   cross-fade behind it. Angular panels wipe across during each change.
2. Chapter opener. Small label bottom-left with a bullet, a rule, and large body
   text on the right. Very little on screen at once.
3. Stat cluster. Three rounded panels, `GENERAL INFOS`, `STATS` and a third
   holding team, helmets and race number. They sit at different vertical offsets
   and move at different rates as you scroll, so the group has depth. Figures set
   huge and condensed: 184, 57, 9, 30.
4. Pull quote. `IT'S THE MIND THAT MAKES THE DIFFERENCE` set enormous and
   scrolling horizontally, right to left, driven by vertical scroll, over a
   pinned blurred backdrop. Red angular panels enter and leave around it.
5. Karting chapter. Pull quote, portrait, body text, and a `KART RESULTS` card
   with prev and next arrows stepping through years.
6. Second pull quote, `IT'S MORE ABOUT HARD WORK THAN TALENT`, resolving on the
   single word `TALENT` held large over a close-up of an eye.
7. `THE WORLD OF FERRARI` chapter, then an audio card: a still, a title, a
   duration of `00:00 — 00:42`, and a play button. Team radio from Monaco 2024.
8. The best thing on the site. A pinned night-circuit backdrop, dark and almost
   abstract, with two floating photographs at different sizes over it and a
   caption underneath. Scrolling swaps both photographs and the caption:
   `Bahrain - March 2019`, then `Monza - September 2024`. A scrubbed archive
   rather than a grid.
9. `LIFE AS A DRIVER` in giant stacked type, then four cards: training,
   preparation, racing, off-season.
10. Footer. Large wordmark, three link columns, social row, `EN IT FR`, and
    photo credits given by handle: `© Photo @antoinetruchet @race.service ...`

Persistent throughout: the CL16 mark in a white notch top-left, a `CHAPTERS`
dropdown, a hamburger, `SCROLL TO EXPLORE` pinned centre, and a blue `+` button
bottom-right.

## Pattern matrix

| Pattern | Why it works | Adaptation for Bhavani | Do not copy |
|---|---|---|---|
| Giant condensed type locked over full-bleed media while the media changes behind it | The name is never not on screen, and the motion happens behind it rather than to it | Already close. The hero burst changes media behind a fixed wordmark | Their type is so large it clips its own descenders |
| Angular parallelogram wipes between media frames | Reads as speed, and is specific to motorsport | Adapt the shape: a ski track is two parallel grooves, so the wipe should be a shallow diagonal, not a hard slant | The literal slant, which is a racing-livery cue and belongs to them |
| Persistent chapter label in a fixed left column | You always know which chapter you are in | The Track rail already does this, with checkpoints | Their label is text only, ours carries the sport |
| `400vh` runway per chapter with a pinned backdrop | Gives one idea four screens to land | Fits the world map: pin the map, advance the place cards | Applying it to every section, which is why their site is 18 sections long |
| Floating CTA anchored bottom-right, always visible | Conversion is never more than one click away | Straight adoption. Work With Me, persistent | Their `+` icon with no label, which says nothing until hovered |
| "Scroll to explore" hint pinned centre | Tells a first-time visitor the page is not static | Only worth it if the hero stops looking scrollable | Keeping it visible after the first scroll, as they do |
| Chapters dropdown in the header | Non-linear access to a long page | We have nav plus the rail. A third control would be clutter | Adding it |

---

## What was rejected outright

`Scroll hijacking.` It costs the scrollbar, keyboard paging, find-in-page,
scroll restoration and any deep link into the middle of the page. The master
brief bans it, and their own mobile build does not use it. Every pinned effect
here is built on `position: sticky` and real document scroll instead.

`Their section count.` Eighteen sections at 30,184px. Ours does the same job in
nine at 27.9 screens, and every one of ours carries content rather than
transition.

---

## If more references arrive

Same method. Drive the site, read the DOM, measure. A screen recording is not
useful because it cannot be inspected. What is useful from the client is a
still, plus one sentence naming the exact element or moment they want, since
that resolves ambiguity a video leaves open.
