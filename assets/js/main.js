/**
 * Behaviour for the athlete site.
 *
 * Everything here is an enhancement. With JavaScript off the page still renders
 * its full content, because build.py writes the markup statically; what is lost
 * is the track rail's progress, the results filter, the plot readout and the
 * lightbox. The results table is the one exception and is rendered here, so it
 * gets a <noscript> fallback pointing at the same data.
 */

/**
 * Structured data travels inside the document, in a JSON script tag written by
 * build.py. It used to be a separate ES module, which meant the page needed a
 * server to run at all and gave the browser one more file to serve stale.
 */
/*
 * Absent on the journal pages, which carry no structured data. Every init below
 * bails when its own elements are missing, so the same script runs everywhere
 * and the reveals work on the subpages too.
 */
const DATA_EL = document.getElementById("site-data");
const DATA = DATA_EL ? JSON.parse(DATA_EL.textContent) : {};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
const prefersReduced = () => reduced.matches;

const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

/**
 * Registers a scroll handler that paints at most once per frame.
 *
 * Several things now read scroll position on every event. Without coalescing
 * them into a frame the page does the same layout reads a dozen times per
 * scroll tick and stutters on a mid-range phone.
 */
function onScroll(fn) {
  let ticking = false;
  const run = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      fn();
    });
  };
  window.addEventListener("scroll", run, { passive: true });
  window.addEventListener("resize", run);
  return run;
}

/*
 * A hidden document runs neither transitions nor animations, and never fires
 * requestAnimationFrame. Anything whose visible state depends on one of those
 * would be stranded, so while the page is hidden we turn motion off and let the
 * end states apply directly. It comes back on the moment the page is shown.
 */
const syncMotionState = () =>
  document.documentElement.classList.toggle(
    "anim-off",
    document.visibilityState === "hidden"
  );

syncMotionState();
document.addEventListener("visibilitychange", syncMotionState);

/*
 * Nothing on this page is allowed to be hidden unless the code that un-hides it
 * is demonstrably running.
 *
 * The entrance styles used to key off the `js` class, which an inline script in
 * the head adds. That inline script always runs, so the moment it did, thirty
 * elements went to `opacity: 0` and stayed there if this file was blocked,
 * throttled or errored on the way in. The reported symptom was a blank page
 * that came good on a refresh, which is exactly what a blocked script looks
 * like once the second load hits cache.
 *
 * This class is added from inside the file that does the revealing, so the two
 * can no longer come apart. `js` still drives everything that is safe without
 * JavaScript, such as travel, which rests at its final position by default.
 */
document.documentElement.classList.add("reveal");

/* ------------------------------------------------------------------- entry */

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initHeroFade();
  initCue();
  initNowbar();
  initDeck();
  initScrub();
  initQuote();
  initBibDepth();
  initFloatCta();
  initJourney();
  initTargets();
  initTravel();
  initRail();
  initReveal();
  initResults();
  initPlot();
  initGallery();
  initPeaks();
  initEnquiry();
  initAnchorScroll();
});

/* -------------------------------------------------------------- the deck */

/**
 * Deals the career cards as the reader scrolls the deck's runway.
 *
 * Writes one custom property per card and lets CSS do the transform. That keeps
 * the motion declarative, so the whole choreography can be retuned in the
 * stylesheet without touching this, and it means a card off-frame costs a
 * variable write rather than a layout.
 */
function initDeck() {
  const deck = $("#deck");
  if (!deck) return;

  const cards = $$(".deck-card", deck);
  if (!cards.length || prefersReduced()) return;

  const paint = () => {
    const box = deck.getBoundingClientRect();
    const travel = box.height - window.innerHeight;
    if (travel <= 0) return;
    const p = clamp(-box.top / travel, 0, 1);

    /*
     * The runway carries every card to the front, plus a short ramp for the
     * last one to leave on.
     *
     * This has been wrong in both directions. At `cards.length` the eleventh
     * card cleared the frame at 95% and the pinned stage then scrolled away
     * with nothing on it, which is a screen of black between the record and the
     * map. At `cards.length - 1` the card arrived at the front exactly as the
     * runway ended, so there was no scroll left for it to exit on: it sat at
     * the reading position and rode the unpin out, which is what reads as
     * stuck. Every other card flies past the viewer and that one does not.
     *
     * EXIT is the fix. The head travels a fraction of a card past the last one
     * so it has somewhere to go, and `.deck` carries a matching ramp in its
     * height. At 0.6 the exit was clean but the reader then scrolled 39vh of
     * empty stage before the next chapter's heading arrived. 0.45 still clears
     * the fade at `--t` 1.42 with the stage pinned, and gives most of that
     * blank stretch back. Keep this in step with the tail in `.deck`.
     */
    const EXIT = 0.45;
    const head = p * (cards.length - 1 + EXIT);
    cards.forEach((card, i) => {
      /*
       * Raw, and allowed to go negative. Clamping it to zero parked every
       * future card in the arrival position at once, so the eleventh card sat
       * in the corner while the fourth was still being read.
       */
      const t = head - i + 1;
      card.style.setProperty("--t", t.toFixed(3));
      /*
       * Three deep behind the reading position, and one on its way out past the
       * viewer. Anything further back is smaller than a stamp and anything
       * further forward has already left the frame.
       */
      card.style.visibility = t < -1.7 || t > 1.55 ? "hidden" : "";
    });
  };

  onScroll(paint);
  paint();
}

/* ------------------------------------------------------- scrubbed archive */

/**
 * Advances the paired photographs as the reader scrolls its runway.
 *
 * The pinning is CSS. This only decides which pair is showing, from how far
 * through the runway the sticky stage has travelled. Under reduced motion the
 * runway collapses to auto height in CSS and this bails, leaving the first pair
 * and the full grid below it.
 */
function initScrub() {
  const scrub = $("#scrub");
  if (!scrub) return;

  const frames = $$(".scrub-frame", scrub);
  const count = $("#scrub-count");
  if (!frames.length || prefersReduced()) return;

  let current = 0;
  const pad = (n) => String(n).padStart(2, "0");

  const paint = () => {
    const box = scrub.getBoundingClientRect();
    const travel = box.height - window.innerHeight;
    if (travel <= 0) return;
    const p = clamp(-box.top / travel, 0, 1);
    // The last pair holds for the final stretch rather than flicking past.
    const i = clamp(Math.floor(p * frames.length), 0, frames.length - 1);
    if (i === current) return;
    current = i;
    frames.forEach((f, n) => (f.dataset.on = String(n === i)));
    if (count) count.textContent = `${pad(i + 1)} / ${pad(frames.length)}`;
  };

  onScroll(paint);
  paint();
}

