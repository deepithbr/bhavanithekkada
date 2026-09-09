"""Her own frames for the journey years, from the Drive folder of 7 Sep 2026.

The client sent one photograph per year. Six of them were already in the
library under other names, so those years are rewired rather than
re-encoded and nothing is stored twice: 2016 is the frame already on that
card, and 2018, 2020, 2022 and 2024 are frames the site holds for other
sections. Seven are new.

Three are not here, and each is held back for its own reason, recorded in
`withheld` rather than quietly dropped.

The `year` field on every entry is when the photograph was taken, read off
its EXIF, not the year of the card it sits on. Three of them disagree with
the card and the disagreement is kept rather than smoothed: the file named
2013 was shot in December 2014 in front of a board reading DTE EVENTS
2014-15, and the files named 2019 and 2020 were both shot in March 2021.
They still illustrate the right beat of her story; they are simply not
from the year the card is about, and a caption that said otherwise would
be a claim nobody checked.

The `focal` point is what `object-fit: cover` keeps in frame. On anything
with a person in it that is the face, measured off the source and then
checked against the rendered card.

Run from the repository root:

    python tools/add_journey_images.py "C:/Users/HP/Desktop/journey"
"""

import json
import pathlib
import sys

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"
LIB = ROOT / "content" / "images.json"
CONTENT = ROOT / "content" / "bhavani.json"

SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None

WIDTHS = (480, 960, 1600)

# slot -> (source file, alt, focal, category, year the photograph was taken)
NEW = {
    "family-kodagu": (
        "1995.jpg",
        "Bhavani Thekkada and her family standing together outside a "
        "shopfront in Kodagu.",
        (0.50, 0.26), "archive", 2025,
    ),
    "ncc-commendation": (
        "2013.jpg",
        "Bhavani Thekkada in NCC uniform shaking hands with an Air Force "
        "officer in a directorate office, an events board on the wall "
        "behind them.",
        (0.36, 0.25), "archive", 2014,
    ),
    "summit-tricolour": (
        "2014(1).jpg",
        "Four climbers on a snow summit holding the Indian tricolour and an "
        "NCC flag open between them, a ridge line and cloud below.",
        (0.50, 0.35), "mountain", 2014,
    ),
    "ncc-drill": (
        "2015.jpg",
        "NCC air wing cadets standing at attention in ranks on a parade "
        "square, palms and trees behind them.",
        (0.50, 0.40), "archive", 2015,
    ),
    "glacier-portrait": (
        "2017.jpg",
        "Bhavani Thekkada in a red down jacket and crampons standing on a "
        "glacier below a steep face of snow and rock.",
        (0.47, 0.29), "mountain", 2017,
    ),
    "gulmarg-piste": (
        "2019.jpg",
        "A skier in a pink jacket at the top of a groomed piste above a "
        "wide snowfield, a chairlift running down the slope beside her.",
        (0.51, 0.52), "training", 2021,
    ),
    "khelo-podium-2021": (
        "2021.jpg",
        "Bhavani Thekkada on the top step of the podium at the second Khelo "
        "India National Winter Games presentation ceremony, the silver and "
        "bronze medallists either side of her.",
        (0.41, 0.41), "race", 2021,
    ),
}

# Already in the library, and she has now supplied the same frame from her
# own archive. Re-encoded from her copy where it is the better original,
# and moved off "unconfirmed", which it only ever carried because the
# first copy of it came out of the portfolio PDF rather than from her.
REGRADE = {
    "medals-detail": ("2022.jpg", "owned"),
}

# year on the journey timeline -> slot. Six of these are frames the
# library already holds; naming them here is what makes the card show her
# choice rather than ours.
WIRING = {
    "1995": "family-kodagu",
    "2013": "ncc-commendation",
    "2014": "summit-tricolour",
    "2015": "ncc-drill",
    # 2016 already shows the frame she sent for it.
    "2017": "glacier-portrait",
    "2018": "team-gulmarg",
    "2019": "gulmarg-piste",
    "2020": "downhill-tuck",
    "2021": "khelo-podium-2021",
    "2022": "medals-detail",
    # 2024 moves off a 674px crop of unconfirmed provenance and onto the
    # full-resolution frame from her own archive: the same photograph.
    "2024": "khelo-medals",
}


def encode(slot, src_path):
    """Write the webp ladder for one slot and return its natural size."""
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
        print("usage: add_journey_images.py <path to the journey folder>")
        return 2

    lib = json.loads(LIB.read_text(encoding="utf-8"))
    by_slot = {i["slot"]: i for i in lib["images"]}

    for slot, (rel, alt, focal, cat, year) in NEW.items():
        src_path = SRC / rel
        if not src_path.exists():
            print(f"  MISSING SOURCE  {slot}  {rel}")
            continue
        (w, h), widths = encode(slot, src_path)
        entry = {
            "slot": slot, "file": slot, "widths": widths,
            "natural": [w, h], "ratio": round(w / h, 4),
            "alt": alt, "credit": "Athlete's own archive",
            "year": year, "location": None, "category": cat,
            "focal": [focal[0], focal[1]], "rights": "owned",
        }
        if slot in by_slot:
            by_slot[slot].update(entry)
        else:
            lib["images"].append(entry)
            by_slot[slot] = entry
        print(f"  {slot:<20} {w}x{h}  widths={widths}")

    for slot, (rel, rights) in REGRADE.items():
        src_path = SRC / rel
        if slot not in by_slot or not src_path.exists():
            print(f"  REGRADE SKIPPED  {slot}")
            continue
        was = by_slot[slot]["rights"]
        (w, h), widths = encode(slot, src_path)
        by_slot[slot].update({
            "natural": [w, h], "ratio": round(w / h, 4),
            "widths": widths, "rights": rights,
            "credit": "Athlete's own archive",
        })
        print(f"  regrade {slot:<18} {was} -> {rights}  {w}x{h}")

    LIB.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    years = {y["year"]: y for y in content["story"]["timeline"]["years"]}
    for year, slot in WIRING.items():
        assert slot in by_slot, f"no such slot: {slot}"
        was = years[year].get("image")
        years[year]["image"] = slot
        print(f"  wired {year}  {was} -> {slot}")

    CONTENT.write_text(
        json.dumps(content, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"\nlibrary now holds {len(lib['images'])} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
