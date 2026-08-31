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
    // The incoming frame fades in ON TOP of the old one, which stays fully
    // opaque beneath until it is covered. Fading both at once let the white
    // page ground bleed through mid-fade, a milky flash every rotation.
    let at = 0;
    let z = 1;
    setInterval(() => {
      if (document.hidden) return;
      at = (at + 1) % slides.length;
      const next = slides[at];
      next.style.zIndex = String(++z);
      next.dataset.on = "true";
      setTimeout(() => {
        slides.forEach((s2, i) => {
          if (i !== at) {
            s2.dataset.on = "false";
            s2.style.zIndex = "0";
          }
        });
      }, 1300);
    }, 7000);
  }

  /* ---- the level of competition, typed --------------------------------- */

  // Her record is still being written, so the hero writes it: each figure
  // types in, holds, erases, and the next one follows. The lines come from
  // the ghost spans already in the markup, so a reader with no JavaScript
  // still sees the first figure and a screen reader gets the plain list.
  // Reduced motion holds the first figure and never moves.
  const typer = document.querySelector('.hero-cred[data-type="true"]');
  if (typer && !reduce.matches) {
    const lines = [...typer.querySelectorAll(".cred-ghost")].map((g) => [
      g.querySelector("b").textContent,
      g.querySelector("span").textContent,
    ]);
    const nEl = typer.querySelector(".cred-n");
    const tEl = typer.querySelector(".cred-t");

    if (lines.length > 1) {
      const TYPE = 46;
      const ERASE = 22;
      const HOLD = 2100;
      const GAP = 130;
      let li = 0;

      // A hidden tab should not burn through the cycle; wait and retry.
      const step = (fn, ms) =>
        setTimeout(() => (document.hidden ? step(fn, 400) : fn()), ms);

      const write = (full, i, done) => {
        nEl.textContent = full[0].slice(0, Math.min(i, 2));
        tEl.textContent = full[1].slice(0, Math.max(0, i - 2));
        if (i >= 2 + full[1].length) step(done, HOLD);
        else step(() => write(full, i + 1, done), i < 2 ? TYPE * 2 : TYPE);
      };

      const erase = (full, i, done) => {
        nEl.textContent = full[0].slice(0, Math.min(i, 2));
        tEl.textContent = full[1].slice(0, Math.max(0, i - 2));
        if (i <= 0) step(done, GAP);
        else step(() => erase(full, i - 1, done), ERASE);
      };

      const cycle = () => {
        const full = lines[li];
        write(full, 0, () =>
          erase(full, 2 + full[1].length, () => {
            li = (li + 1) % lines.length;
            cycle();
          })
        );
      };

      // The markup ships the first figure written out; erase it, then start.
      const opener = lines[0];
      erase(opener, 2 + opener[1].length, () => {
        li = 0;
        cycle();
      });
    }
  }

  /* ---- the drawn stroke ------------------------------------------------ */

  // The stroke under the destination draws itself once, when its panel
  // arrives. Reduced motion gets it already drawn, from CSS, and this
  // still marks it so nothing is left half-scratched.
  const drawn = document.querySelectorAll(".mark-draw");
  if (drawn.length) {
    const pen = new IntersectionObserver(
      (rows, obs) => {
        rows.forEach((row) => {
          if (row.isIntersecting) {
            row.target.dataset.drawn = "true";
            obs.unobserve(row.target);
          }
        });
      },
      { rootMargin: "0px 0px -18% 0px" }
    );
    drawn.forEach((d) => pen.observe(d));
  }

  /* ---- the card stack -------------------------------------------------- */

  // Every homepage section holds while the next one rises over it. A card
  // the height of the viewport pins at top 0; a card taller than the
  // viewport has to pin at a negative top so its LAST screenful is what
  // holds, or everything past the first screen can never be scrolled to.
  // That offset is the card's own height, which CSS cannot read, so it is
  // measured here and re-measured whenever a card changes size.
  const stack = document.querySelector(".stack");
  const wide = window.matchMedia("(min-width: 900px)");
  if (stack && stack.children.length > 1) {
    const cards = [...stack.children];

    const layout = () => {
      if (!wide.matches) {
        cards.forEach((c2) => {
          c2.style.position = "";
          c2.style.top = "";
        });
        return;
      }
      const vh = window.innerHeight;
      cards.forEach((c2) => {
        const h = c2.getBoundingClientRect().height;
        c2.style.position = "sticky";
        c2.style.top = h > vh ? Math.round(vh - h) + "px" : "0px";
      });
    };

    layout();
    wide.addEventListener("change", layout);

    // Late layout shifts move these numbers: fonts landing, a photograph
    // decoding, the typed line changing the chip's width. Watching the
    // cards catches all of it. Setting `top` never changes a height, so
    // this cannot feed itself.
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(layout);
      cards.forEach((c2) => ro.observe(c2));
    } else {
      window.addEventListener("resize", layout);
    }
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
  // order: Kodagu first, the Chilean pair near the end. Runs once. Reduced
  // motion, or no observer, sees the finished map. The lines stage went out
  // with the lines on 31 Aug; three stages are left.
  const routeFig = document.querySelector(".route-map");
  if (routeFig) {
    const pins = Array.from(routeFig.querySelectorAll(".pin[data-stop]"))
      .sort((a, b) => Number(a.dataset.stop) - Number(b.dataset.stop));
    const STEP = 150;
    const FIRST = 220;

    // The client's order: every dot she will stand on comes up first, and
    // La Clusaz arrives last, on its own. Each stage waits for the one
    // before it to finish rather than racing it; the first pass had the
    // destination land while the lines were still drawing.
    const run = () => {
      pins.forEach((pin, i) => {
        setTimeout(() => (pin.dataset.lit = "true"), FIRST + i * STEP);
      });
      const lit = FIRST + pins.length * STEP;
      const at = (ms, stage) =>
        setTimeout(() => (routeFig.dataset.stage = stage), ms);
      at(lit + 250, "plan");        // the three stops before the Games
      at(lit + 1500, "dest");       // La Clusaz, alone
      at(lit + 2800, "rest");       // and the rest steps back
    };

    if (reduce.matches || !("IntersectionObserver" in window)) {
      pins.forEach((p2) => (p2.dataset.lit = "true"));
      routeFig.dataset.stage = "rest";
    } else {
      pins.forEach((p2) => (p2.dataset.lit = "false"));
      const arrive = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          arrive.disconnect();
          run();
        }
      }, { threshold: 0.3 });
      arrive.observe(routeFig);
    }
  }

  /* ---- the journey draws itself ---------------------------------------- */

  const jr = document.querySelector(".jr");
  if (jr) {
    const svg = jr.querySelector(".jr-path");
    const nodes = Array.from(jr.querySelectorAll(".jr-node"));
    const runs = Array.from(svg.querySelectorAll(".jr-run"));
    const tail = svg.querySelector(".jr-tail");
    const clip = svg.querySelector(".jr-clip-r");
    // Where the record stops and the plan starts.
    const lastPast =
      nodes.filter((nd) => nd.dataset.kind !== "ahead").length - 1;

    let pts = [];
    let H = 0;

    // The route, rebuilt in the track's own pixels. The markup's path is
    // only the no-script fallback; its viewBox is stretched about eight
    // times harder across than down, and a stroke under a transform that
    // lopsided renders wrong or not at all.
    const draw = () => {
      if (getComputedStyle(svg).display === "none") { H = 0; return; }
      const box = jr.getBoundingClientRect();
      if (!box.width || !box.height) { H = 0; return; }
      H = box.height;
      const W = box.width;
      svg.setAttribute("viewBox", `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
      svg.setAttribute("preserveAspectRatio", "none");
      pts = nodes.map((nd) => {
        const d = nd.querySelector(".jr-dot").getBoundingClientRect();
        return [d.left - box.left + d.width / 2,
                d.top - box.top + d.height / 2];
      });

      // Vertical handles half the gap long: the curve leaves one marker
      // straight down and meets the next straight down, so both halves
      // of every bend match and the join does not show.
      const seg = (a, z) => {
        let d = `M${pts[a][0].toFixed(1)},${pts[a][1].toFixed(1)}`;
        for (let i = a; i < z; i++) {
          const h = (pts[i + 1][1] - pts[i][1]) * 0.5;
          d += ` C${pts[i][0].toFixed(1)},${(pts[i][1] + h).toFixed(1)}` +
               ` ${pts[i + 1][0].toFixed(1)},${(pts[i + 1][1] - h).toFixed(1)}` +
               ` ${pts[i + 1][0].toFixed(1)},${pts[i + 1][1].toFixed(1)}`;
        }
        return d;
      };

      runs[0].setAttribute("d", seg(0, lastPast));
      if (runs[1]) runs[1].setAttribute("d", seg(lastPast, pts.length - 1));

      // And it does not stop at the last year. A short tail, in a stroke
      // that fades to nothing, because the target is the point of the
      // plan rather than the end of anything.
      const end = pts[pts.length - 1];
      const drop = Math.min(H - end[1] - 4, 150);
      if (tail && drop > 20) {
        tail.setAttribute("d",
          `M${end[0].toFixed(1)},${end[1].toFixed(1)}` +
          ` C${end[0].toFixed(1)},${(end[1] + drop * 0.6).toFixed(1)}` +
          ` ${(W / 2).toFixed(1)},${(end[1] + drop * 0.5).toFixed(1)}` +
          ` ${(W / 2).toFixed(1)},${(end[1] + drop).toFixed(1)}`);
      }
      clip.setAttribute("x", "-20");
      clip.setAttribute("width", (W + 40).toFixed(0));
    };

    // The drawing front sits about three quarters of the way down the
    // screen, so a year lights just after it comes into view rather than
    // at the moment it clips the bottom edge.
    const FRONT = 0.76;

    const sync = () => {
      if (!H) {
        // The rail layout. No route to draw, so each year lights on its
        // own rectangle as it comes up the screen, and never unlights.
        for (const nd of nodes) {
          if (nd.dataset.lit === "true") continue;
          if (nd.getBoundingClientRect().top < innerHeight * 0.92) {
            nd.dataset.lit = "true";
          }
        }
        return;
      }
      const top = jr.getBoundingClientRect().top;
      const at = Math.max(0, Math.min(H, innerHeight * FRONT - top));
      // The scenery drifts against the route on the same number.
      jr.style.setProperty("--jr-p", (at / H).toFixed(3));
      clip.setAttribute("y", "0");
      clip.setAttribute("height", (at + 6).toFixed(1));
      for (let i = 0; i < nodes.length; i++) {
        nodes[i].dataset.lit = at >= pts[i][1] - 8 ? "true" : "false";
      }
    };

    const all = () => {
      draw();
      if (H) {
        clip.setAttribute("height", (H + 40).toFixed(0));
      }
      for (const nd of nodes) nd.dataset.lit = "true";
    };

    if (reduce.matches) {
      // Nothing animates, so nothing is staged: the whole route at once.
      all();
      addEventListener("resize", () => { draw(); if (H) clip.setAttribute("height", (H + 40).toFixed(0)); });
    } else {
      draw();
      sync();
      let tick = false;
      const onScroll = () => {
        // A background tab never runs the frame, so the latch would be
        // set once and the route frozen from then on. Nothing is being
        // painted there anyway, so keep the state right and skip it.
        if (document.hidden) { tick = false; sync(); return; }
        if (tick) return;
        tick = true;
        requestAnimationFrame(() => { tick = false; sync(); });
      };
      addEventListener("scroll", onScroll, { passive: true });
      document.addEventListener("visibilitychange", () => {
        tick = false;
        sync();
      });
      let rt;
      addEventListener("resize", () => {
        clearTimeout(rt);
        rt = setTimeout(() => { draw(); sync(); }, 120);
      });
      // The photographs settle the track's height after they load, and
      // the markers move with it.
      addEventListener("load", () => { draw(); sync(); });
    }

    /* ---- and a year opens ---------------------------------------------- */

    // Hover and :focus-visible are CSS. This is the tap, the click, and
    // keeping aria-expanded true to what is on screen. One open at a
    // time: the panels overlap their neighbours by design.
    const shut = (except) => {
      for (const nd of nodes) {
        if (nd === except || !nd.hasAttribute("data-open")) continue;
        nd.removeAttribute("data-open");
        nd.querySelector(".jr-hit").setAttribute("aria-expanded", "false");
      }
    };

    for (const nd of nodes) {
      const hit = nd.querySelector(".jr-hit");
      hit.addEventListener("click", () => {
        const open = nd.hasAttribute("data-open");
        shut(nd);
        if (open) nd.removeAttribute("data-open");
        else nd.setAttribute("data-open", "");
        hit.setAttribute("aria-expanded", open ? "false" : "true");
      });
    }

    // Anywhere else closes it, which is the only way off a panel on a
    // touch screen.
    document.addEventListener("click", (ev) => {
      if (!ev.target.closest(".jr-node")) shut(null);
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      const open = jr.querySelector(".jr-node[data-open] .jr-hit");
      shut(null);
      if (open) open.focus();
    });
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
