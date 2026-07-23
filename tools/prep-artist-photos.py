#!/usr/bin/env python3
"""
STERK OPAD ENTERTAINMENT - artist photo prep
============================================

Turns a folder of raw artist photos into the sized, compressed WebP files the
artist profile pages use. Source files are never modified. Re-runnable.

Each photo can be emitted in several roles, and a photo may hold more than one:

  hero      full-bleed page header, left uncropped for the CSS
  portrait  the tall image beside the biography
  card      the 3:4 roster card on index.html and artists.html
  gallery   a square thumbnail plus a larger file for the lightbox

Square crops take a `focus` value - how far down the frame the subject sits, as
a fraction of the height. Photos here are shot portrait with the face high in
the frame, so a plain centre crop would take the chest and cut the head off.

Usage:  python tools/prep-artist-photos.py
"""

import os
import sys

try:
    from PIL import Image, ImageOps, ImageEnhance
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARTISTS = [
    {
        "slug": "eazy-ogee",
        "src_dir": "Eazy Ogee Images",
        "photos": [
            # file, gallery slot, extra roles, focus
            ("WhatsApp Image 2026-07-23 at 3.54.09 PM.jpeg",     1, ["hero"],     0.42),
            ("WhatsApp Image 2026-07-23 at 3.54.08 PM (1).jpeg", 2, ["card"],     0.30),
            ("WhatsApp Image 2026-07-23 at 3.54.07 PM.jpeg",     3, [],           0.38),
            ("WhatsApp Image 2026-07-23 at 3.54.08 PM.jpeg",     4, [],           0.45),
            ("WhatsApp Image 2026-07-23 at 3.54.08 PM (3).jpeg", 5, [],           0.40),
            ("WhatsApp Image 2026-07-23 at 3.54.08 PM (2).jpeg", 6, ["portrait"], 0.30),
        ],
    },
    {
        "slug": "larnie-ogee",
        "src_dir": "Larnie Ogee Images",
        # These are all 2:3 portraits, so the hero DOES need pre-cropping —
        # see the note by the hero role below.
        "hero_crop": 3 / 2,
        "hero_focus": 0.50,
        "photos": [
            ("WhatsApp Image 2026-07-23 at 4.13.33 PM (1).jpeg", 1, ["card"],     0.28),
            ("WhatsApp Image 2026-07-23 at 4.13.32 PM (2).jpeg", 2, [],           0.30),
            ("WhatsApp Image 2026-07-23 at 4.13.32 PM.jpeg",     3, ["portrait"], 0.30),
            ("WhatsApp Image 2026-07-23 at 4.13.33 PM.jpeg",     4, [],           0.25),
            ("WhatsApp Image 2026-07-23 at 4.13.32 PM (1).jpeg", 5, ["hero"],     0.40),
        ],
    },
    {
        "slug": "wazza-ogee",
        "src_dir": "Wazza Ogee Images",
        # The landscape frame used for the hero already suits the container,
        # so it needs no pre-crop — only the portraits would have.
        "photos": [
            ("WhatsApp Image 2026-07-23 at 4.30.17 PM (3).jpeg", 1, ["hero"],     0.30),
            ("WhatsApp Image 2026-07-23 at 4.30.17 PM.jpeg",     2, ["card"],     0.28),
            ("WhatsApp Image 2026-07-23 at 4.30.16 PM.jpeg",     3, ["portrait"], 0.28),
            ("WhatsApp Image 2026-07-23 at 4.30.17 PM (1).jpeg", 4, [],           0.32),
            ("WhatsApp Image 2026-07-23 at 4.30.17 PM (2).jpeg", 5, [],           0.35),
            ("WhatsApp Image 2026-07-23 at 4.30.16 PM (1).jpeg", 6, [],           0.35),
        ],
    },
    {
        "slug": "xanny-pxxl",
        "src_dir": "Xanny Pxxl",
        "hero_crop": 3 / 2,
        "hero_focus": 0.55,
        "photos": [
            ("ffff.jpeg",                                        1, ["hero"],     0.35),
            ("WhatsApp Image 2026-07-23 at 4.52.12 PM.jpeg",     2, ["card"],     0.12),
            ("WhatsApp Image 2026-07-23 at 4.52.13 PMxxc.jpeg",  3, ["portrait"], 0.50),
            ("WhatsApp Image 2026-07-23 at 4.52.13 PM.jpeg",     4, [],           0.10),
            # Highest-resolution frame in the set, but he is smoking in it —
            # gallery only, never a hero or roster card. See notes to client.
            ("WhatsApp Image 2026-07-23 at 4.52.13 PMd.jpeg",    5, [],           0.10),
        ],
    },
    {
        # In-house producer rather than a recording artist. Same asset shapes,
        # but "portrait" here is him at the desk — the shot that says producer.
        "slug": "fvrrow-otb",
        "src_dir": "Fvrrow Otb",
        # Casual phone/studio snaps — graded to sit with the darker heroes.
        "grade": True,
        "photos": [
            ("WhatsApp Image 2026-07-23 at 4.56.23 PMd.jpeg", 1, ["hero"],     0.30),
            ("WhatsApp Image 2026-07-23 at 4.56.23 PMf.jpeg", 2, ["portrait"], 0.30),
            ("WhatsApp Image 2026-07-23 at 4.56.24 PMd.jpeg", 3, ["card"],     0.22),
            ("WhatsApp Image 2026-07-23 at 4.56.24 PM.jpeg",  4, [],           0.28),
            ("WhatsApp Image 2026-07-23 at 4.56.24 PMf.jpeg", 5, [],           0.26),
        ],
    },
]

