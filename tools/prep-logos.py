#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - logo prep
====================================

Builds the site's logo files from the official artwork in "Official Logo/".
Source files are never modified. Re-runnable.

Source choice
-------------
The folder has the full lockup at two sizes. The 1563x1563 pair is sharper
but BOTH are cropped - the leg of the K and the bowl of the D are sliced flat
at the right edge of the frame. The 500x500 pair is the same lockup with
correct margins on all four sides, so that is what we build from.

That leaves 241x179 of actual artwork, which is still 3.7x the 48px the logo
is ever displayed at, so it covers 3x retina with room to spare. If a properly
exported high-resolution lockup turns up later, drop it in and point SOURCE at
it - nothing else needs to change.

Transparency
------------
The official files are JPEGs on a solid background, so the logo needs cutting
out. The artwork is flat black on flat white, which means luminance IS the
mask: alpha = 255 - luminance gives a perfectly antialiased edge for free.
A levels clamp either side kills the JPEG mush in the flat areas without
touching the antialiasing in between.

One mask then gets colourised twice, so the white and black logos are
guaranteed to be the same shape to the pixel.

Usage:  python tools/prep-logos.py
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Official Logo",
                   "WhatsApp Image 2026-07-23 at 3.19.29 PM (1).jpeg")
OUT_DIR = os.path.join(ROOT, "images")

# Below LO is background, above HI is solid artwork, between the two the
# antialiasing is kept as-is.
LO, HI = 10, 245

WHITE = (255, 255, 255)
BLACK = (10, 10, 10)          # --black, so it matches the design tokens


def kb(path):
    return max(1, os.path.getsize(path) // 1024)


def build_mask(path):
    """Alpha mask of the artwork: opaque where the logo is, clear elsewhere."""
    lum = Image.open(path).convert("L")

    span = float(HI - LO)
    alpha = lum.point(
        lambda p: max(0, min(255, int(255.0 * ((255 - p) - LO) / span)))
    )

    box = alpha.getbbox()
    return alpha.crop(box) if box else alpha


def colourise(mask, rgb):
    """Flat colour carrying the mask as its alpha channel."""
    out = Image.new("RGBA", mask.size, rgb + (0,))
    out.putalpha(mask)
    return out


def save(im, name):
    path = os.path.join(OUT_DIR, name)
    im.save(path, "PNG", optimize=True)
    print("  %-22s %4dx%-4d  %sKB" % (name, im.width, im.height, kb(path)))
    return path


def square(im, size, bg):
    """Centre the logo on a square canvas. Pass (0, 0, 0, 0) for no backdrop."""
    canvas = Image.new("RGBA", (size, size), bg)
    fitted = im.copy()
    fitted.thumbnail((int(size * 0.82), int(size * 0.82)), Image.LANCZOS)
    canvas.paste(
        fitted,
        ((size - fitted.width) // 2, (size - fitted.height) // 2),
        fitted,
    )
    return canvas


def main():
    if not os.path.isfile(SRC):
        sys.exit("Source logo not found: " + SRC)

    mask = build_mask(SRC)
    print("artwork %dx%d  (ratio %.3f)\n" % (
        mask.width, mask.height, mask.width / mask.height))

    white = colourise(mask, WHITE)
    black = colourise(mask, BLACK)

    save(white, "logo.png")        # nav + footer, on the dark theme
    save(black, "logo-dark.png")   # for light backgrounds

    # Tab favicon keeps a solid white backdrop: browser tab strips are usually
    # light, and a black mark on transparency would vanish against a light one.
    save(square(black, 32, WHITE + (255,)), "favicon-32.png")

    # Home-screen icon is transparent by request. Note that iOS does not honour
    # alpha here — it flattens the icon onto black when added to a home screen.
    # The artwork is white precisely so it still reads when that happens.
    save(square(white, 180, (0, 0, 0, 0)), "apple-touch-icon.png")

    print("\nDisplay sizes for the HTML width/height attributes:")
    for h in (44, 48):
        print("  height %d  ->  width %d" % (h, round(h * mask.width / mask.height)))


if __name__ == "__main__":
    main()
