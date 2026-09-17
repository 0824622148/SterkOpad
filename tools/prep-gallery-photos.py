#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - media page gallery prep
==================================================

Turns the label photo dump in "Gallery Images" into the WebP pairs the media
page grid uses. Source files are never modified. Re-runnable.

Each selected photo produces two files:

  NN-thumb.webp   square crop for the grid tile
  NN.webp         larger frame for the lightbox, aspect ratio left alone

That split is the whole point. The old media gallery pointed both the tile and
the lightbox at the same full-size JPEG, so the page pulled ~2.3MB of photos on
load to fill 400px squares. Here the grid costs only the thumbnails and a full
frame is fetched when somebody actually clicks one.

SELECTION
---------
The source folder holds 81 frames and 56 are used, chosen for spread as much as
quality — the raw set is heavily weighted to one performer on the mic at one
night event, and fifty of those in a row would read as a contact sheet rather
than a gallery. `sheet` is the frame's number in that original set, kept so a
choice can be traced back to the source file.

Dropped: near-duplicates from the same burst, frames too dark to read at
thumbnail size, two shots with a hand or head across the lens, and the "KEEZ"
title card, which is a video still with type on it rather than a photo.

Frames 76-81 are a later indoor sitting: one artist in a full branded hoodie
and joggers against a grey wall. All six are used. They are six frames of the
same pose and the same light, so they are the one place in the set where the
spread rule is stretched — worth watching if the gallery grows again.

The sort that produces `sheet` is alphabetical over the source filenames, and
the WhatsApp names carry the date, so a later drop lands after the existing
frames and the numbers above it stay put. A drop dated *earlier* than the ones
already here would renumber everything, and this list would have to be redone.

ORDER
-----
`order` is the grid position, and the list below is written in it. The branded
daylight shoot opens, then colour and monochrome alternate down the grid so the
night-event run is broken up rather than stacked.

The six frames of the indoor sitting go in at 7, 16, 25, 32, 41 and 48 for the
same reason. The gaps are deliberately uneven. `.gallery-grid` is

    repeat(auto-fill, minmax(280px, 1fr))

so the column count follows the viewport — anywhere from two on a phone to six
on a wide desktop — and a constant gap of ten would have put all six in one
column at five columns and again at two, i.e. a vertical stripe of the same
man down the grid. These six sit on different rows, and never in the same
column within three rows of each other, at every count from two to six.

