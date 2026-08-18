"""
Zip ./dist for a Cloudflare Pages direct upload.

Not Compress-Archive. PowerShell writes entry names with backslashes on
Windows, so `assets\\css\\site.css` arrives at Cloudflare as one file called
`assets\\css\\site.css` sitting at the root, every asset 404s, and the deploy
looks corrupt while the upload reports success. The ZIP spec requires forward
slashes; this writes them.

    python tools/make_zip.py
"""

import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "bhavani-site-dist.zip"


def main() -> int:
    if not DIST.is_dir():
        raise SystemExit("make_zip: no dist/. Run build.py then release.py first.")

    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    if not files:
        raise SystemExit("make_zip: dist/ is empty.")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, p.relative_to(DIST).as_posix())

    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
        bad = [n for n in names if "\\" in n]
        if bad:
            raise SystemExit(f"make_zip: backslash in {bad[:3]}")
        if "index.html" not in names:
            raise SystemExit("make_zip: index.html is not at the archive root.")

    print(f"{OUT.name}  {OUT.stat().st_size / 1024 / 1024:.2f} MB, {len(names)} files")
    for n in [x for x in names if not x.startswith("assets/img/")][:6]:
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
