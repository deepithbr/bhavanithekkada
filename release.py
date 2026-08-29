"""
Assemble the folder that actually gets uploaded.

The project directory holds source the public site must not carry: the extracted
PDFs and raw photographs in _source (75 files, some of them press imagery we
deliberately excluded), the content model, the generator and the handover docs.

    python release.py

Writes ./dist, which is the whole deployable site and nothing else.
"""

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"

# Everything the browser asks for, and nothing it does not. `journal/` is only
# present when at least one post is published, so it is copied if it exists.
# V2 is the site now and builds to the root, so every page it writes ships
# from here. /v2 rides along unchanged for anyone holding a review link.
SHIP_FILES = ["index.html", "journal.html", "achievements.html",
              "journey.html", "media.html", "partnership.html",
              "speaking.html", "contact.html", "404.html"]
SHIP_DIRS = ["assets", "journal",
             # The journal editor and the V2 build ride along so both are
             # reachable on the deployed site: /admin for her writing room,
             # /v2 for the redesign under client review.
             "admin", "v2"]


def main() -> int:
    missing = [f for f in SHIP_FILES if not (ROOT / f).exists()]
    if missing:
        raise SystemExit(f"release: missing {missing}. Run build.py first.")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    for f in SHIP_FILES:
        shutil.copy2(ROOT / f, DIST / f)
    for d in SHIP_DIRS:
        src = ROOT / d
        if src.exists():
            shutil.copytree(src, DIST / d)

    # Firebase, Netlify and Cloudflare Pages all read this. Long cache on the
    # fingerprinted assets, none on the document, matching serve.py.
    #
    # Written to the repo root as well as dist. Pages reads _headers from
    # the root of whatever it serves, and this project keeps functions/ at
    # the repo root, which only works if Pages is pointed at the root. In
    # that setup a dist-only _headers is never deployed and the cache and
    # security headers silently do nothing.
    headers = (
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "\n"
        "/index.html\n"
        "  Cache-Control: no-cache\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
    )
    (DIST / "_headers").write_text(headers, encoding="utf-8")
    (ROOT / "_headers").write_text(headers, encoding="utf-8")

    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"dist/  {len(files)} files, {total / 1024 / 1024:.2f} MB")
    for p in files[:4]:
        print(f"  {p.relative_to(DIST)}")
    print(f"  ... and {len(files) - 4} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