# role: (long edge, quality)
HERO     = (2000, 78)
PORTRAIT = (900, 82)
CARD     = (800, 82)
GALLERY  = (1400, 82)
THUMB    = (600, 80)

CARD_RATIO = 3 / 4       # roster card, width / height


def kb(path):
    return max(1, os.path.getsize(path) // 1024)


def apply_grade(im):
    """
    A subtle cinematic grade + vignette overlay, for casual phone photos that
    read as flat and low-quality next to the site's moody heroes.

    Three gentle moves, none heavy enough to look filtered:
      - a mild contrast S-curve, so the flat midtones get some depth;
      - a touch less saturation, which tames a loud warm/orange cast;
      - a soft dark vignette overlay that adds depth and steers the eye to the
        subject — and, on the hero, keeps the bright edges from washing out
        the red eyebrow and white title sitting over them.

    Baked into the pixels on purpose: the request was to enhance the image,
    and this then travels with the photo wherever it is reused (hero, the
    services studio panel, the gallery).
    """
    im = ImageEnhance.Contrast(im).enhance(1.12)
    im = ImageEnhance.Color(im).enhance(0.88)
    im = ImageEnhance.Brightness(im).enhance(0.97)

    w, h = im.size
    # radial_gradient is black at centre, white at the edges — exactly a
    # vignette mask. Scaled to 0.30 so corners darken ~30%, centre untouched.
    vignette = Image.radial_gradient("L").resize((w, h)).point(
        lambda p: int(p * 0.30)
    )
    darkness = Image.new("RGB", (w, h), (8, 8, 10))
    return Image.composite(darkness, im, vignette)


def crop_ratio(im, ratio, focus=0.5):
    """Crop to an aspect ratio, keeping `focus` as the vertical centre."""
    w, h = im.size
    target_h = w / ratio

    if target_h <= h:                      # trim top and bottom
        top = int((h - target_h) * focus)
        return im.crop((0, top, w, int(top + target_h)))

    target_w = int(h * ratio)              # trim left and right
    left = (w - target_w) // 2
    return im.crop((left, 0, left + target_w, h))


def save(im, long_edge, quality, out_path):
    # Never upscale — ImageOps.contain will happily enlarge a small crop,
    # which just invents pixels and inflates the file for no gain.
    long_edge = min(long_edge, max(im.size))
    im = ImageOps.contain(im, (long_edge, long_edge), Image.LANCZOS)
    im.save(out_path, "WEBP", quality=quality, method=6)
    print("    %-34s %4dx%-4d %sKB" % (
        os.path.basename(out_path), im.width, im.height, kb(out_path)))


def main():
    for artist in ARTISTS:
        src_dir = os.path.join(ROOT, artist["src_dir"])
        out_dir = os.path.join(ROOT, "images", artist["slug"])

        if not os.path.isdir(src_dir):
            sys.exit("Source folder not found: " + src_dir)
        os.makedirs(out_dir, exist_ok=True)

        print(artist["slug"])
        for filename, slot, roles, focus in artist["photos"]:
            path = os.path.join(src_dir, filename)
            if not os.path.isfile(path):
                sys.exit("Missing photo: " + path)

            # Honour any EXIF rotation before measuring or cropping
            im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            if artist.get("grade"):
                im = apply_grade(im)
            print("  %s  (%dx%d)" % (filename, im.width, im.height))

            # Gallery: square thumbnail for the grid, larger file for lightbox
            sq = crop_ratio(im, 1.0, focus)
            save(sq, *THUMB, os.path.join(out_dir, "gallery-%d-thumb.webp" % slot))
            save(im, *GALLERY, os.path.join(out_dir, "gallery-%d.webp" % slot))

            # .hero__bg img is object-fit: cover / object-position: center top,
            # so the browser reframes the hero per viewport and a square source
            # needs no crop from us — it shows the top ~44%, which is the face.
            #
            # A 2:3 portrait is a different story: the same container shows only
            # the top ~30%, which lands on forehead and background. Those need
            # `hero_crop` to bring the frame closer to landscape first, with
            # `hero_focus` placing the face inside what the browser keeps.
            if "hero" in roles:
                hero_im = im
                if artist.get("hero_crop"):
                    hero_im = crop_ratio(im, artist["hero_crop"],
                                         artist.get("hero_focus", focus))
                save(hero_im, *HERO, os.path.join(out_dir, "hero.webp"))
            if "portrait" in roles:
                save(crop_ratio(im, CARD_RATIO, focus), *PORTRAIT,
                     os.path.join(out_dir, "portrait.webp"))
            if "card" in roles:
                save(crop_ratio(im, CARD_RATIO, focus), *CARD,
                     os.path.join(out_dir, "card.webp"))

        print()


if __name__ == "__main__":
    main()
