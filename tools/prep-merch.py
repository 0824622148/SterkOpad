#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - merch photo prep
===========================================

Turns the raw product renders in "Merch Products/" into the WebP tiles the
apparel page uses. Source files are never modified. Re-runnable.

Why this is not just a resize
-----------------------------

The sources do not agree with each other. The original studio shots sit on a
pale sweep that differs per file - sampling the four corners of each:

  tee     179 186 195 206
  cap     177 254 204 254   <- white down the right edge, grey down the left
  hoodie  178 182 186 209

and the 2026 lookbook shoots the white tee on pure black and the black tee on
pure white. Left alone that is four different backdrops across one product row.
On top of it the older sources are ~2:3 portrait while the card tile is 4:5, so
the old CSS letterboxed roughly a third of every tile away.

This script settles all of it: crop to the card's real 4:5, size each garment
to a common optical scale, and flatten every backdrop onto ONE colour, PLATE.
The CSS paints .merch-card__media the same value, so photo and tile read as a
single continuous surface rather than a rectangle floating on a card.

How the backdrop is removed
---------------------------

Breadth-first fill seeded from the border, walking only through backdrop-
coloured pixels - pale ones for the sweep, dark ones for the lookbook's white
tee, chosen per entry by the "key" field.

Two earlier attempts are worth recording so they are not tried again:

  * The colour-delta flood fill from prep-hero-art.py. There is no tolerance
    that works for all of these - at tol=8 the old tee keys cleanly at 44%
    kept while the hoodie collapses to 5%.
  * A plain "recolour every pale pixel outside the garment's bounding box"
    threshold. A bounding box is a rectangle and a garment is not, so the
    sweep survived in the box's corners and every tile showed a faint
    rectangle inside it - the exact artefact this script exists to remove.

The fill cannot reach anything the garment silhouette encloses, so the chest
logo is safe without needing to be masked at all.

Usage:  python tools/prep-merch.py
        python tools/prep-merch.py --probe "Merch Products/New Item.png"
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")


# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "Merch Products")
OUT_DIR = os.path.join(ROOT, "images", "merch")


# ------------------------------------------------------------------
# Manifest
# ------------------------------------------------------------------
# bbox is the garment in source pixels, measured with --probe and then checked
# by eye. It excludes the cast shadow, which is part of the backdrop.
MANIFEST = [
    # From the 2026 lookbook, merch.pdf page 5. The white colourway is page 1 —
    # same artwork, logo bounding boxes matching to a pixel, shot on black
    # rather than white, so it needs key="dark". "Tee White.png" is kept in
    # Merch Products/ ready to add as a second card whenever the range is
    # split by colour; the page currently lists one tee in two colourways.
    {"slug": "tee-black", "src": "Tee Black.png", "bbox": (250, 275, 1421, 1364),
     "key": "light", "fill_w": 0.92},
    # Older shots. These carry the previous large centre-chest logo rather than
    # the lookbook's small left chest, so the row is not visually consistent.
    # Replace them with lookbook-style shots when those exist.
    {"slug": "hoodie",    "src": "Hoodie.png",    "bbox": (64, 80, 468, 580)},
    {"slug": "cap",       "src": "Cap.png",       "bbox": (36, 154, 456, 550)},
]

# The one light surface on the site. Must stay in step with --plate in :root.
PLATE = (237, 237, 235)

TILE_W, TILE_H = 560, 700          # 4:5, the aspect .merch-card__media declares
FILL_H = 0.76                      # garment height as a fraction of the tile
FILL_W = 0.82                      # ...or width, whichever binds first
CENTRE_Y = 0.47                    # garment's optical centre, slightly high
QUALITY = 82

# Anything at least this light outside the garment box is backdrop. The sweep
# bottoms out near 175 at the corners and the garments are black, so there is
# a wide margin either side of this.
KEY_THRESHOLD = 150

# ...and the mirror of it for the lookbook's white tee, which is shot on pure
# black. The garment's darkest shading sits well above this.
DARK_KEY_THRESHOLD = 60