/* ------------------------------------------------------ horizontal quote */

/**
 * Runs the pull quote sideways while the page runs down.
 *
 * Travel is measured from the rendered line rather than guessed, so the text
 * always clears the viewport no matter how long the sentence is or how the
 * font renders.
 */
function initQuote() {
  const quote = $("#quote");
  const line = $("#quote-line");
  if (!quote || !line || prefersReduced()) return;

  let travel = 0;
  const measure = () => {
    travel = Math.max(line.scrollWidth - window.innerWidth + 120, 0);
  };

  const paint = () => {
    const box = quote.getBoundingClientRect();
    const run = box.height - window.innerHeight;
    if (run <= 0) return;
    const p = clamp(-box.top / run, 0, 1);
    line.style.transform = `translate3d(${-p * travel}px, 0, 0)`;
  };

  measure();
  paint();
  onScroll(paint);
  window.addEventListener("resize", () => {
    measure();
    paint();
  });
  if (document.fonts?.ready) {
    document.fonts.ready.then(() => {
      measure();
      paint();
    });
  }
}

/* ---------------------------------------------------------- bib parallax */

/**
 * Gives the bib row depth by shifting alternate plates at different rates.
 *
 * One shared variable on the container, multiplied per plate in CSS, so this
 * writes a single custom property per frame rather than touching six elements.
 */
function initBibDepth() {
  const bibs = $(".bibs");
  if (!bibs || prefersReduced()) return;
  if (!window.matchMedia("(min-width: 1080px)").matches) return;

  const paint = () => {
    const box = bibs.getBoundingClientRect();
    // -1 above the fold to 1 below it, 0 when centred.
    const p = (box.top + box.height / 2 - window.innerHeight / 2) /
      (window.innerHeight / 2 + box.height / 2);
    bibs.style.setProperty("--shift", `${clamp(p, -1, 1) * 26}px`);
  };

  onScroll(paint);
  paint();
}

/* ----------------------------------------------------------- floating CTA */

/** Shows once past the hero, hides again over the contact section. */
function initFloatCta() {
  const cta = $("#float-cta");
  const hero = $(".hero");
  const contact = $("#contact");
  if (!cta || !hero) return;

  const paint = () => {
    const pastHero = hero.getBoundingClientRect().bottom < 0;
    const atContact = contact
      ? contact.getBoundingClientRect().top < window.innerHeight * 0.75
      : false;
    cta.dataset.shown = String(pastHero && !atContact);
  };

  onScroll(paint);
  paint();
}

/* ------------------------------------------------------------------ drift */

/**
 * Slides marked elements sideways as they pass through the viewport.
 *
 * One number per element: `--d`, running about -1 to 1 as the element crosses
 * from the bottom of the screen to the top. Direction and distance live in CSS
 * as `--dir` and `--amp`, so a section can be tuned without touching this.
 *
 * Elements off screen are skipped, which matters because this runs on every
 * frame the page scrolls and the count grows with the page.
 */
function initTravel() {
  const travel = $$("[data-travel]");
  const dissolve = $$("[data-dissolve]");
  const hero = $("#top");
  if (!travel.length && !dissolve.length && !hero) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  // How far through the viewport an element's middle is: 1 at the bottom edge,
  // 0 dead centre, -1 at the top. Off-screen elements return null so the loop
  // can skip them, which matters because this runs on every scrolled frame and
  // the page is forty screens long.
  const across = (el, vh) => {
    const box = el.getBoundingClientRect();
    if (box.bottom < -160 || box.top > vh + 160) return null;
    const mid = box.top + box.height / 2;
    return Math.max(-1, Math.min(1, (mid - vh / 2) / (vh / 2)));
  };

  const clamp01 = (n) => Math.max(0, Math.min(1, n));

  onScroll(() => {
    if (reduce.matches) return;
    const vh = window.innerHeight;

    for (const el of travel) {
      const p = across(el, vh);
      if (p === null) continue;
      /*
       * Clamped at 0, so the path is corner to rest and then it holds.
       *
       * `across` keeps counting past centre and down to -1 as an element
       * leaves the top of the screen. Feeding that straight to `--p` meant a
       * card travelled in from its corner, crossed its resting position at
       * dead centre, and carried straight on out the other side, so it was
       * only ever square on the page for the single frame it passed through
       * the middle. On the small amplitudes, like the press pairs at 0.4, that
       * reads as a drift and nobody minds. On the funding rows at 0.85 it
       * reads as a row that never arrives: the client's screenshot caught 02
       * with its heading still out to the left and its body still half faded.
       *
       * Resting is the intended final state anyway. It is where these elements
       * sit with JavaScript off.
       */
      el.style.setProperty("--p", Math.max(0, p).toFixed(3));
      // Faded in by the time it is two thirds of the way up. Nothing fades on
      // the way out, so text stays readable right to the edge. This one keeps
      // the unclamped value: it is already one-sided.
      el.style.setProperty("--o", clamp01((1.0 - p) / 0.34).toFixed(3));
    }

    for (const el of dissolve) {
      const p = across(el, vh);
      if (p === null) continue;
      // Full strength across the middle third, gone by four fifths out either
      // side. This one does fade both ways, because it is the road to 2030 and
      // reading it one year at a time is the point.
      el.style.setProperty("--v", clamp01(1 - (Math.abs(p) - 0.34) / 0.42).toFixed(3));
    }

    if (hero) {
      // The hero has no entrance to make, so its number is how far the reader
      // has left it: 0 at rest, 1 one viewport down. The wordmark and the
      // photograph pull apart as it goes, which hands the page over rather than
      // letting a static block slide off the top.
      const h = clamp01(window.scrollY / vh);
      hero.style.setProperty("--out", h.toFixed(3));
    }
  })();
}

/* ---------------------------------------------------------------- targets */