Usage:  python tools/prep-gallery-photos.py
"""

import os
import sys

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "Gallery Images")
OUT_DIR = os.path.join(ROOT, "images", "gallery")

# role: (long edge, quality)
FULL  = (1400, 80)
THUMB = (600, 78)
HERO  = (2000, 80)

# The media page header also comes out of this set. It had been pointing at a
# 719x745 photo stretched across a banner declared 1920x800, which is the one
# genuinely low-quality image left on the page.
#
# .hero__bg img is object-fit: cover / object-position: center top, and the
# container swings from about 4.4:1 on a desktop to taller than it is wide on a
# phone. A frame with sky or backdrop across the top loses every face to that
# desktop crop, so the hero is cut to a banner here first, with `focus` placing
# the group high enough to survive it and central enough to survive the phone
# crop, which keeps full height and trims the sides.
HERO_FRAME = 16
HERO_CROP = 2.2
HERO_FOCUS = 0.60

# Square crops take a `focus` value — how far down the frame the subject sits,
# as a fraction of the height. Most of these are portrait frames with the face
# high up, so a plain centre crop would frame the chest and cut the head off.
# It does nothing on a landscape source, where the crop trims the sides.
DEFAULT_PORTRAIT_FOCUS = 0.28
DEFAULT_OTHER_FOCUS = 0.50

FOCUS = {
    4:  0.20,   # full body, head high in a tall 900x1600 frame
    30: 0.20,   # two faces, upper third
    37: 0.25,   # group, faces upper half
    43: 0.16,   # two standing figures, full body
    46: 0.20,   # duo sharing a mic
    56: 0.18,   # full body against the window
    61: 0.12,   # tight head shot, face already near the top
    67: 0.18,
    69: 0.15,   # arm raised, head high
    72: 0.15,   # full body
    73: 0.40,   # studio wide — hold the desk, not the ceiling
    74: 0.55,   # both lines of the Hela Hela print, with the cap still in

    # The indoor sitting. All six are 900x1600 with the subject filling the
    # frame, so the 900px square is cut high: enough air above the beanie to
    # keep the crown, low enough to clear the bottom of the chest print. On 77
    # those two do not both fit — the print ends at y=959 and the beanie starts
    # at y=57, a span of 902 in a 900 crop — so it runs tight at both edges.
    76: 0.14,
    77: 0.09,
    78: 0.04,
    79: 0.04,
    80: 0.06,
    81: 0.04,
}

# (order in the grid, frame number in the source set, alt text)
PHOTOS = [
    (1,  1,  "SterkOpad artist in a branded tee outside a Johannesburg house"),
    (2,  13, "SterkOpad artist in a branded hoodie against a stone wall"),
    (3,  11, "SterkOpad artists together at an outdoor event"),
    (4,  3,  "SterkOpad artist in a branded hoodie surrounded by greenery"),
    (5,  61, "Black and white portrait of a SterkOpad artist in a Nike cap"),
    (6,  15, "SterkOpad artists performing on stage"),
    (7,  76, "SterkOpad artist in a branded black hoodie and joggers indoors"),
    (8,  5,  "SterkOpad artist pointing to the logo on his hoodie"),
    (9,  74, "SterkOpad artist in a Hela Hela tee against a painted wall"),
    (10, 7,  "SterkOpad artist in a branded tee in a garden"),
    (11, 68, "Black and white group shot of the SterkOpad crew"),
    (12, 2,  "SterkOpad artist crouching beside a pool"),
    (13, 27, "Black and white shot of an artist on the mic at night"),
    (14, 63, "SterkOpad artists performing indoors with the crowd's hands up"),
    (15, 6,  "SterkOpad artist holding open a branded hoodie"),
    (16, 77, "SterkOpad artist in a branded hoodie against a grey studio wall"),
    (17, 25, "Black and white shot of an artist performing at a night event"),
    (18, 43, "Two SterkOpad artists outside a gated house"),
    (19, 8,  "SterkOpad artist in a branded white tee"),
    (20, 39, "An artist performing while a phone films him"),
    (21, 19, "Three SterkOpad artists on stage together"),
    (22, 31, "Black and white shot of an artist on the mic in a crowd"),
    (23, 9,  "SterkOpad artist in branded white tee and joggers"),
    (24, 58, "SterkOpad artists performing at an indoor session"),
    (25, 78, "SterkOpad artist in a full branded SterkOpad tracksuit"),
    (26, 10, "Black and white shot of an artist mid-verse"),
    (27, 4,  "SterkOpad artist with one finger raised outdoors"),
    (28, 71, "Black and white group shot of the crew outside"),
    (29, 26, "Black and white shot of an artist on the mic holding a cup"),
    (30, 67, "SterkOpad artist performing in a Nike hoodie"),
    (31, 33, "Two artists sharing the mic at a night event"),
    (32, 79, "SterkOpad artist in a branded hoodie with his hands clasped"),
    (33, 16, "SterkOpad artists performing under a stage canopy"),
    (34, 29, "Black and white shot of an artist in a bucket hat on the mic"),
    (35, 73, "An artist at the console in a recording studio"),
    (36, 21, "Wide shot of the SterkOpad crew on stage"),
    (37, 34, "Black and white shot of an artist performing in a Nike sweater"),
    (38, 30, "Two women in the crowd at a SterkOpad event"),
    (39, 46, "Two SterkOpad artists performing together at night"),
    (40, 12, "Black and white shot of an artist performing outdoors"),
    (41, 80, "SterkOpad artist smiling in a branded hoodie and Nike beanie"),
    (42, 65, "An indoor SterkOpad session filmed on a phone"),
    (43, 28, "Black and white shot of an artist in sunglasses on the mic"),
    (44, 72, "SterkOpad artist performing under green stage light"),
    (45, 23, "Close black and white shot of an artist on the mic"),
    (46, 69, "SterkOpad artist with his arm raised mid-performance"),
    (47, 32, "Black and white shot of an artist beside a car at night"),
    (48, 81, "Portrait of a SterkOpad artist in a branded hoodie and beanie"),
    (49, 18, "Two SterkOpad artists on stage at an outdoor show"),
    (50, 35, "Black and white shot of an artist in a bucket hat performing"),
    (51, 56, "SterkOpad artist outside a house in a white tee"),
    (52, 20, "Black and white shot of a performer facing the crowd"),
    (53, 70, "The SterkOpad crew at an indoor session"),
    (54, 24, "Two artists performing together under an umbrella at night"),
    (55, 62, "Wide shot of a SterkOpad indoor performance"),
    (56, 37, "Black and white shot of the crowd at a SterkOpad event"),
]


def kb(path):
    return max(1, os.path.getsize(path) // 1024)


def crop_ratio(im, ratio, focus):
    """Crop to an aspect ratio, keeping `focus` as the vertical centre."""
    w, h = im.size
    target_h = w / ratio

    if target_h <= h:                       # trim top and bottom
        top = int((h - target_h) * focus)
        return im.crop((0, top, w, int(top + target_h)))

    target_w = int(h * ratio)               # trim left and right
    left = (w - target_w) // 2
    return im.crop((left, 0, left + target_w, h))


def crop_square(im, focus):
    return crop_ratio(im, 1.0, focus)


def save(im, long_edge, quality, out_path):
    # Never upscale — contain will happily enlarge a small crop, which just
    # invents pixels and inflates the file for no gain.
    long_edge = min(long_edge, max(im.size))
    im = ImageOps.contain(im, (long_edge, long_edge), Image.LANCZOS)
    im.save(out_path, "WEBP", quality=quality, method=6)
    return im


def main():
    if not os.path.isdir(SRC_DIR):
        sys.exit("Source folder not found: " + SRC_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    # The source names are WhatsApp timestamps, so sorting them reproduces the
    # order the frames were reviewed in and `sheet` stays a stable reference.
    files = sorted(os.listdir(SRC_DIR))

    total = 0
    for order, sheet, _alt in PHOTOS:
        name = files[sheet - 1]
        im = ImageOps.exif_transpose(
            Image.open(os.path.join(SRC_DIR, name))).convert("RGB")

        focus = FOCUS.get(sheet, DEFAULT_PORTRAIT_FOCUS if im.height > im.width
                          else DEFAULT_OTHER_FOCUS)

        thumb_path = os.path.join(OUT_DIR, "%02d-thumb.webp" % order)
        full_path = os.path.join(OUT_DIR, "%02d.webp" % order)
        t = save(crop_square(im, focus), *THUMB, thumb_path)
        f = save(im, *FULL, full_path)
        total += os.path.getsize(thumb_path) + os.path.getsize(full_path)

        print("  %02d  frame %-2d  %4dx%-4d -> thumb %dx%d %sKB / full %dx%d %sKB"
              % (order, sheet, im.width, im.height, t.width, t.height,
                 kb(thumb_path), f.width, f.height, kb(full_path)))

    hero_src = ImageOps.exif_transpose(
        Image.open(os.path.join(SRC_DIR, files[HERO_FRAME - 1]))).convert("RGB")
    hero_path = os.path.join(OUT_DIR, "hero.webp")
    hero = save(crop_ratio(hero_src, HERO_CROP, HERO_FOCUS), *HERO, hero_path)
    print("\n  hero  frame %-2d  %4dx%-4d -> %dx%d %sKB"
          % (HERO_FRAME, hero_src.width, hero_src.height,
             hero.width, hero.height, kb(hero_path)))

    thumbs = sum(os.path.getsize(os.path.join(OUT_DIR, "%02d-thumb.webp" % o))
                 for o, _, _ in PHOTOS)
    print("\n%d photos" % len(PHOTOS))
    print("grid loads %.2fMB of thumbnails; %.2fMB on disk in total"
          % (thumbs / 1048576, total / 1048576))


if __name__ == "__main__":
    main()
