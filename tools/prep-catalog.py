#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - catalogue prep (Nov 2026)
====================================================

Builds the apparel page assets from the label's "STERK OPAD CATALOG.pdf"
(Merch Products/Merch Updates/). Source file is never modified. Re-runnable.

Why render the PDF rather than extract its images
-------------------------------------------------

The tee page places ONE blank black tee and ONE blank white tee twice each,
and draws the SterkOpad mark on top as vector paths - so the extracted images
have no logo on them. Rendering the page region keeps the mark exactly where
the designer put it.

The floral backdrop (xref 54) sits behind every page. It is removed before
rendering so each garment comes out as a cut-out on transparent alpha, and the
page's CSS paints the same floral texture behind it - the garment floats on
the flowers exactly as it does in the catalogue, at any card size.

That backdrop is also exported on its own as catalog-floral.webp.

Usage:  python tools/prep-catalog.py
Needs:  pip install pymupdf Pillow
"""

import io
import os
import sys

try:
    import pymupdf
    from PIL import Image
except ImportError:
    sys.exit("Needs PyMuPDF and Pillow:  pip install pymupdf Pillow")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "Merch Products", "Merch Updates", "STERK OPAD CATALOG.pdf")
OUT_DIR = os.path.join(ROOT, "images", "merch")

FLORAL_XREF = 54

# (slug, page index, region in PDF points). Regions are the placed image
# rectangles from page.get_image_info(), which also contain the vector logo.
# Page 1 is tees, page 2 hoodies, page 3 track pants; left column is black,
# right column white; top row is the centre-chest print, bottom row left-chest.
GARMENTS = [
    ("tee-black-centre",    1, (192, 68, 656, 499)),
    ("tee-white-centre",    1, (1264, 68, 1728, 499)),
    ("tee-black-left",      1, (192, 581, 656, 1012)),
    ("tee-white-left",      1, (1264, 581, 1728, 1012)),
    ("hoodie-black-centre", 2, (212, 49, 637, 518)),
    ("hoodie-white-centre", 2, (1283, 49, 1708, 518)),
    ("hoodie-black-left",   2, (212, 562, 637, 1031)),
    ("hoodie-white-left",   2, (1283, 562, 1708, 1031)),
    ("trackpants-black",    3, (342, 221, 1920, 933)),
]

TILE_W, TILE_H = 560, 700    # 4:5, matches .merch-card__media
FILL = 0.84                  # garment's longer side as a fraction of the tile
ZOOM = 3                     # render scale - plenty of headroom over 560px
QUALITY = 84

FLORAL_W = 1600
FLORAL_QUALITY = 70


def kb(path):
    return os.path.getsize(path) // 1024


def render_cutout(page, rect):
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM),
                          clip=pymupdf.Rect(rect), alpha=True)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    # Crop to the garment itself - the placed images carry transparent margin
    # (the track pants most of all), which would otherwise shrink the garment.
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(box)


def build_tile(im, out):
    gw, gh = im.size
    scale = min(TILE_W * FILL / gw, TILE_H * FILL / gh)
    im = im.resize((round(gw * scale), round(gh * scale)), Image.LANCZOS)
    tile = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 0))
    tile.paste(im, ((TILE_W - im.width) // 2, round((TILE_H - im.height) * 0.46)))
    tile.save(out, "WEBP", quality=QUALITY, method=6)


def main():
    if not os.path.isfile(PDF):
        sys.exit("Catalogue not found: " + PDF)
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = pymupdf.open(PDF)

    # The backdrop first, before it is stripped from the pages. The image
    # itself is dark flowers; the pale look of the product pages comes from
    # the form it is drawn through (Fm0 under a GS0 graphics state), not from
    # the image. So -light is rendered: a scratch copy of the pants page with
    # its content cut down to that first block. -dark is the raw image, which
    # is what shows through the cover's brown panel - used for the hero.
    floral = pymupdf.Pixmap(doc, FLORAL_XREF)
    if floral.n - floral.alpha > 3:
        floral = pymupdf.Pixmap(pymupdf.csRGB, floral)
    dark = Image.open(io.BytesIO(floral.tobytes("png"))).convert("RGB")

    scratch = pymupdf.open()
    scratch.insert_pdf(doc, from_page=3, to_page=3)
    page = scratch[0]
    first, *rest = page.get_contents()
    scratch.update_stream(first, b"q /GS0 gs /Fm0 Do Q")
    for xref in rest:
        scratch.update_stream(xref, b"")
    zoom = FLORAL_W / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    light = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    for name, im in (("catalog-floral-light", light), ("catalog-floral-dark", dark)):
        im = im.resize((FLORAL_W, round(im.height * FLORAL_W / im.width)), Image.LANCZOS)
        out = os.path.join(OUT_DIR, name + ".webp")
        im.save(out, "WEBP", quality=FLORAL_QUALITY, method=6)
        print("  %-20s %dx%d %3dKB" % (name, im.width, im.height, kb(out)))

    # One delete is enough: the backdrop is a single shared XObject.
    doc[1].delete_image(FLORAL_XREF)

    for slug, page_no, rect in GARMENTS:
        out = os.path.join(OUT_DIR, slug + ".webp")
        build_tile(render_cutout(doc[page_no], rect), out)
        print("  %-20s %dx%d %3dKB" % (slug, TILE_W, TILE_H, kb(out)))

    print("\nDone. %d garments + floral backdrop -> %s" % (len(GARMENTS), OUT_DIR))


if __name__ == "__main__":
    main()