/**
 * Advances the road to 2030 while its block is pinned.
 *
 * One number again, `--tp`, 0 to 1 across the runway. Every year is on screen
 * throughout; CSS decides which of them is lit from that number and the tile's
 * own index, so adding a fifth target needs no change here.
 */
function initTargets() {
  // Same mechanism drives the qualification route, which is also a pinned block
  // whose tiles advance off one scroll position.
  const runs = [$("#targets-run"), $("#croute-run")].filter(Boolean);
  if (!runs.length) return;

  const stage = $(".targets");
  const finalCard = $(".target-final .tf-inner");
  const zoomTile = $('.target[data-zoom="true"]');

  /**
   * Works out where the finale card has to start so that it appears to be the
   * 2030 tile, and how much it has to grow.
   *
   * The card used to be a separate panel that faded up in the middle of the
   * screen while the tile sat there dimmed, so it read as two objects rather
   * than one thing opening. Measuring the tile lets the card begin at exactly
   * its position and size and expand out of it.
   *
   * Both rects are read with the animation forced to its end state, because a
   * transformed element reports its transformed box and the maths needs the
   * resting one. That costs a forced layout, so it runs on resize only, never
   * per scrolled frame.
   */
  let start = null;
  const measure = () => {
    if (!stage || !finalCard || !zoomTile) return;
    stage.style.setProperty("--promote", "1");
    const a = zoomTile.getBoundingClientRect();
    const b = finalCard.getBoundingClientRect();
    stage.style.removeProperty("--promote");

    if (!a.width || !b.width) {
      start = null;
      return;
    }
    start = {
      dx: a.left + a.width / 2 - (b.left + b.width / 2),
      dy: a.top + a.height / 2 - (b.top + b.height / 2),
      s: a.width / b.width,
    };
    const fin = finalCard.parentElement;
    fin.style.setProperty("--fx", start.dx.toFixed(1));
    fin.style.setProperty("--fy", start.dy.toFixed(1));
    fin.style.setProperty("--fs", start.s.toFixed(4));
  };

  measure();
  window.addEventListener("resize", measure);

  onScroll(() => {
    for (const run of runs) {
      const runway = run.offsetHeight - window.innerHeight;
      if (runway <= 0) {
        run.style.setProperty("--tp", "1");
        continue;
      }
      const p = Math.min(1, Math.max(0, -run.getBoundingClientRect().top / runway));
      run.style.setProperty("--tp", p.toFixed(4));

      // The finale's call to action only becomes clickable and focusable once
      // the card has finished growing. A link that is on screen at a fifth of
      // its size is not a link anybody meant to press.
      if (run.id === "targets-run" && finalCard) {
        const fin = finalCard.parentElement;
        const live = p > 0.94;
        fin.dataset.live = String(live);
        const cta = $(".tf-cta", fin);
        if (cta) cta.tabIndex = live ? 0 : -1;
      }
    }
  })();
}

/* ------------------------------------------------------------ journey rail */

/**
 * Drives the journey sideways while the page scrolls down.
 *
 * The whole job is one number. How far the pinned stage has travelled through
 * its runway becomes `--shift` in pixels, and CSS moves the track. Nothing here
 * touches the scroll position itself, so the scrollbar stays honest, the
 * keyboard still pages, and find-in-page can still land inside a chapter.
 *
 * The travel distance is measured rather than assumed, because panel widths are
 * viewport-relative and the last one has to stop with its text on screen, not
 * flush against the right edge where it would read as cut off.
 */
function initJourney() {
  const rail = $("#jrail");
  const track = $("#jrail-track");
  const fill = $("#jrail-fill");
  if (!rail || !track) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const wide = window.matchMedia("(min-width: 900px)");

  const run = onScroll(() => {
    if (reduce.matches || !wide.matches) {
      track.style.removeProperty("--shift");
      return;
    }

    const box = rail.getBoundingClientRect();
    const runway = rail.offsetHeight - window.innerHeight;
    if (runway <= 0) return;

    // 0 at the moment the stage pins, 1 when it is about to unpin.
    const p = Math.min(1, Math.max(0, -box.top / runway));
    const travel = Math.max(0, track.scrollWidth - window.innerWidth);

    track.style.setProperty("--shift", (p * travel).toFixed(1));
    if (fill) fill.style.setProperty("--p", p.toFixed(3));

    /*
     * The year ticks and their rule orient the reader for the first moment of
     * the run and are clutter for the rest of it. They were also what the
     * panels appeared to snag on, because a photograph travelling left crossed
     * a line of fixed text sitting still. They clear out as soon as the run is
     * moving.
     */
    const foot = track.parentElement;
    foot.style.setProperty("--fade", Math.max(0, 1 - p / 0.1).toFixed(3));
  });

  // Panel widths change with the viewport, and late-decoding photographs change
  // the track width, so the measurement is redone rather than cached.
  reduce.addEventListener?.("change", run);
  wide.addEventListener?.("change", run);
  $$("img", track).forEach((im) => {
    if (!im.complete) im.addEventListener("load", run, { once: true });
  });
  run();
}

/* -------------------------------------------------------------- hero burst */

/**
 * A shutter burst across the hero, standing in for footage until footage
 * exists. Cuts through the frames once, then clears to the portrait beneath.
 *
 * Two rules it will not break. It never loops, because a hero that keeps
 * flashing is hostile to anyone trying to read the name underneath it. And it
 * only plays if every frame has already decoded, because a burst that stutters
 * on a slow connection looks broken rather than fast.
 */
function initHeroFade() {
  const stack = $("#hero-fade");
  if (!stack) return;

  const frames = $$("img", stack);
  const ms = Number(stack.dataset.ms) || 4600;

  // Reduced motion is a standing preference, so the spare frames go for good and
  // the hero is a still photograph, which it is perfectly happy being.
  //
  // A hidden document is NOT a reason to remove them. `anim-off` is on whenever
  // the tab is in the background, and an earlier version tore the frames out
  // here, so anyone who opened the site in a background tab lost the fade
  // permanently. Being hidden only pauses the interval, below.
  if (frames.length < 2 || prefersReduced()) {
    frames.slice(1).forEach((f) => f.remove());
    return;
  }

  let i = 0;
  let timer = 0;

  const step = () => {
    i = (i + 1) % frames.length;
    frames.forEach((f, n) => (f.dataset.on = String(n === i)));
  };

  const start = () => {
    if (timer) return;
    timer = setInterval(step, ms);
  };
  const stop = () => {
    clearInterval(timer);
    timer = 0;
  };

  // A hero that keeps fading in a background tab is heat for nothing.
  document.addEventListener("visibilitychange", () => {
    document.visibilityState === "hidden" ? stop() : start();
  });

  if (document.visibilityState !== "hidden") start();
}

