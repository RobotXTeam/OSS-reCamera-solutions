# Showcase Artwork Style Guide

Every piece of gallery artwork in this repository — the PNGs shipped inside
`packages/**/*.deb` and the previews kept next to these generators — is
produced by `stylekit.py`, the executable version of this guide. New or
updated artwork must render through the kit; hand-edited pixels drift the
gallery out of one visual family.

Design baseline follows the `ui` design-intelligence skill's dark-slate
recommendation (OLED dark mode, status green, high-contrast text); the exact
tokens below are the approved local values.

Repo policy: gallery artwork never contains real camera footage. Scenes are
illustrated (flat vector style) or reuse existing illustrated rasters; the
chrome on top is always the kit's.

## Artwork classes, one chrome

| Class       | When                          | How                                    |
|-------------|-------------------------------|----------------------------------------|
| ILLUSTRATED | default for app scenes        | hand-authored flat SVG scene in `illustrations/<id>.svg` (light slate gradient, thin rounded frame, flat objects, lime label chips, white callouts, translucent bottom-right caption), rasterized by cairosvg at 1280×720, then `frame_screenshot()` chrome |
| FRAMED      | an existing illustrated raster source (e.g. firmware-shipped art) | `frame_screenshot()` — cover-fit, legibility scrims, standard chrome |

The older kit-primitive RENDERED schematics are retired; the primitives
(`canvas()`, `chip()`, `dashed_rect()`) stay in `stylekit.py` as the chrome
and composition backbone. All classes carry the identical chrome so the
Solutions gallery reads as one family.

## Canvas

- 1280×720 px, RGB PNG.
- Background (RENDERED): vertical gradient `#141A22 → #1F2937`.
- FRAMED sources get black scrims (alpha ≤ 150, 150 px deep) at top and
  bottom so chips always sit on ≥ 4.5:1 contrast.

## Chrome layout zones

- Title chip (EN, bold 26 px): `(24, 20)`.
- Sub-title chip (ZH, 24 px, dim): `(24, 64)`.
- Footer chip (19 px): right-aligned, 24 px margin, `H-60`.
- Safe area: keep subject content out of the top 120 px and bottom 80 px
  bands; 24 px side margins.

Chip = rounded rect (radius 8) fill `#0F141C`, 1 px edge `#3C4A5C`,
10 px padding.

## Palette (hex / role)

Annotation tokens:

| Token     | Value     | Use                                   |
|-----------|-----------|---------------------------------------|
| bg-top    | `#141A22` | canvas gradient start                  |
| bg-bot    | `#1F2937` | canvas gradient end                    |
| text      | `#EBF2FA` | primary labels (~15:1 on bg)           |
| text-dim  | `#A0AFC3` | secondary labels (~7:1 on bg)          |
| green     | `#35E07A` | model detections / positive readouts   |
| amber     | `#FFD23F` | ROI / attention markers                |
| cyan      | `#40E0E0` | skeletons / tracked keypoints          |
| chip-bg   | `#0F141C` | chip fill                              |
| chip-edge | `#3C4A5C` | chip border                            |

Auxiliary subject tokens (RENDERED illustrations only):

| Token        | Value     | Use                                  |
|--------------|-----------|--------------------------------------|
| metal        | `#C8D0D8` | workpiece / subject body              |
| metal-line   | `#B8C0C9` | surface detail lines on the body      |
| metal-edge   | `#5A6470` | subject outline                       |
| inset        | `#2A3138` | dark insets on the subject (grooves)  |
| green-dim    | `#9FE8B8` | secondary log / readout lines         |
| green-dimmer | `#6EA080` | tertiary log lines                    |

Annotation colors are semantic: green/lime = detection output, amber = region
of interest, cyan = tracking. ILLUSTRATED scenes use the firmware-illustration
lime (`#B8E356` boxes, `#D3F28A` label chips) for detections; FRAMED sources
keep their original colors as-is. Do not introduce a new hue without updating
these tables first.

## Typography

- Latin: DejaVu Sans / DejaVu Sans Bold (offline PIL stand-in for the skill's
  Fira Sans); CJK: Noto Sans CJK SC.
- Sizes: title 26 bold, ZH sub 24, footer 19, small labels 17–20.
- Body-equivalent text never below 17 px; all text ≥ 4.5:1 contrast against
  whatever is under it (the scrims guarantee this on screenshots).

## Files & naming

- Generators: `make_illustrated.py` (SVG → cairosvg → chrome) and
  `make_previews.py` (FRAMED firmware rasters), importing `stylekit`.
- Vector sources: `illustrations/<id>.svg` (committed; the editable truth for
  ILLUSTRATED art). Render dependency: `pip install cairosvg`.
- Output: `tools/artwork/<id>.png` (committed; GitHub previews it).
- Source rasters: `tools/artwork/sources/<id>_raw.png` (committed, keeps the
  repo self-contained).
- In-deb copy: `userdata/local/apps/img/<id>.png`, referenced by the manifest
  as `"image": "/appimg/<id>.png"`. Byte-identical to the tools/artwork copy.
- Catalog: optional `image` field on the entry — CDN URL of the
  `tools/artwork/<id>.png` preview, for online-gallery card art.

## Adding artwork for a new package

1. Author the scene: copy an existing `illustrations/<id>.svg` as template,
   register the app in `make_illustrated.py` (renders + applies chrome).
   Only if an illustrated raster already exists → FRAMED via
   `frame_screenshot()` (see `make_previews.py`). Never use real footage.
2. Run the script; commit `<id>.png` + `.svg` (+ `sources/` raw if FRAMED).
3. Ship the same PNG inside the deb at `userdata/local/apps/img/<id>.png`
   and set the manifest `image` field.
4. Add the catalog entry's optional `image` URL.
5. QA checklist below; a reviewer must actually look at the PNG.

## QA checklist

- [ ] 1280×720 RGB, opens clean (`PIL.Image.verify()`).
- [ ] Title/sub/footer chips present, unclipped, inside the layout zones.
- [ ] Only palette/auxiliary tokens above (ILLUSTRATED); FRAMED source pixels
      are exempt by definition. No real camera footage.
- [ ] Text ≥ 4.5:1 against underlying pixels.
- [ ] In-deb copy byte-identical to `tools/artwork/<id>.png`.
