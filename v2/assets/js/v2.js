/*
 * Bhavani Thekkada — V2
 *
 * Deliberately small. V1 carried a scroll engine: pinned stages, horizontal
 * travel, a stacking deck, a scrubbed archive, all driven from rAF. The client
 * called that overwhelming and every reference site she chose scrolls
 * normally, so V2 has two behaviours and nothing else.
 *
 *   1. A hairline appears under the nav once the page has moved.
 *   2. Each fold fades up 12px as it enters.
 *
 * Both degrade to nothing. The `js` class is added from inside this file, so
 * if the script is blocked or errors on the way in, the reveal CSS never
 * applies and the page renders in full. V1 shipped that bug once; the fix is
 * cheap enough to carry forward.
 */

(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("js");

  /* ---- nav hairline ---------------------------------------------------- */

  const nav = document.querySelector(".nav");
  if (nav) {
    let ticking = false;
    const sync = () => {
      ticking = false;
      nav.dataset.scrolled = String(window.scrollY > 8);
    };
    addEventListener(
      "scroll",
      () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(sync);
      },
      { passive: true }
    );
    sync();
  }

  /* ---- fold reveal ----------------------------------------------------- */

  const rising = document.querySelectorAll("[data-rise]");
  if (!rising.length) return;

  const reduce = matchMedia("(prefers-reduced-motion: reduce)");

  // No IntersectionObserver, or the reader asked for less motion: show
  // everything at once and stop. Nothing on this page depends on the reveal.
  if (reduce.matches || !("IntersectionObserver" in window)) {
    rising.forEach((el) => (el.dataset.shown = "true"));
    return;
  }

  const seen = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.dataset.shown = "true";
        // One-shot. Nothing fades out on the way back up, so a reader
        // scrolling against the page never watches it disassemble.
        seen.unobserve(entry.target);
      }
    },
    { rootMargin: "0px 0px -12% 0px", threshold: 0.05 }
  );

  rising.forEach((el) => seen.observe(el));
})();
