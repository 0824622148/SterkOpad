#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - hero asset prep
==========================================

One-time (re-runnable) build step for the homepage release carousel.

Reads the supplied artwork from "Hero Section background Images/" and writes
web-ready files into "images/hero/". Source files are never modified.

For each release we produce two assets:

  <slug>-bg.webp    the widescreen banner, resized to 1920px wide. It is
                    blurred and darkened to 45% brightness in CSS, so heavy
                    compression is invisible. Releases that shipped without a
                    banner omit "bg" in the manifest; for those the backdrop
                    is enlarged from the sleeve itself, which at 14px of blur
                    reads as a colour wash drawn from the artwork.

  <slug>-art.webp   the vinyl-sleeve mockup with its baked-in backdrop
                    removed, so it floats over the hero.

Removal is a flood fill seeded from the border, so it can only ever eat a
region connected to the edge of the frame - it cannot punch holes inside the
artwork. Crucially it compares each candidate pixel against *the pixel the
fill is arriving from*, not against a fixed backdrop colour. A smooth gradient
is a chain of tiny steps, so the fill walks straight through it; the hard edge
of the sleeve is one large step that stops it dead.

That matters because three of these mockups sit on flat white/cream and two on
a vignette fading from black up to a glow behind the sleeve - and all five cast
a soft drop shadow. A fixed-colour key handles the flat backdrops but leaves
both the vignettes and the shadows behind. This one handles all three.

Not every release arrives as a mockup. Where the label supplies the finished
square cover instead, mark it "flat" in the manifest: there is no backdrop to
remove, and keying it would be actively wrong - a full-bleed cover reaches the
border, so the fill would eat the artwork itself rather than a backdrop. Flat
entries are resized and used as-is.

