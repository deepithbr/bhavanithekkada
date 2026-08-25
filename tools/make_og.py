"""
Share cards for V2.

One 1200x630 image per page, cropped from her own photographs with the same
focal points the site uses, written to v2/assets/og/. A link shared to
WhatsApp, LinkedIn or X shows her, not a blank rectangle; that gap is the
kind of thing a jury or a sponsor notices before the page even opens.

Pure photograph, no overlaid text: the platforms print the page title under
the card themselves, and text baked into an image cannot be translated,
resized or read aloud.

Run from the repository root after the image ladder exists.
"""

import json
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "v2" / "assets" / "og"

CARDS = {
    "index": "double-pole",
    "about": "portrait-studio",
    "journey": "ridge-sunrise",
    "media": "podium-gulmarg-2023",
    "journal": "classic-tracks",
    "partnership": "summit-solo",
    "speaking": "flag-almaty",
    "work-with-me": "lake-mountains",
}

W, H = 1200, 630


def main() -> int:
    lib = json.loads((ROOT / "content" / "images.json").read_text(encoding="utf-8"))
    by_slot = {i["slot"]: i for i in lib["images"]}
    OUT.mkdir(parents=True, exist_ok=True)

    for page, slot in CARDS.items():
        a = by_slot[slot]
        src = ROOT / "assets" / "img" / f"{a['file']}-{a['widths'][-1]}.webp"
        im = Image.open(src).convert("RGB")
        w, h = im.size
        fx, fy = a.get("focal") or (0.5, 0.5)

        # cover-crop to 1200x630 around the focal point
        target = W / H
        if w / h > target:
            cw, ch = int(h * target), h
            left = min(max(int(fx * w - cw / 2), 0), w - cw)
            box = (left, 0, left + cw, ch)
        else:
            cw, ch = w, int(w / target)
            top = min(max(int(fy * h - ch / 2), 0), h - ch)
            box = (0, top, cw, top + ch)
        card = im.crop(box).resize((W, H), Image.LANCZOS)
        card.save(OUT / f"{page}.jpg", "JPEG", quality=86, progressive=True)
        print(f"  og/{page}.jpg  from {slot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