/* --------------------------------------------------------- section marker */

/**
 * Names the section the reader is currently in, under the header.
 *
 * The headings themselves cannot do this. Each one lives in its own wrapper
 * rather than spanning its section, so making them `position: sticky` would pin
 * them for a couple of hundred pixels and then let go, which is worse than not
 * pinning at all. This reads the heading out of the DOM instead and keeps it on
 * screen for the whole section, which is also the only wayfinding a phone gets,
 * since the rail is desktop-only.
 *
 * Hidden over the hero, where the wordmark is already saying where you are.
 */
function initNowbar() {
  const bar = $("#nowbar");
  if (!bar) return;

  // The header is one line of type plus padding, which is 72px on a phone and
  // less on a desktop, and it changes again if the reader has bumped their font
  // size. A hardcoded offset put the bar on top of the header at 375px, so it
  // is measured.
  const navEl = $("#nav");
  if (navEl) {
    /*
     * Two numbers, not one.
     *
     * `--nav-h` is the header. `--top-h` is the header plus this bar, which
     * hangs below it and is what the pinned section titles actually have to
     * clear. They were offset by the header alone, so "All the records, on the
     * record" ran straight through "01 Kodagu to Davos" for the whole card run.
     */
    const setH = () => {
      const nav = Math.round(navEl.getBoundingClientRect().height);
      const own = Math.round(bar.getBoundingClientRect().height);
      const root = document.documentElement.style;
      root.setProperty("--nav-h", `${nav}px`);
      root.setProperty("--top-h", `${nav + own}px`);
    };
    setH();
    if ("ResizeObserver" in window) {
      const ro = new ResizeObserver(setH);
      ro.observe(navEl);
      ro.observe(bar);
    } else {
      window.addEventListener("resize", setH);
    }
  }

  const idxEl = $(".now-idx", bar);
  const nameEl = $(".now-name", bar);
  const sections = $$("section[id]").filter((s) => s.id !== "top");
  if (!sections.length || !("IntersectionObserver" in window)) return;

  const label = (s) => {
    const head = $(".section-head", s);
    return {
      idx: head ? $(".idx", head)?.textContent.trim() || "" : "",
      name:
        (head && $("h2", head)?.textContent.trim()) ||
        s.getAttribute("aria-label") ||
        "",
    };
  };

  let live = "";
  const show = (s) => {
    if (s.id === live) return;
    live = s.id;
    const { idx, name } = label(s);
    idxEl.textContent = idx;
    nameEl.textContent = name;
    bar.dataset.shown = "true";
  };

  // A line a third of the way down the viewport. Whichever section is crossing
  // it is the one the reader is in, which is steadier than asking which section
  // covers the most pixels.
  const io = new IntersectionObserver(
    (entries) => {
      for (const en of entries) {
        if (en.isIntersecting) en.target.dataset.here = "true";
        else delete en.target.dataset.here;
      }
      const at = sections.filter((s) => s.dataset.here === "true");
      if (at.length) show(at[at.length - 1]);
    },
    { rootMargin: "-32% 0px -66% 0px", threshold: 0 }
  );
  sections.forEach((s) => io.observe(s));

  /*
   * Retracted over the hero and again over the footer, where it would sit on
   * top of the closing wordmark. Also retracted while the section's own heading
   * is on screen.
   *
   * That last one is the point of the thing. The bar exists to answer "which
   * chapter am I in" for a reader who arrived mid-section, and that question is
   * already answered, in 59px type, whenever the heading is visible. Without
   * the check the chapter name appeared twice within 17px of itself, which is
   * what a reader reads as a mistake rather than as navigation. The bar now
   * takes over from the title instead of competing with it.
   */
  const headingOnScreen = () => {
    const s = live && document.getElementById(live);
    const h = s && $(".section-head h2", s);
    if (!h) return false;
    const r = h.getBoundingClientRect();
    return r.bottom > 0 && r.top < window.innerHeight;
  };

  onScroll(() => {
    if (window.scrollY < window.innerHeight * 0.75) bar.dataset.shown = "false";
    else if (live && !headingOnScreen()) bar.dataset.shown = "true";
    else bar.dataset.shown = "false";
  })();
}

/* ----------------------------------------------------------------- the cue */

/**
 * Tells the reader the page moves, whenever they are in a position to need it.
 *
 * It used to retire on the first scroll and never return, which was wrong: come
 * back to the top and the hero is once again a still, full-height screen with
 * no sign that anything is under it, and the one element that says otherwise
 * had permanently removed itself. It now simply tracks whether the hero is the
 * thing being looked at.
 *
 * Leclerc's site leaves theirs up permanently, over every section, which turns
 * a hint into furniture. This is the middle position: present at the top, gone
 * everywhere else.
 */
function initCue() {
  const cue = $("#hero-cue");
  if (!cue) return;

  onScroll(() => {
    cue.dataset.gone = String(window.scrollY > 40);
  })();
}

/* ----------------------------------------------------------- anchor scroll */

/**
 * Smooth scrolling for in-page links, driven here rather than by CSS.
 *
 * `scroll-behavior: smooth` on `html` did this for free and did it wrong. On a
 * document this tall, about 30,000px, the browser abandons a smooth scroll the
 * moment the layout shifts underneath it, and across a journey that long the
 * lazy images and the reveal classes guarantee a shift. Measured in Chrome:
 * clicking RECORD set `location.hash` to `#record` and left `scrollY` at 0 with
 * the target 13,986px below. It failed the same way for the rail stops, the
 * hero cue, and a hash typed into the address bar.
 *
 * The fix is to re-read the target's document position on every frame instead
 * of computing it once at the start. A shift above the target moves the
 * destination and this simply follows it, which is the exact case that defeats
 * the native version.
 *
 * Duration is tied to distance and then capped. A fixed duration makes a short
 * hop feel slow and a 14,000px run feel endless; 900ms is the ceiling, which
 * keeps the longest jump on the page brisk enough to sit through.
 */