Usage:  python tools/prep-hero-art.py
"""

import os
import sys
from collections import deque

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")


# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "Hero Section background Images")
OUT_DIR = os.path.join(ROOT, "images", "hero")
COVER_DIR = os.path.join(ROOT, "images", "releases")


# ------------------------------------------------------------------
# Manifest — tune tolerances here, not in the logic below
# ------------------------------------------------------------------
# tol   The per-step colour delta the fill may cross. Keep it small. Raising
#       it lets the fill hop the sleeve edge and devour the artwork: at 7 the
#       "1 Two 8" sleeve - a smooth purple sky - collapsed from 51% kept to
#       15%. That sleeve is no longer keyed (see below), but it is what the
#       value was tuned against, and every entry still keyed verified clean
#       at 4.
MANIFEST = [
    {
        "slug": "cadillac",
        "bg":   "Cadillac.png",
        "art":  "Cadillac Cover.png",
        "tol":  4,
    },
    {
        "slug": "2001",
        "bg":   "2001.png",
        "art":  "2001 Cover.png",
        "tol":  4,
    },
    {
        "slug": "secret-location",
        "bg":   "Secret Location Larnie Ogee.png",
        "art":  "Secret location Cover.png",
        "tol":  4,
    },
    # The sleeve mockup this shipped with had the advisory sticker misspelled
    # three ways ("PARENIAL ADVISTRY EXPLICIT COMPENT"), so it is now the
    # label's clean square cover. The widescreen banner is unaffected and
    # still supplies the backdrop.
    {
        "slug": "1-two-8",
        "bg":   "Eazy Ogee Wazza Ogee Larnie Ogee 1 Two 8.png",
        "art":  "Eazy OGee (feat. Wazza OGee,Geez SA & Larnie OGee) - 1Two8 Cover.jpeg",
        "flat": True,
    },
    {
        "slug": "kroon-kyk",
        "bg":   "Kroon Kyk en Mooi Lyk.png",
        "art":  "Kroon Kyk en Mooi Lyk Cover.png",
        "tol":  4,
    },
    # No banner was supplied for these four — the backdrop comes off the sleeve.
    {
        "slug": "smokin-n-drinkin",
        "art":  "Eazy OGee & Wazza OGee - Smokin N Drinkin cover.png",
        "tol":  4,
    },
    {
        "slug": "aan-die-brand",
        "art":  "Larnie OGee (feat. C-P4YNE) - Aan die brand Cover.png",
        "tol":  4,
    },
    {
        "slug": "dope-scale",
        "art":  "Eazy OGee & Wazza OGee - Dope Scale (feat. Mac D) Cover.png",
        "tol":  4,
    },
    {
        "slug": "long-road",
        "art":  "Xanny Pxxl - Long Road (Produced by. Shawn Brooklyn) Cover.png",
        "tol":  4,
    },
    # Supplied as the finished square cover rather than a sleeve mockup, so
    # there is nothing to key off it — see "flat" in build_art().
    {
        "slug": "main-ou",
        "art":  "Larnie OGee - Main Ou Cover.jpeg",
        "flat": True,
    },
]

BG_ASPECT = 16 / 9

BG_WIDTH = 1920
BG_QUALITY = 70
ART_MAX = 1100
ART_QUALITY = 88

# Artwork is keyed at its final size. The tolerances above are tuned for it -
# at a different resolution the gradient steps change and "grad" mode drifts.


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def kb(path):
    return os.path.getsize(path) // 1024


def sample_backdrop(px, w, h):
    """Average the four corner pixels to get the backdrop colour."""
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    return tuple(sum(c[i] for c in corners) // 4 for i in range(3))


def flood_alpha(im, bg, tol):
    """
    Return an 'L' mask where 255 = keep, 0 = backdrop.

    Breadth-first flood seeded from the border, so only a region connected to
    the edge of the frame can be removed. Border pixels are seeded against the
    sampled backdrop colour; from there each candidate is measured against the
    pixel the fill is spreading from, so it follows a gradient but not an edge.
    """
    w, h = im.size
    px = im.load()
    tol_sq = tol * tol * 3

    keep = bytearray(b"\xff" * (w * h))
    seen = bytearray(w * h)
    q = deque()

    def close(a, b):
        dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
        return dr * dr + dg * dg + db * db <= tol_sq

    def seed(x, y, ref):
        i = y * w + x
        if not seen[i] and close(px[x, y], ref):
            seen[i] = 1
            keep[i] = 0
            q.append((x, y))

    for x in range(w):
        seed(x, 0, bg)
        seed(x, h - 1, bg)
    for y in range(h):
        seed(0, y, bg)
        seed(w - 1, y, bg)

    while q:
        x, y = q.popleft()
        ref = px[x, y]
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                seed(nx, ny, ref)

    return Image.frombytes("L", (w, h), bytes(keep))


def fit(im, max_dim):
    w, h = im.size
    if max(w, h) <= max_dim:
        return im
    scale = max_dim / max(w, h)
    return im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


# ------------------------------------------------------------------
# Per-asset builders
# ------------------------------------------------------------------
def build_bg(entry):
    src = os.path.join(SRC_DIR, entry["bg"])
    out = os.path.join(OUT_DIR, entry["slug"] + "-bg.webp")

    im = Image.open(src).convert("RGB")
    before = im.size
    if im.width > BG_WIDTH:
        im = im.resize(
            (BG_WIDTH, round(im.height * BG_WIDTH / im.width)), Image.LANCZOS
        )
    im.save(out, "WEBP", quality=BG_QUALITY, method=6)

    print(
        "  bg   {0[0]}x{0[1]} {1}KB  ->  {2[0]}x{2[1]} {3}KB".format(
            before, kb(src), im.size, kb(out)
        )
    )


def build_art(entry):
    src = os.path.join(SRC_DIR, entry["art"])
    out = os.path.join(OUT_DIR, entry["slug"] + "-art.webp")

    original = Image.open(src)
    before = original.size

    # A finished cover is already the artwork — resize and stop. The alpha is
    # opaque throughout, purely so the cover and backdrop builders below can
    # treat every entry the same way.
    if entry.get("flat"):
        im = fit(original.convert("RGB"), ART_MAX).convert("RGBA")
        im.save(out, "WEBP", quality=ART_QUALITY, method=6)
        print(
            "  art  {0[0]}x{0[1]} {1}KB  ->  {2[0]}x{2[1]} {3}KB   flat".format(
                before, kb(src), im.size, kb(out)
            )
        )
        return build_cover(entry, im)

    # Key at the final size, which is what the tolerances are tuned against.
    rgb = fit(original.convert("RGB"), ART_MAX)
    bg = sample_backdrop(rgb.load(), *rgb.size)

    alpha = flood_alpha(rgb, bg, entry["tol"])
    # Soften the cut so the edge does not read as a hard cardboard stamp.
    alpha = alpha.filter(ImageFilter.GaussianBlur(1))

    im = rgb.convert("RGBA")
    im.putalpha(alpha)

    box = alpha.getbbox()
    if box:
        pad_x = round(rgb.width * 0.02)
        pad_y = round(rgb.height * 0.02)
        im = im.crop(
            (
                max(0, box[0] - pad_x),
                max(0, box[1] - pad_y),
                min(rgb.width, box[2] + pad_x),
                min(rgb.height, box[3] + pad_y),
            )
        )

    im.save(out, "WEBP", quality=ART_QUALITY, method=6)

    kept = round(100 * sum(alpha.tobytes()) / (255 * alpha.width * alpha.height))
    print(
        "  art  {0[0]}x{0[1]} {1}KB  ->  {2[0]}x{2[1]} {3}KB   "
        "tol={4} bg={5} kept={6}%".format(
            before, kb(src), im.size, kb(out), entry["tol"], bg, kept
        )
    )

    return build_cover(entry, im)


def build_cover(entry, art):
    """
    Square sleeve crop, for use as a flat release cover.

    In every mockup the sleeve sits flush left with the vinyl peeking out to
    its right, and the sleeve is square — so the leftmost square of the keyed
    artwork is the cover. Release cards are `aspect-ratio: 1` with
    `object-fit: cover`, which would otherwise crop the wide mockup down the
    middle and slice the sleeve in half.
    """
    os.makedirs(COVER_DIR, exist_ok=True)
    out = os.path.join(COVER_DIR, entry["slug"] + ".webp")

    side = min(art.height, art.width)
    cover = art.crop((0, 0, side, side))
    cover.save(out, "WEBP", quality=ART_QUALITY, method=6)

    print("  cover                      ->  {0[0]}x{0[1]} {1}KB".format(
        cover.size, kb(out)))

    return cover


def build_bg_from_cover(entry, cover):
    """
    Stand-in banner for a release that shipped without one.

    Blows the square sleeve up to 1920 wide and takes the centre band. The
    result is far too soft to read as a photograph at 1:1, but the hero blurs
    it by 14px and drops it to 45% brightness, so all that survives is a
    colour field — and taking it from the sleeve keeps that field on-palette.
    """
    out = os.path.join(OUT_DIR, entry["slug"] + "-bg.webp")

    im = Image.new("RGB", cover.size, (10, 10, 10))
    im.paste(cover, (0, 0), cover)

    height = round(BG_WIDTH / BG_ASPECT)
    im = im.resize((BG_WIDTH, BG_WIDTH), Image.LANCZOS)
    top = (BG_WIDTH - height) // 2
    im = im.crop((0, top, BG_WIDTH, top + height))

    im.save(out, "WEBP", quality=BG_QUALITY, method=6)

    print("  bg   from sleeve           ->  {0[0]}x{0[1]} {1}KB".format(
        im.size, kb(out)))


# ------------------------------------------------------------------
def main():
    if not os.path.isdir(SRC_DIR):
        sys.exit("Source folder not found: " + SRC_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    for entry in MANIFEST:
        for key in ("bg", "art"):
            if key not in entry:
                continue
            path = os.path.join(SRC_DIR, entry[key])
            if not os.path.isfile(path):
                sys.exit("Missing source file: " + path)

        print(entry["slug"])
        if "bg" in entry:
            build_bg(entry)
            build_art(entry)
        else:
            build_bg_from_cover(entry, build_art(entry))
        print()

    print("Done. {0} releases -> {1}".format(len(MANIFEST), OUT_DIR))


if __name__ == "__main__":
    main()
