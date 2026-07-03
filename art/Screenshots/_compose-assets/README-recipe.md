# How to add a README promo screenshot for a new color variant

1. Deploy the new variant's CSS to a live Mastodon instance. Use English
   locale content for the captures (the published screenshots are in
   English, unlike earlier working drafts).
2. Capture 3 screenshots at the live instance, via Chrome DevTools:
   - Open DevTools, toggle Device Toolbar (Cmd+Shift+M), set a **custom**
     viewport size + DPR, then Cmd+Shift+P -> **"Capture screenshot"** (NOT
     "Capture full size screenshot" - that scrolls through Mastodon's
     infinite feed and produces a huge broken image).
   - `<variant>-light.png`: viewport **1625x1392, DPR 2** (renders at
     3250x2784) — light mode.
   - `<variant>-dark.png`: same size — dark mode.
   - `<variant>-iphone.png`: viewport **359x706, DPR 2** (renders at
     718x1412 — the exact size of the phone frame's content hole, no
     rescaling needed). This should be **app content only** — no status
     bar, no home indicator. Those are already baked into
     `phone-frame-template2.png` as realistic static chrome (09:41,
     Dynamic Island, signal/wifi/battery, home indicator bar). A plain
     DevTools capture never includes real device chrome anyway, so this
     just works — don't try to crop a real on-device screenshot instead,
     it would show a second status bar on top of the frame's own one.
3. Run:
   ```
   python3 art/Screenshots/_compose-assets/compose-variant-screenshot.py <variant> \
     --light art/Screenshots/<variant>-light.png \
     --dark art/Screenshots/<variant>-dark.png \
     --iphone art/Screenshots/<variant>-iphone.png \
     --accent <hex> \
     --out art/Screenshots/TangerineUI-<variant>.png
   ```
   `--accent` is the variant's light-mode accent color (hex, no `#`) —
   used to tint the promo page background, same recipe as the original's
   warm peach backdrop (measured ~20% accent / 80% white).
   Only needs `pip install Pillow` — the template assets in this folder
   were pre-extracted from `TangerineUI-template.psd` once (browser
   chrome, drop shadow) and are already checked in; `phone-frame-template2.png`
   is a separately-made clean iPhone frame (see below). No need to touch
   the PSD again.
4. Inspect the corners (phone + browser window) and the status bar/home
   indicator area at full res before using it.
5. Add to README.md section 2.a, same `<img width="1784" ...>` pattern as
   the other variants.

## Why this works (background)

The original PSD (`TangerineUI-template.psd`) has one group per variant
(Lagoon/Cherry/Purple/Tangerine — Granite and later variants aren't in
there). Each group = a shared bezel/drop-shadow shape (identical across
variants, confirmed by hashing) + a "Light" screenshot layer (diagonal
top-left triangle) + a "Dark" screenshot layer (diagonal bottom-right
triangle, drawn first/underneath) + a "Mobile" phone-mockup layer (a real
screenshot baked into a frame, both flattened into one raster).

**Browser chrome + shadow (`base-canvas.png`, `chrome-*-template.png`):**
the Light/Dark layers are ONE flat screenshot each — real browser chrome
(macOS Safari traffic lights + address bar, ~168-170px tall) baked into
the same image as the Mastodon page content, with a diagonal cut baked
into the alpha channel (not a simple straight-line formula — verified by
rendering the alpha channel as a binary black/white image,
`alpha.point(lambda p: 255 if p>128 else 0)`, which shows a clean
quadrilateral). The trick: reuse the ORIGINAL alpha channel (exact
diagonal+rounded shape) and the ORIGINAL top ~168px chrome strip, swap
out everything below for new content. `base-canvas.png` is the fully
rendered "Tangerine" group (`group.composite()` via psd-tools+aggdraw) —
includes the real drop-shadow effect (shadows are a layer effect, not
part of the flat shape fill, so isolating just the bezel shape alone
renders fully transparent — has to come from a full group composite).
The shadow is legitimate/intentional (present in the original assets
too) but reads harsher against a plain light UI background than it did
against the original's custom warm promo-page color — hence
`SHADOW_STRENGTH` (weakens it) and `--accent` (tints the page background
to match, same idea as the original).

**Phone frame (`phone-frame-template2.png`):** the PSD's own "Mobile"
layer bakes a *real screenshot* into the frame, status bar and all — but
our raw phone captures are plain Chrome DevTools viewport renders (no
real device chrome), so pasting them into that layer's content area left
a blank gap where a status bar/home indicator should be. Fix: a separate,
purpose-made clean frame with a *realistic static* status bar + home
indicator baked in as opaque chrome, and a transparent rectangular hole
(76,168)-(794,1580) within the 869x1698 frame for app content only. That
hole has **sharp, unrounded corners** (confirmed by zooming the alpha
channel) — no corner-radius masking needed for the pasted content.