function initAnchorScroll() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const ease = (t) =>
    t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  let frame = 0;

  // Any real input from the reader outranks an animation they did not ask to
  // keep watching. Without this the page fights a mid-flight scroll.
  const stop = () => {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
  };
  ["wheel", "touchstart", "keydown"].forEach((ev) =>
    window.addEventListener(ev, stop, { passive: true })
  );

  document.addEventListener("click", (ev) => {
    if (ev.defaultPrevented || ev.button !== 0) return;
    if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;

    const link = ev.target.closest('a[href^="#"]');
    if (!link || link.target === "_blank") return;

    const id = link.getAttribute("href").slice(1);
    if (!id) return;
    const target = document.getElementById(id);
    if (!target) return;

    ev.preventDefault();
    stop();

    // Read fresh each frame. This is the whole point of the function.
    const destination = () => {
      const limit =
        document.documentElement.scrollHeight - window.innerHeight;
      const y = target.getBoundingClientRect().top + window.scrollY;
      return Math.max(0, Math.min(limit, y));
    };

    const land = () => {
      // `pushState` rather than assigning the hash, which would scroll a second
      // time and undo the landing.
      history.pushState(null, "", `#${id}`);
      // Focus follows the jump, so a keyboard reader carries on from the
      // section they asked for rather than from where they were.
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    };

    const start = window.scrollY;
    if (reduce.matches) {
      window.scrollTo(0, destination());
      land();
      return;
    }

    const span = Math.abs(destination() - start);
    if (span < 2) {
      land();
      return;
    }
    const ms = Math.min(900, Math.max(320, span * 0.22));
    const t0 = performance.now();

    const step = (now) => {
      const t = Math.min(1, (now - t0) / ms);
      window.scrollTo(0, start + (destination() - start) * ease(t));
      if (t < 1) {
        frame = requestAnimationFrame(step);
      } else {
        frame = 0;
        land();
      }
    };
    frame = requestAnimationFrame(step);
  });
}

/* --------------------------------------------------------------------- nav */

function initNav() {
  const nav = $("#nav");
  const toggle = $("#nav-toggle");
  const panel = $("#nav-panel");
  if (!nav || !toggle || !panel) return;

  const setOpen = (open) => {
    panel.dataset.open = String(open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    document.documentElement.style.overflow = open ? "hidden" : "";
    if (open) $("a", panel)?.focus();
  };

  toggle.addEventListener("click", () =>
    setOpen(toggle.getAttribute("aria-expanded") !== "true")
  );
  panel.addEventListener("click", (ev) => {
    if (ev.target.tagName === "A") setOpen(false);
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && panel.dataset.open === "true") {
      setOpen(false);
      toggle.focus();
    }
  });

  const onScroll = () => {
    nav.dataset.stuck = String(window.scrollY > 24);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
}

/* -------------------------------------------------------------------- rail */

/**
 * The track rail. Nodes are placed at each section's real scroll offset rather
 * than at even intervals, so the rail is an honest map of the page.
 *
 * The cut and its bright head are driven straight from scroll position, not
 * animated, which is why the rail still works under prefers-reduced-motion.
 */
function initRail() {
  const railEl = $(".track-rail");
  const nodesEl = $("#rail-nodes");
  if (!railEl || !nodesEl) return;

  /*
   * Rail geometry, in CSS pixels. The SVG has no viewBox on purpose.
   *
   *   MID          the line of travel before the track exists
   *   LEFT/RIGHT   the two classic grooves, once she is on snow
   *   SPLAY        how far it takes the single path to open into two
   */
  const MID = 38;
  const LEFT = 30;
  const RIGHT = 46;
  const SPLAY = 14;
  const SKI = 20; // length of each ski segment
  const STRIDE = 7; // how far one ski leads the other
  const TICK = 72; // spacing of the distance markers
  // The whole track lives between these insets. The top one clears the fixed
  // nav, which sits above the rail and would crop a checkpoint's label.
  const TOP_INSET = 78;
  const BOT_INSET = 34;

  const cutA = $("#cut-a");
  const cutB = $("#cut-b");
  const skiA = $("#ski-a");
  const skiB = $("#ski-b");
  const tApproach = $("#terrain-approach");
  const tGrooveA = $("#terrain-groove-a");
  const tGrooveB = $("#terrain-groove-b");
  const tTicks = $("#terrain-ticks");

  const stops = DATA.railStops
    .map((id) => ({ id, el: document.getElementById(id), node: $(`.node[data-stop="${id}"]`) }))
    .filter((s) => s.el && s.node);

  const navLinks = new Map($$("[data-nav]").map((a) => [a.dataset.nav, a]));

  let layout = [];
  let H = 0;
  let usable = 1;
  let snowY = 0; // where the track opens: she reaches snow
  let raceY = 0; // where distance markers begin: international racing

  const progressOf = (el, scrollable) =>
    clamp((el.getBoundingClientRect().top + window.scrollY) / scrollable, 0, 1);

  /**
   * Page progress to a y on the rail.
   *
   * Everything the rail draws goes through this, so the checkpoints, the cut and
   * the skis all agree. Clamping positions individually instead would stack the
   * first two checkpoints on the same pixel and let the ski head drift off them.
   */
  const yFor = (p) => TOP_INSET + p * usable;

  const measure = () => {
    const doc = document.documentElement;
    const scrollable = Math.max(doc.scrollHeight - window.innerHeight, 1);
    H = railEl.clientHeight;
    usable = Math.max(H - TOP_INSET - BOT_INSET, 1);

    layout = stops.map((s) => {
      const p = progressOf(s.el, scrollable);
      s.node.style.top = `${yFor(p).toFixed(1)}px`;
      return { ...s, p };
    });

    // The two terrain changes are tied to what the page is actually saying at
    // that point, not to arbitrary fractions of the scroll.
    const career = document.getElementById("journey");
    const footprint = document.getElementById("footprint");
    snowY = yFor(career ? progressOf(career, scrollable) : 0.3);
    raceY = yFor(footprint ? progressOf(footprint, scrollable) : 0.6);

    tApproach.setAttribute("d", `M${MID} ${TOP_INSET} V${snowY.toFixed(1)}`);
    const end = yFor(1);
    tGrooveA.setAttribute(
      "d",
      `M${MID} ${snowY.toFixed(1)} L${LEFT} ${(snowY + SPLAY).toFixed(1)} V${end.toFixed(1)}`
    );
    tGrooveB.setAttribute(
      "d",
      `M${MID} ${snowY.toFixed(1)} L${RIGHT} ${(snowY + SPLAY).toFixed(1)} V${end.toFixed(1)}`
    );

    // Markers sit beside the track, the way course boards do. Drawn across the
    // grooves they read as ladder rungs instead.
    let ticks = "";
    for (let y = raceY + TICK; y < end - 4; y += TICK) {
      ticks += `<line x1="${RIGHT + 3}" y1="${y.toFixed(1)}" x2="${RIGHT + 9}" y2="${y.toFixed(1)}"/>`;
    }
    tTicks.innerHTML = ticks;
  };

  /** The cut track: one path to the snow line, then splaying into its groove. */
  const cutPath = (x, y) => {
    if (y <= snowY) return `M${MID} ${TOP_INSET} V${y.toFixed(1)}`;
    const openY = Math.min(snowY + SPLAY, y);
    const openX = MID + (x - MID) * ((openY - snowY) / SPLAY);
    return (
      `M${MID} ${TOP_INSET} V${snowY.toFixed(1)} ` +
      `L${openX.toFixed(1)} ${openY.toFixed(1)} V${y.toFixed(1)}`
    );
  };

  const paint = () => {
    const doc = document.documentElement;
    const scrollable = Math.max(doc.scrollHeight - window.innerHeight, 1);
    const p = clamp(window.scrollY / scrollable, 0, 1);
    const y = yFor(p);

    cutA.setAttribute("d", cutPath(LEFT, y));
    cutB.setAttribute("d", cutPath(RIGHT, y));

    // One ski leads, then the other. Driven by scroll distance rather than by
    // a timer, so it only moves when the reader moves.
    const lead = Math.sin(window.scrollY / 130) * STRIDE;
    const onSnow = y > snowY + SPLAY;
    const xa = onSnow ? LEFT : MID;
    const xb = onSnow ? RIGHT : MID;
    const ya = clamp(y + lead, TOP_INSET, yFor(1));
    const yb = clamp(y - lead, TOP_INSET, yFor(1));
    skiA.setAttribute(
      "d",
      `M${xa} ${Math.max(ya - SKI, TOP_INSET).toFixed(1)} V${ya.toFixed(1)}`
    );
    skiB.setAttribute(
      "d",
      `M${xb} ${Math.max(yb - SKI, TOP_INSET).toFixed(1)} V${yb.toFixed(1)}`
    );

    let current = null;
    for (const s of layout) {
      const passed = p >= s.p - 0.004;
      s.node.dataset.passed = String(passed);
      if (passed) current = s;
    }
    for (const s of layout) {
      const isCurrent = current && s.id === current.id;
      s.node.dataset.current = String(Boolean(isCurrent));
      const link = navLinks.get(s.id);
      if (link) {
        if (isCurrent) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      }
    }
  };

  let ticking = false;
  const onScroll = () => {
    // rAF does not fire while the document is hidden, and the rail would then
    // freeze mid-page. Nothing is being composited in that state anyway, but
    // painting straight through keeps the rail correct for prerenders and for
    // anything that scrolls the page without displaying it.
    if (document.visibilityState === "hidden") {
      paint();
      return;
    }
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      paint();
      ticking = false;
    });
  };

  const remeasure = () => {
    measure();
    paint();
  };

  remeasure();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", remeasure);
  window.addEventListener("load", remeasure);
  // A hidden document may not dispatch scroll at all, so catch up on return.
  document.addEventListener("visibilitychange", remeasure);
  if (document.fonts?.ready) document.fonts.ready.then(remeasure);
}

