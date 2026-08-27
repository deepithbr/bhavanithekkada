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
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");

  // No IntersectionObserver, or the reader asked for less motion: show
  // everything at once. Only the reveal is skipped. This block used to
  // return out of the whole file instead, which unplugged every behaviour
  // after it on any page without a data-rise element, and for every
  // reduced-motion reader everywhere; the menu and the form are not motion.
  if (!rising.length || reduce.matches || !("IntersectionObserver" in window)) {
    rising.forEach((el) => (el.dataset.shown = "true"));
  } else {
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
  }

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

  /* ---- the hero rotation ---------------------------------------------- */

  // Three frames, 7 seconds each: stadium-screen pace, crossfaded by CSS. Reduced motion never
  // rotates, and a hidden tab pauses so the fade is never wasted offscreen.
  const slides = document.querySelectorAll('[data-slides="true"] .slide');
  if (slides.length > 1 && !reduce.matches) {
    const cap = document.getElementById("hero-cap");
    let at = 0;
    setInterval(() => {
      if (document.hidden) return;
      at = (at + 1) % slides.length;
      slides.forEach((s2, i) => (s2.dataset.on = String(i === at)));
      if (cap) cap.textContent = slides[at].dataset.cap || "";
    }, 7000);
  }

  /* ---- the mobile menu ------------------------------------------------ */

  // One button, one attribute. Escape closes and hands focus back; a tap on
  // any link closes it too, since every link leaves the page.
  const navEl = document.getElementById("nav");
  const navToggle = navEl && navEl.querySelector(".nav-toggle");
  if (navToggle) {
    const setOpen = (on) => {
      navEl.dataset.open = String(on);
      navToggle.setAttribute("aria-expanded", String(on));
    };
    navToggle.addEventListener("click", () => {
      setOpen(navEl.dataset.open !== "true");
    });
    navEl.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && navEl.dataset.open === "true") {
        setOpen(false);
        navToggle.focus();
      }
    });
    navEl.querySelectorAll(".nav-links a").forEach((a) =>
      a.addEventListener("click", () => setOpen(false))
    );
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
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Photograph viewer");
    box.tabIndex = -1;
    box.innerHTML =
      '<img alt="">' +
      '<span class="count"></span>' +
      '<button type="button" class="shut" aria-label="Close">&times;</button>' +
      '<nav><button type="button" data-go="-1" aria-label="Previous photograph">&larr;</button>' +
      '<button type="button" data-go="1" aria-label="Next photograph">&rarr;</button></nav>';
    document.body.appendChild(box);
    const pic = box.querySelector("img");
    const cap = null; // captions came off the photographs, 27 Aug list
    const count = box.querySelector(".count");
    const items = Array.from(fulls);
    let at = 0;

    const show = (i) => {
      at = (i + items.length) % items.length;
      const a = items[at];
      pic.src = a.getAttribute("href");
      pic.alt = (a.querySelector("img") || {}).alt || "";
      if (cap) cap.textContent = a.dataset.cap || "";
      count.textContent = (at + 1) + " / " + items.length;
    };

    let opener = null;
    const shut = () => {
      box.hidden = true;
      document.documentElement.style.overflow = "";
      if (opener) opener.focus();
    };
    box.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-go]");
      if (btn) {
        ev.stopPropagation();
        show(at + Number(btn.dataset.go));
        return;
      }
      shut();
    });
    addEventListener("keydown", (ev) => {
      if (box.hidden) return;
      if (ev.key === "Escape") shut();
      else if (ev.key === "ArrowLeft") show(at - 1);
      else if (ev.key === "ArrowRight") show(at + 1);
      else if (ev.key === "Tab") {
        // Focus stays inside the dialog: three buttons, wrapped.
        const stops = box.querySelectorAll("button");
        const first = stops[0];
        const last = stops[stops.length - 1];
        if (ev.shiftKey && document.activeElement === first) {
          ev.preventDefault();
          last.focus();
        } else if (!ev.shiftKey && document.activeElement === last) {
          ev.preventDefault();
          first.focus();
        }
      }
    });

    items.forEach((a, i) => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        opener = a;
        show(i);
        box.hidden = false;
        document.documentElement.style.overflow = "hidden";
        box.focus();
      });
    });
  }

  /* ---- the latitude rail ---------------------------------------------- */

  // Her life runs 12N to 66N; the rail maps the page to that span. Pure
  // presentation, desktop only, and absent under reduced motion because a
  // permanently moving marker is motion.
  if (matchMedia("(min-width: 1100px)").matches && !reduce.matches) {
    const rail = document.createElement("div");
    rail.className = "lat-rail";
    rail.setAttribute("aria-hidden", "true");
    rail.innerHTML =
      '<span class="lat-end" data-end="n">66&deg;N</span>' +
      "<i></i><b>12&deg;N</b>" +
      '<span class="lat-end" data-end="s">12&deg;N</span>';
    document.body.appendChild(rail);
    const dot = rail.querySelector("i");
    const label = rail.querySelector("b");
    let railTick = false;
    const railSync = () => {
      railTick = false;
      const de = document.documentElement;
      const max = de.scrollHeight - innerHeight;
      const p = max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 0;
      const lat = 12 + (66 - 12) * p;
      const y = (1 - p) * 100;
      dot.style.top = y + "%";
      label.style.top = y + "%";
      label.textContent = lat.toFixed(1) + "\u00b0N";
    };
    addEventListener("scroll", () => {
      if (railTick) return;
      railTick = true;
      requestAnimationFrame(railSync);
    }, { passive: true });
    railSync();
  }

  /* ---- the places arrive ----------------------------------------------- */

  // When the map enters, the fourteen pins appear one at a time in racing
  // order, 340ms apart: Kodagu first, the Chilean pair near the end. Runs
  // once. Reduced motion, or no observer, sees the finished map.
  const routeFig = document.querySelector(".route-map");
  if (routeFig) {
    const pins = Array.from(routeFig.querySelectorAll(".pin[data-stop]"))
      .sort((a, b) => Number(a.dataset.stop) - Number(b.dataset.stop));
    if (reduce.matches || !("IntersectionObserver" in window)) {
      pins.forEach((p) => (p.dataset.lit = "true"));
    } else {
      pins.forEach((p) => (p.dataset.lit = "false"));
      const arrive = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          arrive.disconnect();
          pins.forEach((pin, i) => {
            setTimeout(() => (pin.dataset.lit = "true"), 250 + i * 340);
          });
        }
      }, { threshold: 0.45 });
      arrive.observe(routeFig);
    }
  }

  /* ---- journal reading progress ---------------------------------------- */

  const readBar = document.getElementById("read-bar");
  if (readBar) {
    let readTick = false;
    const readSync = () => {
      readTick = false;
      const de = document.documentElement;
      const max = de.scrollHeight - innerHeight;
      readBar.style.setProperty(
        "--read", max > 0 ? (scrollY / max).toFixed(4) : 1);
    };
    addEventListener("scroll", () => {
      if (readTick) return;
      readTick = true;
      requestAnimationFrame(readSync);
    }, { passive: true });
    readSync();
  }

  /* ---- the press peek -------------------------------------------------- */

  // On a cursor screen, hovering a press row floats its photograph beside
  // the pointer. Touch screens and reduced motion never see it; the rows
  // stand on their own.
  const peek = document.querySelector(".press-peek");
  if (peek && matchMedia("(hover: hover)").matches && !reduce.matches) {
    const peekImg = peek.querySelector("img");
    let px = 0, py = 0, moveTick = false;
    const place = () => {
      moveTick = false;
      peek.style.left = Math.min(px + 24, innerWidth - 260) + "px";
      peek.style.top = Math.min(py + 16, innerHeight - 180) + "px";
    };
    document.querySelectorAll(".press-wire [data-peek]").forEach((row) => {
      row.addEventListener("mouseenter", () => {
        peekImg.src = row.dataset.peek;
        peek.dataset.on = "true";
      });
      row.addEventListener("mouseleave", () => {
        peek.dataset.on = "false";
      });
      row.addEventListener("mousemove", (ev) => {
        px = ev.clientX;
        py = ev.clientY;
        if (moveTick) return;
        moveTick = true;
        requestAnimationFrame(place);
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

    // speaking.html links across with ?topic=Speaking; honour it.
    const pre = new URLSearchParams(location.search).get("topic");
    if (pre) {
      const sel = form.querySelector('[name="topic"]');
      if (sel && [...sel.options].some((o) => o.value === pre)) sel.value = pre;
    }

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
        ["name", "organisation", "email", "topic", "message", "website"].map(
          (k) => [k, String(fd.get(k) || "").trim()]
        )
      );

      // Each miss is named at its own field, not only in the general note,
      // and focus lands on the first one so the fix is a keystroke away.
      let firstBad = null;
      for (const k of ["email", "message"]) {
        const el = form.querySelector(`[name="${k}"]`);
        const err = document.getElementById(el.getAttribute("aria-describedby"));
        const invalid = !f[k] || (k === "email" && !el.checkValidity());
        el.setAttribute("aria-invalid", String(invalid));
        el.dataset.invalid = String(invalid);
        if (err) err.hidden = !invalid;
        if (invalid && !firstBad) firstBad = el;
      }
      if (firstBad) {
        say("An email address and a message are all it needs.");
        firstBad.focus();
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
