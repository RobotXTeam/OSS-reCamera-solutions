# Showcase Artwork Style Guide

Every piece of gallery artwork in this repository — the PNGs shipped inside
`packages/**/*.deb` and the previews kept next to these generators — is
produced by `stylekit.py`, the executable version of this guide. New or
updated artwork must render through the kit; hand-edited pixels drift the
gallery out of one visual family.

Design baseline follows the `ui` design-intelligence skill's dark-slate
recommendation (OLED dark mode, status green, high-contrast text); the exact
tokens below are the approved local values.

## Two artwork classes, one chrome

| Class     | When                          | How                                    |
|-----------|-------------------------------|----------------------------------------|
| FRAMED    | an existing raster source exists (real device screenshot, or firmware-shipped illustration) | `stylekit.frame_screenshot()` — cover-fit to canvas, top/bottom legibility scrims, standard chrome |
| RENDERED  | no source material (model-free apps, pipelines) | kit primitives only: `canvas()`, `chip()`, `dashed_rect()`, fonts |

Both classes carry the identical chrome, so the Solutions gallery reads as
one family regardless of source material.

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

Annotation colors are semantic: green = detection output, amber = region of
interest, cyan = tracking. The semantics apply to kit-rendered artwork;
FRAMED sources keep the device's own OSD colors as-is (a real screenshot is
evidence and is not restyled — e.g. onvif-yolo's red detection boxes stay
red). Do not introduce a new hue without updating these tables first.

## Typography

- Latin: DejaVu Sans / DejaVu Sans Bold (offline PIL stand-in for the skill's
  Fira Sans); CJK: Noto Sans CJK SC.
- Sizes: title 26 bold, ZH sub 24, footer 19, small labels 17–20.
- Body-equivalent text never below 17 px; all text ≥ 4.5:1 contrast against
  whatever is under it (the scrims guarantee this on screenshots).

## Files & naming

- Generators: `make_<id>.py` (or grouped, e.g. `make_previews.py`), importing
  `stylekit`.
- Output: `tools/artwork/<id>.png` (committed; GitHub previews it).
- Source rasters: `tools/artwork/sources/<id>_raw.png` (committed, keeps the
  repo self-contained).
- In-deb copy: `userdata/local/apps/img/<id>.png`, referenced by the manifest
  as `"image": "/appimg/<id>.png"`. Byte-identical to the tools/artwork copy.
- Catalog: optional `image` field on the entry — CDN URL of the
  `tools/artwork/<id>.png` preview, for online-gallery card art.

## Adding artwork for a new package

1. Raster source available (screenshot or firmware illustration)? → FRAMED:
   write `make_<id>.py` calling
   `frame_screenshot(sources/<id>_raw.png, EN, ZH, footer)`.
   Otherwise RENDERED: compose with kit primitives on `canvas()`.
2. Run the script; commit `<id>.png` + script (+ `sources/` raw).
3. Ship the same PNG inside the deb at `userdata/local/apps/img/<id>.png`
   and set the manifest `image` field.
4. Add the catalog entry's optional `image` URL.
5. QA checklist below; a reviewer must actually look at the PNG.

## QA checklist

- [ ] 1280×720 RGB, opens clean (`PIL.Image.verify()`).
- [ ] Title/sub/footer chips present, unclipped, inside the layout zones.
- [ ] Only palette/auxiliary tokens above (RENDERED); FRAMED source pixels
      are exempt by definition.
- [ ] Text ≥ 4.5:1 against underlying pixels.
- [ ] In-deb copy byte-identical to `tools/artwork/<id>.png`.