/* ------------------------------------------------------------------ reveal */

function initReveal() {
  const items = $$("[data-anim]");
  if (!items.length) return;
  if (prefersReduced() || !("IntersectionObserver" in window)) {
    items.forEach((el) => (el.dataset.shown = "true"));
    return;
  }
  let delivered = false;

  const io = new IntersectionObserver(
    (entries) => {
      delivered = true;
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        en.target.dataset.shown = "true";
        io.unobserve(en.target);
      }
    },
    { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
  );
  items.forEach((el) => io.observe(el));

  /*
   * Safety net for a rendering pipeline that never runs: a prerender, a hidden
   * document, a browser that reports IntersectionObserver but never delivers.
   *
   * It must not fire while the observer is simply doing its job and waiting for
   * the reader to scroll. A working observer delivers an initial batch for every
   * observed element almost immediately, including the off-screen ones, so
   * `delivered` is the signal that it is alive. Revealing everything on a plain
   * timer instead defeats the whole reveal system, which is what it did.
   */
  setTimeout(() => {
    if (delivered) return;
    items.forEach((el) => (el.dataset.shown = "true"));
  }, 2500);
}

/* ----------------------------------------------------------------- results */

/* Second copy of SOURCE_LABEL in build.py. Keep them in step: this one renders
   the table after any filter click, that one renders it at build time, and a
   difference between them shows up as a column that changes when you touch a
   control. `portfolio` is empty on purpose: the table's caption explains what a
   blank source cell means, rather than the column repeating it on every row. */
const SOURCE_LABEL = {
  fis: "FIS",
  "awg-wikipedia": "Asian Winter Games",
  "kiwg-2026": "Khelo India",
  ap: "AP",
  portfolio: "",
};

