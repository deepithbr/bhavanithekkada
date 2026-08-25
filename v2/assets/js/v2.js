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

  /* ---- the count-up -------------------------------------------------- */

  // The two division totals count from zero when they first enter, over
  // 900ms, eased. The markup carries the real number, so a blocked script,
  // a crawler or a reduced-motion reader simply sees the total. Numbers are
  // the site's whole argument; they get the one flourish.
  const totals = document.querySelectorAll(".tally-total");
  if (totals.length) {
    const ease = (t) => 1 - Math.pow(1 - t, 3);
    const counter = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        counter.unobserve(entry.target);
        const el = entry.target;
        const end = parseInt(el.textContent, 10);
        if (!Number.isFinite(end)) continue;
        const t0 = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - t0) / 900);
          el.textContent = String(Math.round(end * ease(t)));
          if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }
    }, { threshold: 0.6 });
    totals.forEach((el) => counter.observe(el));
  }

  /* ---- the lightbox --------------------------------------------------- */

  // The gallery grid shows a 3:4 crop for order; the photograph itself is a
  // click away, whole. The tile is a real link to the image file, so with no
  // JavaScript the browser simply opens it; this upgrades the same click.
  const fulls = document.querySelectorAll("[data-full]");
  if (fulls.length) {
    const box = document.createElement("div");
    box.className = "lightbox";
    box.hidden = true;
    box.innerHTML = '<img alt=""><p class="caption"></p>';
    document.body.appendChild(box);
    const pic = box.querySelector("img");
    const cap = box.querySelector(".caption");

    const shut = () => {
      box.hidden = true;
      document.documentElement.style.overflow = "";
    };
    box.addEventListener("click", shut);
    addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !box.hidden) shut();
    });

    fulls.forEach((a) => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        pic.src = a.getAttribute("href");
        pic.alt = (a.querySelector("img") || {}).alt || "";
        cap.textContent = a.dataset.cap || "";
        box.hidden = false;
        document.documentElement.style.overflow = "hidden";
      });
    });
  }

  /* ---- the enquiry form ---------------------------------------------- */

  // Same pipeline as V1: POST to the Pages function, and if that is absent,
  // unconfigured or down, open the reader's own mail client with the message
  // intact. The form never dead-ends: worst case is mailto, which is where
  // this page started.
  const form = document.getElementById("enquiry");
  if (form) {
    const note = document.getElementById("enquiry-note");
    const say = (t) => { if (note) note.textContent = t; };
    const EMAIL = "bhavani.thekkada2026@gmail.com";

    const mailto = (f) => {
      const body =
        (f.message || "") + "\n\n" + [f.name, f.email].filter(Boolean).join(" · ");
      location.href =
        "mailto:" + EMAIL +
        "?subject=" + encodeURIComponent(f.topic || "Enquiry via the website") +
        "&body=" + encodeURIComponent(body);
      say("Your mail client should be open with this message ready to send.");
    };

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(form);
      const f = Object.fromEntries(
        ["name", "email", "topic", "message", "website"].map((k) => [
          k, String(fd.get(k) || "").trim(),
        ])
      );

      let bad = false;
      for (const k of ["email", "message"]) {
        const el = form.querySelector(`[name="${k}"]`);
        const invalid = !f[k] || (k === "email" && !el.checkValidity());
        el.dataset.invalid = String(invalid);
        bad = bad || invalid;
      }
      if (bad) {
        say("An email address and a message are all it needs.");
        return;
      }

      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      say("Sending\u2026");
      try {
        const r = await fetch("/api/enquiry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(f),
        });
        if (!r.ok) throw new Error(String(r.status));
        form.reset();
        say("Sent. It lands directly in her inbox.");
      } catch {
        mailto(f);
      } finally {
        btn.disabled = false;
      }
    });
  }
})();
