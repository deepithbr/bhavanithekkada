"""The frames in her Drive folder that were not year cards, put to work.

Five of them earn a place. Three do not, and the reason is the same each
time: I cannot caption them truthfully or place them honestly, and a
photograph nobody can describe is not an asset, it is a guess.

The lectern frame is the one that changes a page rather than decorating
it. The Speaking page argues six things a decade on snow is worth to a
room, and its Persuasion card, about explaining an unfamiliar sport to
the person who can fund it, was illustrated with a group of skiers on a
snowfield. It now shows her at a lectern with a microphone.

The Chile racing frame goes into the media collage in place of a training
one. The collage is the shop window for her archive and a race in the
India suit outranks a session on an empty field.

Three go behind the journey as scenery. That layer has rules worth
keeping: three disjoint columns so one frame cannot appear twice side by
side, nothing that is also a card on the page, and the middle column,
which runs directly behind the route, holding only frames with nobody in
them. The Gulmarg village goes to the middle on that last rule; the wide
field and the lookout, both with figures in them, go out to the edges.

Held back, with reasons in withheld: the cut-out portrait, which needs a
designed ground rather than a slot in a photo mosaic, and two frames I
cannot date or place well enough to caption.
"""

import json
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"
LIB = ROOT / "content" / "images.json"
CONTENT = ROOT / "content" / "bhavani.json"

SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None

WIDTHS = (480, 960, 1600)

# slot -> (source file, alt, focal, category, year, location)
NEW = {
    "lectern-speaking": (
        "speaking.jpg",
        "Bhavani Thekkada speaking at a lectern with a microphone in front "
        "of her, in a dark blazer, greenery behind.",
        (0.50, 0.25), "portrait", 2024, None,
    ),
    "race-chile-skate": (
        "skiing.webp",
        "Bhavani Thekkada skating in the blue India race suit on an open "
        "course, spectators and a bare ridge line behind her.",
        (0.37, 0.20), "race", 2025, "Chile",
    ),
    "gulmarg-village": (
        "gulmarg.jpg",
        "Snow-laden pines and timber lodges below a bare white ridge at "
        "Gulmarg under a deep blue sky.",
        (0.55, 0.50), "training", 2021, None,
    ),
    "gulmarg-field": (
        "gulmarg1.jpg",
        "Three skiers small on a wide open snowfield below a forested "
        "slope and a bare mountain face.",
        (0.50, 0.45), "training", 2022, None,
    ),
    "alpine-lookout": (
        "skiing 1.jpg",
        "A skier in a red jacket standing with alpine skis at the top of a "
        "track through snow-covered pines, a peak beyond.",
        (0.49, 0.48), "training", 2021, None,
    ),
}


def encode(slot, src_path):
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    widths = [x for x in WIDTHS if x <= w] or [w]
    if widths[-1] != w and w < WIDTHS[-1]:
        widths.append(w)
    for target in widths:
        scaled = im.resize(
            (target, max(1, round(h * target / w))), Image.LANCZOS
        )
        scaled.save(OUT / f"{slot}-{target}.webp", "WEBP",
                    quality=82, method=6)
    return (w, h), widths


def main() -> int:
    if SRC is None or not SRC.exists():
        print("usage: add_extra_images.py <path to the journey folder>")
        return 2

    lib = json.loads(LIB.read_text(encoding="utf-8"))
    by_slot = {i["slot"]: i for i in lib["images"]}

    for slot, (rel, alt, focal, cat, year, loc) in NEW.items():
        src_path = SRC / rel
        if not src_path.exists():
            print(f"  MISSING SOURCE  {slot}  {rel}")
            continue
        (w, h), widths = encode(slot, src_path)
        entry = {
            "slot": slot, "file": slot, "widths": widths,
            "natural": [w, h], "ratio": round(w / h, 4),
            "alt": alt, "credit": "Athlete's own archive",
            "year": year, "location": loc, "category": cat,
            "focal": [focal[0], focal[1]], "rights": "owned",
        }
        if slot in by_slot:
            by_slot[slot].update(entry)
        else:
            lib["images"].append(entry)
            by_slot[slot] = entry
        print(f"  {slot:<20} {w}x{h}  widths={widths}")

    LIB.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    # The Persuasion card is about making an unfamiliar idea land with the
    # person who can back it, and it was illustrated with a snowfield.
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    for s in content["speaking"]["skills"]:
        if s["word"] == "Persuasion":
            print(f"  speaking Persuasion  {s['image']} -> lectern-speaking")
            s["image"] = "lectern-speaking"
    CONTENT.write_text(
        json.dumps(content, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"\nlibrary now holds {len(lib['images'])} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