function initResults() {
  const body = $("#results-body");
  const toggle = $("#results-toggle");
  const buttons = $$(".filters button");
  if (!body) return;

  let filter = "all";
  let expanded = false;

  /*
   * `featured` trims the opening view only.
   *
   * It used to be applied on top of the category filter, which made two of the
   * five buttons dead on arrival: National has seven results and Biathlon two,
   * and not one of the nine is flagged featured, so both answered "No results
   * in this category yet" over a record that holds them. A reader who picks a
   * category has asked for that category, and the honest answer is all of it.
   *
   * So: the unfiltered view stays short, and any specific filter shows
   * everything it matches.
   */
  const rowsFor = () => {
    const all = DATA.results.rows.filter(
      (r) => filter === "all" || r.tags.includes(filter)
    );
    if (expanded || filter !== "all") return all;
    return all.filter((r) => r.featured);
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (m) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m])
    );

  const render = () => {
    const rows = rowsFor();
    if (!rows.length) {
      body.innerHTML =
        '<tr><td colspan="6" style="color:var(--fg-dim);padding:1.5rem 0">' +
        "No results in this category yet.</td></tr>";
      return;
    }
    body.innerHTML = rows
      .map((r) => {
        const src = DATA.sources[r.sourceRef] || {};
        // Must match result_row in build.py, which renders the same rows at
        // build time. Any change here needs making there too or the table
        // changes shape the first time somebody touches a filter.
        const medal = r.medal
          ? `<span class="medal-dot" data-medal="${esc(r.medal)}"></span>` +
            `<span class="medal-name">${esc(r.medal)}</span>`
          : "";
        const label = SOURCE_LABEL[r.sourceRef] ?? src.sourceName ?? "";
        let link = "";
        if (src.sourceUrl) {
          link =
            `<a class="src-flag" href="${esc(src.sourceUrl)}" target="_blank" rel="noopener">` +
            `${esc(label)}</a>`;
        } else if (label) {
          link =
            `<span class="src-flag is-unlinked" title="${esc(src.sourceName ?? "")}">` +
            `${esc(label)}</span>`;
        }
        return `<tr>
          <td class="c-year">${esc(r.year ?? "—")}</td>
          <td class="c-event">${esc(r.event)}<small>${esc(r.detail)}</small></td>
          <td class="c-place">${esc(r.place)}</td>
          <td class="c-mark">${esc(r.mark || "—")}</td>
          <td class="c-medal">${medal}</td>
          <td>${link}</td>
        </tr>`;
      })
      .join("");
  };

  /* The expand button only means something on the unfiltered view. Inside a
     category every match is already on screen, so offering to expand would be
     a control that does nothing. */
  const syncToggle = () => {
    if (!toggle) return;
    toggle.hidden = filter !== "all";
  };

  buttons.forEach((b) =>
    b.addEventListener("click", () => {
      filter = b.dataset.filter;
      buttons.forEach((x) =>
        x.setAttribute("aria-pressed", String(x === b))
      );
      syncToggle();
      render();
    })
  );

  toggle?.addEventListener("click", () => {
    expanded = !expanded;
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.textContent = expanded
      ? "Show selected results only"
      : "View full achievement record";
    render();
  });

  render();
}

/* ------------------------------------------------------------------- plot */

function initPlot() {
  const atlas = $("#atlas");
  const readout = $("#plot-readout");
  if (!atlas || !readout) return;

  const byId = new Map(DATA.footprint.map((p) => [p.id, p]));
  const pins = $$(".pin", atlas);
  const cards = new Map($$(".atlas-card", atlas).map((el) => [el.dataset.card, el]));
  const RESTING = "__resting";

  /**
   * Exactly one card is ever visible, and the panel is never empty. Restoring
   * the resting card rather than blanking the panel stops the section below it
   * from jumping every time the pointer leaves the map.
   */
  const show = (id) => {
    if (!cards.has(id)) return;
    for (const [key, el] of cards) el.hidden = key !== id;

    const active = id === RESTING ? null : id;
    pins.forEach((g) => (g.dataset.active = String(g.dataset.place === active)));

    const p = byId.get(id);
    if (!p) {
      readout.textContent = "";
      return;
    }
    const hemi = p.lat >= 0 ? "N" : "S";
    readout.textContent =
      `${p.place}, ${p.country}. ${p.event}. ${p.best}. ` +
      `${p.years.join(", ")}. ${Math.abs(p.lat).toFixed(1)} degrees ${hemi}.`;
  };

  pins.forEach((g) => {
    const id = g.dataset.place;
    g.addEventListener("mouseenter", () => show(id));
    g.addEventListener("focus", () => show(id));
    g.addEventListener("click", (ev) => {
      ev.stopPropagation();
      show(id);
    });
    g.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        show(id);
      }
      if (ev.key === "Escape") show(RESTING);
    });
  });

  // Leaving the map returns the panel to its resting state. Focus does not,
  // because a keyboard user tabbing between markers should keep reading.
  $(".atlas-scroll", atlas)?.addEventListener("mouseleave", () => {
    if (!atlas.contains(document.activeElement)) show(RESTING);
  });
}

/* ---------------------------------------------------------------- gallery */

