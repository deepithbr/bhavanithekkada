"""
Bring photographs from the athlete's own Drive archive into the image library.

Everything already in `assets/img` was extracted from the client-supplied
portfolio PDFs, which is why `images.json` carries a blanket rights warning: one
extracted frame still had an agency watermark on it. The files this script adds
come from Bhavani's own Drive folders instead, supplied by her directly, so they
carry `rights: "owned"` rather than `"unconfirmed"`.

Every slot on the page is filled, at the client's instruction, but not every
slot is filled the same way, and the difference is recorded rather than hidden.

Four of the fourteen map pins carry a photograph genuinely taken at that venue:
Harbin, Trondheim, Antillanca and Corralco. Those four have a real `location`,
and `footprint()` in build.py prints it under the picture.

The other ten, and the deck cards with no photograph of their own race, get an
image with no identifiable landmark in the frame: tracks in trees, a ridge line,
floodlit training, a tuck against open sky. Their `location` is deliberately
null so the card never claims they were shot there. The card supplies the
caption; the photograph is allowed to be atmosphere, but it is never allowed to
contradict the caption. That is the line held here: a wrong-venue landmark would
be a false claim, whereas unlabelled snow is not.

`holmenkollen` is the one deliberate exception. It sits on the Lygna pin, and
because its location differs from the pin's place name, the card prints
"Holmenkollen, Oslo" underneath. The reader is told where it was taken.

Run from the repository root. Idempotent: re-running rewrites the same files.
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

# Where the downloaded archive was unpacked. Passed in so the script does not
# hard-code a scratch path that will not exist on anyone else's machine.
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None

WIDTHS = (480, 960, 1600)

# slot -> (source file, alt, focal, category, year, location)
#
# `focal` is the point `object-fit: cover` keeps in frame, as fractions of the
# source. On anything with a person in it that is her face, not the middle of
# the picture. Every value here was set by measuring the face in the source and
# then checked against the rendered page.
NEW = {
    "portrait-studio": (
        "B612_20250630_204338_851.jpg",
        "Bhavani Thekkada in a white Reliance Foundation polo shirt, arms "
        "folded, photographed against a plain light background.",
        (0.50, 0.24), "portrait", 2025, None,
    ),
    "race-worldcup": (
        "Bhavani/2025/WC 25/Copy of IMG_9006.HEIC",
        "Bhavani Thekkada in the blue India race suit on the stadium loop in "
        "front of a full grandstand, advertising boards and national flags "
        "along the barrier behind her.",
        (0.42, 0.35), "race", 2025, "Trondheim, Norway",
    ),
    "flag-harbin": (
        "Bhavani/2025/AWG 25/Copy of IMG-20250210-WA0175.jpg",
        "Bhavani Thekkada holding the Indian flag open above her shoulders in "
        "her race bib at the Asian Winter Games.",
        (0.50, 0.34), "race", 2025, "Harbin, China",
    ),
    "chile-lake": (
        "Bhavani/2025/Chile/Copy of IMG-20250826-WA0011.jpg",
        "A lone skier crossing an open snowfield high above a lake and a line "
        "of volcanic peaks in southern Chile.",
        (0.41, 0.44), "race", 2025, "Antillanca, Chile",
    ),
    "chile-corralco": (
        "Bhavani/2025/Chile/Copy of IMG20250914122515.jpg",
        "Bhavani Thekkada on skis with three other racers at the foot of the "
        "piste, snow-covered slopes and a chairlift behind them.",
        (0.55, 0.40), "race", 2025, "Corralco, Chile",
    ),
    "holmenkollen": (
        "Bhavani/2025/Copy of IMG_9357.jpg",
        "Bhavani Thekkada standing on her skis in an India training top below "
        "a large ski jump tower.",
        (0.62, 0.44), "training", 2025, "Holmenkollen, Oslo",
    ),
    "republic-day-2016": (
        "Bhavani/6.jpg",
        "Massed marching contingents and a military band on the Republic Day "
        "parade route in New Delhi.",
        (0.50, 0.50), "archive", 2016, "New Delhi",
    ),
    "summit-solo": (
        "Bhavani/2018/Copy of P1140480.JPG",
        "A single climber standing on a rocky summit ridge with a horizon of "
        "snow peaks behind and cloud above.",
        (0.62, 0.42), "mountain", 2018, None,
    ),
    "course-glacier": (
        "Bhavani/2017/Copy of IMG_9486.JPG",
        "A full mountaineering course cohort in climbing kit, sitting and "
        "standing together on a glacier below a moraine slope.",
        (0.50, 0.62), "mountain", 2017, None,
    ),
    "nordic-podium": (
        "Bhavani/2022/2.jpg",
        "Two racers in bibs on the top two steps of a podium at a Nordic "
        "arena, one being handed a prize.",
        (0.45, 0.20), "race", 2022, None,
    ),
    "khelo-medals": (
        "Bhavani/2024/Copy of IMG_3275.HEIC",
        "Bhavani Thekkada standing with her skis and several medals around "
        "her neck in front of a Khelo India Winter Games backdrop.",
        (0.50, 0.31), "race", 2024, "Ladakh",
    ),
    "classic-tracks": (
        "Bhavani/2025/Copy of IMG-20250130-WA0046.jpg",
        "Set classic tracks running away through deep snow and heavily laden "
        "pines, a skier small in the distance.",
        (0.62, 0.47), "training", 2025, None,
    ),
    "snow-ridge-line": (
        "Bhavani/2026/New Zealand/Copy of IMG_6565.HEIC",
        "A long line of skiers spread across an open snow ridge under a wide "
        "pale sky, arms raised.",
        (0.50, 0.52), "training", 2026, None,
    ),
    "night-training": (
        "Bhavani/2026/New Zealand/Copy of IMG_6551.HEIC",
        "Skiers training on a floodlit trail after dark, headlamps and lit "
        "snow against a black sky.",
        (0.50, 0.52), "training", 2026, None,
    ),
    "family-kodava": (
        "Bhavani/2019/Copy of 4CAAA9BB-BB71-4BF5-B76A-108B39E19310.jpg",
        "Bhavani Thekkada on stage with her mother and father at a Kodava "
        "Samaja felicitation in Kodagu.",
        (0.50, 0.45), "archive", 2019, "Kodagu",
    ),
    "nordic-overlook": (
        "Bhavani/2022/Copy of IMG_2461.HEIC",
        "A skier in an India race suit standing on her skis at the top of a "
        "cleared slope, a northern town spread out in the valley below.",
        (0.43, 0.40), "training", 2022, None,
    ),
    "track-solo-pines": (
        "Bhavani/2019/Copy of IMG_1281.JPG",
        "A single skier on a set track cut through deep snow, heavily laden "
        "conifers standing close on both sides.",
        (0.47, 0.62), "training", 2019, None,
    ),
    "double-pole": (
        "Bhavani/2020/Copy of 168E1E5E-380F-476C-8006-397EAB4F252E.JPG",
        "Bhavani Thekkada mid-stride on skis with both poles planted, a "
        "treeline and open sky behind her.",
        (0.48, 0.28), "training", 2020, None,
    ),
    "downhill-tuck": (
        "Bhavani/2020/Copy of A037A62B-A96F-420F-92E2-FF88F2B0AB10.JPG",
        "Bhavani Thekkada low in a tuck on skis, carrying speed across an "
        "open slope against a clear sky.",
        (0.52, 0.42), "race", 2020, None,
    ),
    # The five below exist to break up repetition rather than to fill a hole.
    # Three photographs were each carrying three different slots, which is what
    # made the page feel like it kept showing you the same picture: `ruapehu`,
    # `race-planica-elbrus` and `khelo-ice-sculpture`. Each is now down to the
    # one or two slots it genuinely belongs to.
    "first-skis-2018": (
        "Bhavani/2018/Copy of IMG_0788.JPG",
        "A skier in a red jacket coming down an open piste, poles trailing, "
        "carving across the fall line.",
        (0.50, 0.15), "training", 2018, None,
    ),
    "ridge-sunrise": (
        "Bhavani/2018/Copy of DSC05311.JPG",
        "A roped line of climbers working up a steep snow slope at first "
        "light, a horizon of peaks falling away below them.",
        (0.55, 0.55), "mountain", 2018, None,
    ),
    "nz-snowfarm": (
        "Bhavani/2026/New Zealand/Copy of IMG_6534.HEIC",
        "A group of skiers standing together on their skis on an open snow "
        "field under a heavy bank of cloud.",
        (0.50, 0.53), "training", 2026, "New Zealand",
    ),
    "podium-gulmarg-2023": (
        "Bhavani/2023/Copy of IMG_5350.HEIC",
        "Three racers on the podium at a cross-country championship in "
        "Gulmarg, medals around their necks and the event banner behind.",
        (0.50, 0.36), "race", 2023, "Gulmarg, Jammu and Kashmir, India",
    ),
    "contingent-2021": (
        "Bhavani/2021/Copy of 231891cd-3794-49d7-91c4-82e48f3e4ee5.jpg",
        "The full India contingent lined up with their medals at a Khelo "
        "India National Winter Games presentation ceremony.",
        (0.50, 0.42), "race", 2021, None,
    ),
    "team-gulmarg": (
        "Bhavani/7.jpg",
        "A full squad of skiers gathered with their skis upright among snow-"
        "covered pines.",
        (0.50, 0.45), "training", 2022, None,
    ),
}

# Where each new slot is wired. Paths are walked from the root of bhavani.json.
# Anything not listed here keeps whatever it already had.
WIRING = [
    (["story", "beats", 0], "family-kodava"),
    (["story", "beats", 2], "republic-day-2016"),
    (["careerMilestones", 0], "nordic-podium"),
    (["careerMilestones", 1], "snow-ridge-line"),
    (["careerMilestones", 3], "night-training"),
    (["careerMilestones", 6], "classic-tracks"),
    (["careerMilestones", 7], "chile-corralco"),
    (["careerMilestones", 8], "race-worldcup"),
    # Harbin, Trondheim, Antillanca and Corralco are the four pins where the
    # photograph was genuinely taken at the venue, so those four carry a
    # location and the card prints it. The rest are atmosphere with no
    # identifiable landmark in frame, and their `location` is deliberately null
    # so the card never claims they were shot there.
    (["internationalFootprint", 2], "nordic-overlook"),
    (["internationalFootprint", 5], "track-solo-pines"),
    (["internationalFootprint", 6], "double-pole"),
    (["internationalFootprint", 7], "holmenkollen"),
    (["internationalFootprint", 8], "flag-harbin"),
    (["internationalFootprint", 9], "race-worldcup"),
    (["internationalFootprint", 10], "chile-lake"),
    (["internationalFootprint", 11], "chile-corralco"),
    (["internationalFootprint", 12], "team-gulmarg"),
    (["internationalFootprint", 13], "downhill-tuck"),
    (["press", 2], "khelo-medals"),
    (["press", 8], "trophy-karnataka"),
    # De-duplication. Each of these three slots was showing a photograph that
    # already appeared twice elsewhere on the page.
    #
    #   ruapehu              beat 3, mountainAchievements 1, cert 3  -> 1 use
    #   race-planica-elbrus  deck 2, map 3, mountainAchievements 0   -> 2 uses
    #   khelo-ice-sculpture  deck 10, map 1, press 9                 -> 1 use
    #
    # Each keeps the slot it actually belongs to. `ruapehu` is a photograph of
    # Mt. Ruapehu, so it stays on the summit card. `race-planica-elbrus` is her
    # racing in a World Championships bib, so it stays on the Planica race and
    # the Planica pin, and the Elbrus summit card gets a real climbing frame
    # instead of the composited mountain behind her. `khelo-ice-sculpture` is
    # Gulmarg, so the Gulmarg pin gets a Gulmarg podium and the 2026 Khelo India
    # card keeps the sculpture.
    (["story", "beats", 3], "first-skis-2018"),
    (["mountainAchievements", 0], "ridge-sunrise"),
    (["certificationPhases", 3], "nz-snowfarm"),
    (["internationalFootprint", 1], "podium-gulmarg-2023"),
    (["press", 5], "contingent-2021"),
    # trophy-ceremony was already in the library and used nowhere. A Khelo India
    # closing ceremony is a better fit for a medal-tally story than a repeat of
    # the snow sculpture.
    (["press", 9], "trophy-ceremony"),
    # Both of these were illustrated by a photograph of skis. The first two
    # phases are the climbing ones, so they now get climbing photographs.
    (["certificationPhases", 0], "summit-solo"),
    (["certificationPhases", 1], "course-glacier"),
]


def encode(slot, src_path):
    """Write the webp ladder for one slot and return its natural size."""
    im = Image.open(src_path)
    im = im.convert("RGB")
    w, h = im.size
    widths = [x for x in WIDTHS if x <= w] or [w]
    if widths[-1] != w and w < WIDTHS[-1]:
        widths.append(w)
    for target in widths:
        scaled = im.resize(
            (target, max(1, round(h * target / w))), Image.LANCZOS
        )
        dest = OUT / f"{slot}-{target}.webp"
        scaled.save(dest, "WEBP", quality=82, method=6)
    return (w, h), widths


def main() -> int:
    if SRC is None or not SRC.exists():
        print("usage: add_images.py <path to unpacked Drive archive>")
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
            "slot": slot,
            "file": slot,
            "widths": widths,
            "natural": [w, h],
            "ratio": round(w / h, 4),
            "alt": alt,
            "credit": "Athlete's own archive",
            "year": year,
            "location": loc,
            "category": cat,
            "focal": [focal[0], focal[1]],
            "rights": "owned",
        }
        if slot in by_slot:
            by_slot[slot].update(entry)
        else:
            lib["images"].append(entry)
            by_slot[slot] = entry
        print(f"  {slot:<20} {w}x{h}  widths={widths}")

    LIB.write_text(
        json.dumps(lib, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    for path, slot in WIRING:
        node = content
        for step in path:
            node = node[step]
        node["image"] = slot
        print(f"  wired {'/'.join(str(p) for p in path):<32} -> {slot}")

    CONTENT.write_text(
        json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nlibrary now holds {len(lib['images'])} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
