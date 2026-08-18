# Bhavani Thekkada Nanjunda — athlete site

A static, dependency-free site. It builds with Python's standard library and
serves as plain files, so it deploys to Firebase Hosting, Netlify, GitHub Pages
or any bucket without a toolchain.

## Run it

```bash
python build.py
python -m http.server 8123
```

Then open http://localhost:8123. Opening `index.html` straight off disk also
works, because the structured data travels inside the document and the script is
an ordinary deferred one rather than an ES module. The server is only there so
the URL matches what a host will serve.

On this machine the interpreter is shadowed by a Microsoft Store alias, so use
the real one:

```bash
"C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" build.py
```

There is no npm install, no typecheck and no bundler, because Node is not
installed here. See "Porting to Next.js" below.

## How it fits together

```
content/bhavani.json     every factual claim on the site
content/bhavani.ts       typed re-export of the above
content/images.json      the image library with alt text, credits and rights
content/images.ts        typed re-export of the above
build.py                 renders index.html
assets/css/site.css      one stylesheet, tokens at the top
assets/js/main.js        rail, reveals, filters, plot, lightbox, form
assets/img/*.webp        25 assets at up to three widths each
_source/                 PDF extraction working files, not deployed
```

`content/bhavani.json` is the single source of truth. Three consumers read it and
none of them duplicates it: `build.py` renders the static markup, the same script
inlines what the interactive parts need into a `<script type="application/json"
id="site-data">` tag in the document, and `content/bhavani.ts` is what a Next.js
app would import.

The interactive data used to be a separate `assets/js/data.js` module. Inlining it
removed a request, removed the ES-module requirement, and removed the possibility
of a fresh `index.html` being paired with a cached, stale data file.

`build.py` fingerprints `site.css` and `main.js` and appends the hash to their
URLs, so a rebuild is never masked by a cached asset.

Nothing factual is written into markup by hand. Correct a date in the JSON, run
`python build.py`, and the page, the structured data, the results table and the
map all change together.

## Deploying

`build.py` writes `index.html` in place, so the deployable set is:

```
index.html  assets/  content/
```

`_source/`, `build.py` and the `.ts` files can ship or not; they are harmless
either way. For Firebase, `firebase deploy --only hosting` with `public: "."`
and `content/bhavani.json` reachable, since `data.js` is generated at build time
and the JSON itself is not fetched at runtime.

## Porting to Next.js and Tailwind

The site was built to make this mechanical rather than a rewrite.

- Every section is one function in `build.py` with no shared state. Each maps to
  one component.
- `content/bhavani.ts` and `content/images.ts` already carry the full type
  surface. Turn on `resolveJsonModule` and they work unchanged.
- Design tokens are CSS custom properties in one `:root` block at the top of
  `site.css`. They transfer to a Tailwind theme as-is: `--ink`, `--india`,
  `--race`, `--glacier`, `--snow`, `--stone`, `--moss`, plus a `--step-*` type
  scale that maps to `fontSize`.
- The per-section temperature ladder is CSS custom property reassignment on
  section IDs. In Tailwind that becomes a `data-temp` variant or a wrapper class
  per section.
- `main.js` splits along its comment banners: `initRail`, `initResults`,
  `initPlot`, `initGallery` each become a hook or a client component.

Delete `build.py` and `assets/js/data.js` at that point. Keep the JSON.

## Things worth knowing before you change anything

The motion system has a deliberate escape hatch. Neither CSS transitions nor
animations advance while a document is hidden, and `requestAnimationFrame` never
fires there, so anything whose visible state depends on one of those is stranded
in a background tab or a prerender. `main.js` therefore adds `anim-off` to the
root whenever `document.visibilityState` is `hidden`, and `site.css` uses that to
jump straight to the end state. If you add an entrance effect, give it a resting
state that is visible by default and let `js` opt into hiding it, not the reverse.

`<meta name="darkreader-lock">` is in the head deliberately. The palette is
authored dark and tuned against the photographs. Dark Reader, which is widely
installed, otherwise rewrites every colour: transparent borders become visible
brown, and the hero's gradient scrim becomes an opaque panel sitting on top of
the athlete. The meta tag is Dark Reader's documented opt-out and is the correct
signal for a site that is already dark.

## The journal

Posts are markdown files in `content/journal/`, one per file, named
`YYYY-MM-DD-short-name.md`. `build.py` turns them into `journal.html` and one
page per entry under `journal/`.

`content/journal/_HOW-TO-ADD-A-POST.md` is the guide written for Bhavani.
Files beginning with an underscore are never published.

```bash
python build.py            # publishes only posts without draft: true
python build.py --drafts   # includes drafts, for previewing
```

Two things happen automatically. The Journal link appears in the site navigation
only when at least one post is published, so an empty section is never
advertised. And `journal/` is deleted and rebuilt on every run, so removing a
markdown file removes its page.

Frontmatter is deliberately not YAML. It is `key: value` lines and nothing else,
so a stray colon cannot break a build she runs herself.

The reveal fallback is deliberately conditional, and getting that wrong is worth
understanding before you touch it. `initReveal` needs a way to un-hide content if
the IntersectionObserver never runs, but an unconditional timer defeats the entire
reveal system: it marks every element shown a few seconds after load, so by the
time the reader scrolls down everything has already appeared and nothing animates.
The fallback therefore fires only when the observer has delivered nothing at all,
which a live observer always does immediately, including for off-screen targets.

The results table is rendered twice on purpose. `build.py` writes the ten
featured rows into the HTML so the page works without JavaScript and so crawlers
see them; `main.js` re-renders the same markup when a filter or the expand button
is used. If you change the row markup, change it in both places. They are next to
each other in intent: `result_row()` in `build.py` and `render()` in `initResults`.

## Verification status

Results are checked against the FIS database, the Khelo India 2026 reporting and
the Asian Winter Games record. Every row on the site carries its source, and rows
sourced only to the client's portfolio are labelled "to confirm" in the interface
rather than presented as verified.

Ten claims present in the source material are deliberately not published. They are
listed with reasons in `content/bhavani.json` under `withheld`, and summarised in
`CONTENT_NEEDED.md`.

Image rights for the whole set are unconfirmed. One extracted frame carried a
visible picture-agency watermark, so at least some of the race photography in the
portfolio is licensed material. Read `content/images.json` `meta.rightsWarning`
before publishing anything.