function initGallery() {
  const lb = $("#lightbox");
  const tiles = $$(".gal button");
  if (!lb || !tiles.length) return;

  const imgEl = $("#lb-img");
  const capEl = $("#lb-cap");
  const creditEl = $("#lb-credit");
  const countEl = $("#lb-count");
  const prev = $("#lb-prev");
  const next = $("#lb-next");
  const close = $("#lb-close");
  const items = DATA.gallery;

  /*
   * `order` is the list of item indices currently on screen, and `pos` is where
   * we are inside it. Filtering rewrites `order`, so the arrows and the counter
   * follow whatever the reader has filtered to rather than the full set.
   */
  let order = tiles.map((t) => Number(t.dataset.i));
  let pos = 0;
  let opener = null;

  const paint = () => {
    const it = items[order[pos]];
    if (!it) return;
    imgEl.src = it.full;
    imgEl.alt = it.alt;
    capEl.textContent = it.alt;
    const bits = [it.category, it.location, it.year, it.credit].filter(Boolean);
    creditEl.textContent = bits.join(" · ");
    countEl.textContent = `${pos + 1} / ${order.length}`;
    prev.disabled = pos === 0;
    next.disabled = pos === order.length - 1;
  };

  const open = (index, from) => {
    const at = order.indexOf(index);
    pos = at === -1 ? 0 : at;
    opener = from || null;
    lb.dataset.open = "true";
    document.documentElement.style.overflow = "hidden";
    paint();
    // The dialog is visibility:hidden until the open transition starts, so it
    // cannot take focus in the same frame. rAF is starved in a non-rendering
    // tab, so a timer backs it up and whichever lands first wins.
    let focused = false;
    const grab = () => {
      if (focused) return;
      focused = true;
      close.focus();
    };
    requestAnimationFrame(grab);
    setTimeout(grab, 60);
  };

  const shut = () => {
    lb.dataset.open = "false";
    document.documentElement.style.overflow = "";
    imgEl.removeAttribute("src");
    opener?.focus();
  };

  const step = (d) => {
    const n = clamp(pos + d, 0, order.length - 1);
    if (n === pos) return;
    pos = n;
    paint();
  };

  tiles.forEach((btn) =>
    btn.addEventListener("click", () => open(Number(btn.dataset.i), btn))
  );

  /*
   * The media filter row is gone and so is the code that drove it.
   *
   * It offered All, Press and Photos over a list whose every item was tagged
   * `press`, so All and Press returned the same ten rows and Photos returned
   * none. Nothing here referenced the press list for any other purpose, so the
   * handler went with the markup rather than being left to query elements that
   * no longer exist.
   */
  prev.addEventListener("click", () => step(-1));
  next.addEventListener("click", () => step(1));
  close.addEventListener("click", shut);
  lb.addEventListener("click", (ev) => {
    if (ev.target === lb || ev.target.classList.contains("lb-stage")) shut();
  });

  document.addEventListener("keydown", (ev) => {
    if (lb.dataset.open !== "true") return;
    if (ev.key === "Escape") shut();
    else if (ev.key === "ArrowLeft") step(-1);
    else if (ev.key === "ArrowRight") step(1);
    else if (ev.key === "Tab") {
      // Keep focus inside the dialog.
      const focusable = $$("button:not([disabled])", lb);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (ev.shiftKey && document.activeElement === first) {
        ev.preventDefault();
        last.focus();
      } else if (!ev.shiftKey && document.activeElement === last) {
        ev.preventDefault();
        first.focus();
      }
    }
  });

  // Touch: horizontal swipe changes image, vertical is left to the browser.
  let x0 = null;
  let y0 = null;
  lb.addEventListener(
    "touchstart",
    (ev) => {
      x0 = ev.changedTouches[0].clientX;
      y0 = ev.changedTouches[0].clientY;
    },
    { passive: true }
  );
  lb.addEventListener(
    "touchend",
    (ev) => {
      if (x0 === null) return;
      const dx = ev.changedTouches[0].clientX - x0;
      const dy = ev.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 46 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
      x0 = null;
      y0 = null;
    },
    { passive: true }
  );
}

/* ------------------------------------------------------------------ peaks */

function initPeaks() {
  const bars = $$(".peak .scale i");
  if (
    !bars.length ||
    prefersReduced() ||
    document.visibilityState === "hidden" ||
    !("IntersectionObserver" in window)
  ) {
    return;
  }
  bars.forEach((b) => {
    b.dataset.w = b.style.width;
    b.style.width = "0%";
  });
  let delivered = false;
  const io = new IntersectionObserver(
    (entries) => {
      delivered = true;
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        en.target.style.width = en.target.dataset.w;
        io.unobserve(en.target);
      }
    },
    { threshold: 0.35 }
  );
  bars.forEach((b) => io.observe(b));
  // Same reasoning as initReveal, and the same trap: only step in when the
  // observer is dead, never while it is waiting for the reader.
  setTimeout(() => {
    if (delivered) return;
    bars.forEach((b) => (b.style.width = b.dataset.w));
  }, 2500);
}

/* --------------------------------------------------------------- enquiry */

/**
 * The form has no backend, so it must not pretend to send. It composes a mailto
 * instead and says so, both in the visible note and on submit.
 */
function initEnquiry() {
  const form = $("#enquiry");
  const note = $("#enquiry-note");
  if (!form) return;

  /*
   * A link carrying `data-topic` sets the enquiry subject on its way past.
   *
   * "Invite Bhavani to speak" now lands here, and arriving at a five-option
   * dropdown set to the wrong thing is a small insult to someone who has just
   * told you exactly why they came. The anchor still does the navigating; this
   * only fills the field, so with JavaScript off the button is unaffected.
   */
  const topic = $("#enquiry-topic");
  if (topic) {
    for (const link of $$("a[data-topic]")) {
      link.addEventListener("click", () => {
        const want = link.dataset.topic;
        const match = [...topic.options].find((o) => o.value === want || o.text === want);
        if (match) topic.value = match.value;
      });
    }
  }

  /*
   * Post to the endpoint, and keep the mailto as the fallback.
   *
   * The fallback is not belt and braces, it is the whole reason this is safe to
   * ship before the domain exists. Until `RESEND_API_KEY`, `ENQUIRY_FROM` and
   * `ENQUIRY_TO` are set on the Pages project the function answers 503, and the
   * form quietly does exactly what it did before: opens the reader's mail
   * client with everything filled in. Nobody meets a dead form on either side
   * of the switch, and switching it on is three environment variables and a
   * redeploy, with no change here.
   *
   * Same path covers a blocked fetch, an offline reader, and a function that
   * errors, which between them are the realistic ways this fails in the wild.
   */
  const mailto = ({ name, org, email, topic, message }) => {
    const signoff = [name, org, email].filter(Boolean).join(" · ");
    const body = signoff ? `${message}\n\n—\n${signoff}` : message;
    window.location.href =
      "mailto:bhavani.thekkada2026@gmail.com" +
      `?subject=${encodeURIComponent(topic || "Enquiry via the website")}` +
      `&body=${encodeURIComponent(body)}`;
    note.textContent =
      "Your mail client should be open now, with this message ready to send.";
  };

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    const f = {
      name: String(fd.get("name") || "").trim(),
      org: String(fd.get("org") || "").trim(),
      email: String(fd.get("email") || "").trim(),
      topic: String(fd.get("topic") || "").trim(),
      message: String(fd.get("message") || "").trim(),
      website: String(fd.get("website") || "").trim(),
    };

    if (!f.message) {
      note.textContent = "Add a message first, and this will go straight to her.";
      return;
    }

    const button = $("button[type=submit]", form);
    if (button) button.disabled = true;
    note.textContent = "Sending…";

    try {
      const res = await fetch("/api/enquiry", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(f),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        form.reset();
        note.textContent = "Sent. She reads these herself, so give her a few days.";
        return;
      }
      throw new Error(data.error || res.status);
    } catch (err) {
      mailto(f);
    } finally {
      if (button) button.disabled = false;
    }
  });
}
