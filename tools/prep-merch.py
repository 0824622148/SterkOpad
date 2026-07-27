#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - merch photo prep
===========================================

Turns the raw product renders in "Merch Products/" into the WebP tiles the
apparel page uses. Source files are never modified. Re-runnable.

Why this is not just a resize
-----------------------------

The three garments are photographed on a pale studio sweep, and the sweep is
not the same in each file. Sampling the four corners:

  tee     179 186 195 206
  cap     177 254 204 254   <- white down the right edge, grey down the left
  hoodie  178 182 186 209

So the cards showed three different backdrops. On top of that the sources are
~2:3 portrait and the old CSS forced them into a square with object-fit
contain, which letterboxed roughly a third of every tile.

This script fixes both: it crops to the card's real 4:5, sizes each garment to
the same optical scale, and flattens every backdrop onto ONE colour, PLATE.
The CSS paints .merch-card__media the same value, so photo and tile become a
single continuous surface instead of a grey rectangle floating on a card.

Backdrop removal is a lightness key, not the border flood fill used by
prep-hero-art.py. That fill was tried here first and there is no tolerance
that works for all three - at tol=8 the tee keys cleanly at 44% kept while
the hoodie collapses to 5%. A lightness threshold suits these files because
the sweep is uniformly pale and every garment is black. It is the print on
the chest that needs care, not the garment: the logo is white, so the key is
applied only outside the garment's bounding box.

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
    {"slug": "tee-black", "src": "Black t.png", "bbox": (18, 72, 470, 616)},
    {"slug": "cap",       "src": "Cap.png",     "bbox": (36, 154, 456, 550)},
    {"slug": "hoodie",    "src": "Hoodie.png",  "bbox": (64, 80, 468, 580)},
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
    """Print the dark-pixel bounding box, to seed a new MANIFEST entry."""
    im = Image.open(path).convert("L")
    mask = im.point(lambda v: 255 if v < KEY_THRESHOLD else 0)
    box = mask.getbbox()
    print("%s  %dx%d  dark bbox = %s" % (os.path.basename(path),
                                         im.width, im.height, box))
    return box


def flatten_backdrop(rgb):
    """
    Return a copy with the backdrop replaced by PLATE.

    Breadth-first fill seeded from the border, walking only through pale
    pixels. Because it can reach nothing that the garment silhouette encloses,
    the white chest logo survives untouched while the sweep and the cast
    shadow around the garment are flattened.

    A plain "every pale pixel" threshold was tried first and is wrong: the
    garment bounding box is a rectangle, the garment is not, so the sweep
    survived in the box's corners and each tile showed a faint rectangle
    inside it - the very artefact this script exists to remove.
    """
    from collections import deque

    w, h = rgb.size
    grey = rgb.convert("L")
    gpx, px = grey.load(), rgb.load()

    seen = bytearray(w * h)
    q = deque()

    def seed(x, y):
        i = y * w + x
        if not seen[i] and gpx[x, y] >= KEY_THRESHOLD:
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

    im = flatten_backdrop(im)

    # Scale so the garment lands at a consistent size in every tile. Whichever
    # of the two limits binds first wins, so a wide hoodie and a small cap end
    # up looking like they were shot for the same grid.
    scale = min(TILE_H * FILL_H / gh, TILE_W * FILL_W / gw)
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
