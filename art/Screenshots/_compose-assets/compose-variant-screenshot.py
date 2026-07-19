#!/usr/bin/env python3
"""
Compose a README promo screenshot (TangerineUI-<variant>.png) for a new
color variant, reusing the original template's browser chrome, rounded
corners, drop shadow, and phone frame.

Usage:
    python3 compose-variant-screenshot.py <variant> \
        --light path/to/<variant>-light.png \
        --dark path/to/<variant>-dark.png \
        --iphone path/to/<variant>-iphone.png \
        --out path/to/TangerineUI-<variant>.png

Requires: pip install Pillow
(aggdraw/psd-tools are NOT needed here - those were only needed once, to
extract the *-template.png assets in this folder from the original PSD.
That extraction does not need to be repeated.)

Input screenshot requirements (see README-recipe.md in this folder):
  <variant>-light.png : 3250x2784 (or close), Mastodon light mode, plain
                         page content only — no browser chrome needed, that
                         part is reused from the template.
  <variant>-dark.png   : same size, dark mode.
  <variant>-iphone.png : app content only (no status bar / home indicator —
                         those are baked into phone-frame-template2.png as
                         realistic static chrome). Capture via Chrome
                         DevTools custom device: 359x706 viewport, DPR=2
                         (renders at exactly 718x1412, the content hole's
                         native size, no rescaling needed).
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

SHADOW_STRENGTH = 0.45  # scales down the base canvas's own alpha (the drop
                         # shadow); the shadow is legitimate/present in the
                         # original assets too, but reads harsher against a
                         # light UI background than it did against the
                         # original's custom warm promo-page color.

ASSETS = Path(__file__).parent

CHROME_H_LIGHT = 168
CHROME_H_DARK = 170

LIGHT_SIZE = (3232, 2776)
DARK_SIZE = (3250, 2784)
LIGHT_OFFSET = (218, 173)
DARK_OFFSET = (209, 169)

# phone-frame-template2.png: a clean iPhone frame with a REALISTIC static
# status bar (09:41, Dynamic Island, signal/wifi/battery) and home indicator
# already baked in as opaque chrome — only the actual app-content area is a
# transparent hole. This is why the OLD phone-frame-template.png (from the
# original PSD's Mobile layer, which was itself a real screenshot inside a
# frame) produced screenshots that looked like they were missing a status
# bar/home indicator: our own raw captures never had one either (they're
# plain Chrome DevTools viewport captures, not real on-device screenshots),
# so pasting them into the OLD frame's inner box (which spanned status bar
# to home indicator) just showed blank app chrome where the status bar
# should be. Content hole measured as a PLAIN RECTANGLE, no rounded corners
# (confirmed by rendering the alpha channel as black/white and zooming the
# corner — the transition is a crisp right angle).
PHONE_INNER_BOX = (76, 168, 794, 1580)  # x0,y0,x1,y1 within the 869x1698 frame
PHONE_OFFSET = (2641, 1255)

# Crop off the outer shadow-blur margin to match the published assets
# (verified against TangerineUI-tangerine.png: 3568x3018, no visible shadow).
FINAL_CROP_MARGIN_LEFT = 50
FINAL_CROP_MARGIN_TOP = 51
FINAL_WIDTH = 3568
FINAL_HEIGHT = 3018


def build_masked_layer(template_path, new_content_path, chrome_h, target_size):
    """Take the ORIGINAL template layer (has real chrome + correct rounded/
    diagonal alpha shape baked in), keep its chrome strip + alpha shape,
    but replace the page content below the chrome with new_content_path."""
    orig = Image.open(template_path).convert("RGBA")
    assert orig.size == target_size, f"{template_path}: {orig.size} != {target_size}"
    alpha = orig.split()[-1]

    chrome = orig.crop((0, 0, target_size[0], chrome_h))

    new_content = Image.open(new_content_path).convert("RGBA")
    content_h = target_size[1] - chrome_h
    new_content = new_content.resize((target_size[0], content_h), Image.LANCZOS)

    combined = Image.new("RGBA", target_size, (255, 255, 255, 255))
    combined.paste(chrome, (0, 0))
    combined.paste(new_content, (0, chrome_h))
    combined.putalpha(alpha)
    return combined


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=255)
    return mask


def tint_bg_color(accent_hex, mix=0.20):
    """Light tint of the accent color, ~mix accent / (1-mix) white — same
    recipe as the original promo image's warm peach page background (derived
    from Tangerine's orange accent, measured at roughly 20% accent / 80%
    white)."""
    r = int(accent_hex[0:2], 16)
    g = int(accent_hex[2:4], 16)
    b = int(accent_hex[4:6], 16)
    return tuple(round(c * mix + 255 * (1 - mix)) for c in (r, g, b)) + (255,)


def build(light_path, dark_path, phone_path, out_path, accent_hex):
    """phone_path may be None — e.g. the advanced-UI feature screenshot
    uses the same diagonal light/dark composite but has no phone layer."""
    base_size = Image.open(ASSETS / "base-canvas.png").size
    bg_color = tint_bg_color(accent_hex)

    dark_combined = build_masked_layer(
        ASSETS / "chrome-dark-template.png", dark_path, CHROME_H_DARK, DARK_SIZE
    )
    light_combined = build_masked_layer(
        ASSETS / "chrome-light-template.png", light_path, CHROME_H_LIGHT, LIGHT_SIZE
    )

    if phone_path is not None:
        # Base canvas carries the baked window+phone drop shadow.
        canvas = Image.open(ASSETS / "base-canvas.png").convert("RGBA")
        # Weaken the drop shadow — it's legitimate/present in the original
        # assets too, but reads harsher on our real-UI light background than
        # it did against the original's custom warm promo-page color.
        r, g, b, a = canvas.split()
        a = a.point(lambda v: round(v * SHADOW_STRENGTH))
        canvas = Image.merge("RGBA", (r, g, b, a))
        colored_bg = Image.new("RGBA", base_size, bg_color)
        colored_bg.alpha_composite(canvas)
        canvas = colored_bg
    else:
        # No phone layer to cover the phone-shaped part of the baked shadow,
        # so skip the base canvas entirely and synthesize a window-only
        # shadow from the actual window alpha instead.
        canvas = Image.new("RGBA", base_size, bg_color)
        window_mask = Image.new("L", base_size, 0)
        window_mask.paste(dark_combined.split()[-1], DARK_OFFSET)
        light_alpha = light_combined.split()[-1]
        placed_light = Image.new("L", base_size, 0)
        placed_light.paste(light_alpha, LIGHT_OFFSET)
        window_mask = Image.composite(
            Image.new("L", base_size, 255), window_mask,
            placed_light.point(lambda v: 255 if v > 8 else 0))
        window_mask = window_mask.point(lambda v: 255 if v > 8 else 0)
        shadow = Image.new("RGBA", base_size, (0, 0, 0, 0))
        black = Image.new("RGBA", base_size, (0, 0, 0, round(160 * SHADOW_STRENGTH)))
        shadow.paste(black, (0, 22), window_mask)
        shadow = shadow.filter(ImageFilter.GaussianBlur(40))
        canvas.alpha_composite(shadow)

    canvas.alpha_composite(dark_combined, dest=DARK_OFFSET)
    canvas.alpha_composite(light_combined, dest=LIGHT_OFFSET)

    if phone_path is not None:
        phone_frame = Image.open(ASSETS / "phone-frame-template2.png").convert("RGBA")
        phone_shot = Image.open(phone_path).convert("RGBA")
        x0, y0, x1, y1 = PHONE_INNER_BOX
        inner_w, inner_h = x1 - x0, y1 - y0

        if phone_shot.size != (inner_w, inner_h):
            scale = inner_w / phone_shot.width
            new_h = round(phone_shot.height * scale)
            resized = phone_shot.resize((inner_w, new_h), Image.LANCZOS)
            if new_h > inner_h:
                top_crop = (new_h - inner_h) // 2
                resized = resized.crop((0, top_crop, inner_w, top_crop + inner_h))
            elif new_h < inner_h:
                pad = Image.new("RGBA", (inner_w, inner_h), (0, 0, 0, 255))
                pad.paste(resized, (0, (inner_h - new_h) // 2))
                resized = pad
        else:
            resized = phone_shot

        phone_composite = phone_frame.copy()
        phone_composite.alpha_composite(resized, dest=(x0, y0))
        # Re-apply the frame on top: the content hole is a plain rectangle,
        # but the frame's own bezel art rounds off the visible screen
        # corners by overlapping slightly into the hole. That overlap gets
        # covered by the opaque screenshot paste above, exposing square
        # corners — redrawing the frame here restores it via the frame's
        # own alpha, leaving the true (transparent) screen area untouched.
        phone_composite.alpha_composite(phone_frame, dest=(0, 0))
        canvas.alpha_composite(phone_composite, dest=PHONE_OFFSET)

    # The base canvas carries a ~50px outer margin (the shape's drop-shadow
    # blur bleed allowance from the PSD). The existing published screenshots
    # (e.g. TangerineUI-tangerine.png, 3568x3018) are cropped to exclude it
    # entirely -- no shadow is visible in the real assets, window/phone sit
    # directly on the promo page background with a crisp edge. Match that.
    canvas = canvas.crop((FINAL_CROP_MARGIN_LEFT, FINAL_CROP_MARGIN_TOP,
                          FINAL_CROP_MARGIN_LEFT + FINAL_WIDTH,
                          FINAL_CROP_MARGIN_TOP + FINAL_HEIGHT))

    canvas.save(out_path)
    print(f"Saved {out_path} size={canvas.size}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("variant", help="variant name, just for messages")
    p.add_argument("--light", required=True)
    p.add_argument("--dark", required=True)
    p.add_argument("--iphone", default=None,
                   help="optional; omit for a phone-less composite (e.g. the advanced-UI feature image)")
    p.add_argument("--out", required=True)
    p.add_argument("--accent", required=True, help="variant's light-mode accent color, hex without #, e.g. 32863a")
    args = p.parse_args()
    build(args.light, args.dark, args.iphone, args.out, args.accent)