# The storefront render spells the label "STERK PAD" - the record glyph that
# forms the O has come away from it - and does so on the fascia, the right-hand
# wall sign, the counter front and the pavement A-frame.
#
# This box is the largest crop that contains none of those four: it stops above
# the counter and short of the wall sign, leaving the pegboard tee rack, the cap
# shelf and the track lighting. The garments on the rack still carry the wrong
# logo, so .hero--store also drops the whole thing to 0.3 opacity. Even then it
# is readable if you look for it - dimming is mitigation, not a fix. The render
# needs replacing; when it is, revisit this box and that opacity together.
HERO = {
    "src": "Store front.png",
    "slug": "store-front",
    "box": (0, 590, 760, 905),     # x0, y0, x1, y1 in the 1024x1536 source
    "out": (1440, 600),
    "quality": 68,
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def kb(path):
    return os.path.getsize(path) // 1024


def probe(path):
    """
    Print the garment bounding box, to seed a new MANIFEST entry.

    Reads the corners first to work out which way round the shot is, so this
    is useful on a black-backdrop file too - testing for dark pixels on one of
    those just returns the whole frame.
    """
    im = Image.open(path).convert("L")
    w, h = im.size
    corners = [im.getpixel(p) for p in ((3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4))]
    dark_bg = sum(corners) / 4 < 128

    if dark_bg:
        mask = im.point(lambda v: 255 if v > DARK_KEY_THRESHOLD else 0)
    else:
        mask = im.point(lambda v: 255 if v < KEY_THRESHOLD else 0)

    box = mask.getbbox()
    print("%s  %dx%d  key=%-5s bbox = %s"
          % (os.path.basename(path), w, h, "dark" if dark_bg else "light", box))
    return box


def flatten_backdrop(rgb, key="light"):
    """
    Return a copy with the backdrop replaced by PLATE.

    Breadth-first fill seeded from the border, walking only through backdrop-
    coloured pixels. Because it can reach nothing that the garment silhouette
    encloses, the chest logo survives untouched while the sweep and the cast
    shadow around the garment are flattened.

    A plain "every pale pixel" threshold was tried first and is wrong: the
    garment bounding box is a rectangle, the garment is not, so the sweep
    survived in the box's corners and each tile showed a faint rectangle
    inside it - the very artefact this script exists to remove.

    key="light"  backdrop is the pale studio sweep (the original three shots)
    key="dark"   backdrop is black (the white tee from the lookbook, which is
                 shot on black - the black tee in the same set is on white)
    """
    from collections import deque

    w, h = rgb.size
    grey = rgb.convert("L")
    gpx, px = grey.load(), rgb.load()

    if key == "light":
        is_backdrop = lambda v: v >= KEY_THRESHOLD
    elif key == "dark":
        is_backdrop = lambda v: v <= DARK_KEY_THRESHOLD
    else:
        raise ValueError("unknown key mode: " + key)

    seen = bytearray(w * h)
    q = deque()

    def seed(x, y):
        i = y * w + x
        if not seen[i] and is_backdrop(gpx[x, y]):
            seen[i] = 1
            px[x, y] = PLATE
            q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                seed(nx, ny)

    return rgb


def build_tile(entry):
    src = os.path.join(SRC_DIR, entry["src"])
    out = os.path.join(OUT_DIR, entry["slug"] + ".webp")

    im = Image.open(src).convert("RGB")
    before = im.size
    x0, y0, x1, y1 = entry["bbox"]
    gw, gh = x1 - x0, y1 - y0

    im = flatten_backdrop(im, entry.get("key", "light"))

    # Scale so the garment lands at a consistent size in every tile. Whichever
    # of the two limits binds first wins, so a wide hoodie and a small cap end
    # up looking like they were shot for the same grid.
    #
    # A garment wider than it is tall hits the width limit long before the
    # height one - the lookbook tees are 1.08:1 and stopped at 61% of tile
    # height against the hoodie's 76%, which read as a smaller product rather
    # than a wider one. fill_w lets those entries spend more of the width.
    scale = min(TILE_H * entry.get("fill_h", FILL_H) / gh,
                TILE_W * entry.get("fill_w", FILL_W) / gw)
    crop_w, crop_h = TILE_W / scale, TILE_H / scale

    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    left = round(cx - crop_w / 2)
    top = round(cy - crop_h * CENTRE_Y)

    # The crop can run off the source by a few dozen pixels. Paste onto a PLATE
    # canvas rather than clamping, so the garment stays centred and the added
    # margin is exactly the backdrop colour.
    canvas = Image.new("RGB", (round(crop_w), round(crop_h)), PLATE)
    canvas.paste(im, (-left, -top))
    tile = canvas.resize((TILE_W, TILE_H), Image.LANCZOS)
    tile.save(out, "WEBP", quality=QUALITY, method=6)

    print("  %-10s %-11s %5dKB  ->  %dx%d %3dKB   garment %d%% of height"
          % (entry["slug"], "%dx%d" % before, kb(src), TILE_W, TILE_H, kb(out),
             round(100 * gh * scale / TILE_H)))


def build_hero():
    src = os.path.join(SRC_DIR, HERO["src"])
    out = os.path.join(OUT_DIR, HERO["slug"] + ".webp")

    im = Image.open(src).convert("RGB")
    before = im.size
    im = im.crop(HERO["box"]).resize(HERO["out"], Image.LANCZOS)
    im.save(out, "WEBP", quality=HERO["quality"], method=6)

    print("  %-10s %-11s %5dKB  ->  %dx%d %3dKB   sign-free box %s"
          % (HERO["slug"], "%dx%d" % before, kb(src), HERO["out"][0],
             HERO["out"][1], kb(out), HERO["box"]))


# ------------------------------------------------------------------
def main():
    if "--probe" in sys.argv:
        for path in sys.argv[sys.argv.index("--probe") + 1:]:
            probe(path)
        return

    if not os.path.isdir(SRC_DIR):
        sys.exit("Source folder not found: " + SRC_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    for entry in MANIFEST + [HERO]:
        path = os.path.join(SRC_DIR, entry["src"])
        if not os.path.isfile(path):
            sys.exit("Missing source file: " + path)

    print("merch tiles -> %s" % OUT_DIR)
    for entry in MANIFEST:
        build_tile(entry)
    build_hero()
    print("\nDone. %d tiles + hero." % len(MANIFEST))


if __name__ == "__main__":
    main()
