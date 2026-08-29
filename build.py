"""
The deploy entry point.

Cloudflare Pages runs `python build.py`. Until now that file was V1's
generator, which writes its single-page site straight over the repo root.
V2 is the site as of 30 Aug 2026 and builds to that same root, so leaving
this as V1 meant every successful deploy would have overwritten the
current design with the old one.

It failed instead, on a KeyError for `speaking.close`, a field that moved
into `speaking.lede` when the Speaking page was rebuilt. That failure is
the only reason the promotion survived its first deploy.

So this file is now a shim. It builds V2 at the root and assembles dist,
which covers both Pages configurations: serving the repo root directly,
and serving a `dist` output directory.

V1's generator is preserved verbatim as build_v1.py. Nothing runs it. It
still reads `speaking.close`, which has been restored to the content file
so the file is not left broken, but running it would put V1 back at the
root and undo the promotion.

    python build.py          ->  the site, at the root, plus dist/
"""

import runpy
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> int:
    # build_v2 reads --root from sys.argv at import time, so it goes on
    # before the module is loaded. Any other argument Pages passes is left
    # alone and ignored.
    if "--root" not in sys.argv:
        sys.argv.append("--root")

    try:
        runpy.run_path(str(ROOT / "build_v2.py"), run_name="__main__")
    except SystemExit as stop:
        if stop.code:
            return int(stop.code)

    # Harmless when Pages serves the repo root, and required when it is
    # pointed at an output directory instead.
    try:
        runpy.run_path(str(ROOT / "release.py"), run_name="__main__")
    except SystemExit as stop:
        if stop.code:
            return int(stop.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
