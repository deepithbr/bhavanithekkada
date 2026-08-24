"""
Subset the wordmark face and write it as WOFF2.

    python tools/make_wordmark_font.py

The face sets one string on this site, her name in the hero, and nothing else.
Shipping all 288 glyphs of a 1MB brush font to render sixteen characters is the
kind of thing that quietly costs a phone user two seconds on a slow connection.

The character set is read from `identity.wordmark` rather than hard-coded, in
both cases plus a little punctuation. A-Z and a-z came out at 171KB, which is
most of the saving thrown away to carry sixty glyphs that never render. Deriving
it from the content file gets the same safety a fixed alphabet was buying, since
editing the name and rebuilding regenerates the subset to match.

Rerun this after changing `identity.wordmark`. build.py prints a warning if the
font is older than the content file.

Layout features are kept. A brush script relies on `calt` and `liga` to vary
repeated letters, and dropping them is what makes a script font look like it
has been typed rather than written.
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
SRC = ROOT / "_source" / "fonts" / "Black Rusher Free.otf"
OUT = ROOT / "assets" / "fonts" / "black-rusher.woff2"
CONTENT = ROOT / "content" / "bhavani.json"


def wanted_chars() -> str:
    ident = json.loads(CONTENT.read_text(encoding="utf-8"))["identity"]
    seed = f"{ident['wordmark']} {ident['shortName']} {ident['fullName']}"
    # Both cases of everything, because the hero sets the name in mixed case and
    # the content file stores it upper.
    chars = set(seed.upper()) | set(seed.lower()) | set(" .,'’-&")
    return "".join(sorted(c for c in chars if c.isprintable()))

FEATURES = "ccmp,liga,rlig,calt,kern,locl"


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"make_wordmark_font: missing {SRC}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    chars = wanted_chars()

    cmd = [
        sys.executable, "-m", "fontTools.subset", str(SRC),
        f"--text={chars}",
        f"--layout-features={FEATURES}",
        "--flavor=woff2",
        f"--output-file={OUT}",
        # The name table is kept: it carries the foundry, the copyright and the
        # licence URL, and stripping those from a font you are hosting is not a
        # thing to do by accident.
        "--name-IDs=*",
        "--notdef-outline",
        "--drop-tables+=DSIG",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
        return res.returncode

    before = SRC.stat().st_size
    after = OUT.stat().st_size
    print(f"{SRC.name}  {before / 1024:.0f} KB")
    print(f"{OUT.name}  {after / 1024:.1f} KB   "
          f"({after / before * 100:.1f}% of source)")
    print(f"subset to {len(chars)} characters: {chars.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
