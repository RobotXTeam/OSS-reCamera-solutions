"""Shared style kit for reCamera solution showcase artwork.

All generated showcase PNGs (packages/*/) must render through this kit so the
Solutions gallery reads as one visual family: 1280x720 dark-slate canvas,
rounded chip labels, and a fixed annotation palette
(green = detections, amber = ROI/attention, cyan = skeleton/tracking).
Real device screenshots (e.g. onvif-yolo) are used as-is instead.
"""
import math

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

# palette
BG_TOP = (0x14, 0x1A, 0x22)
BG_BOT = (0x1F, 0x29, 0x37)
GREEN = (53, 224, 122)      # detection boxes / positive readouts
AMBER = (255, 210, 63)      # ROI / attention markers
CYAN = (64, 224, 224)       # skeletons / tracking
TEXT = (235, 242, 250)
TEXT_DIM = (160, 175, 195)
CHIP_BG = (15, 20, 28)
CHIP_EDGE = (60, 74, 92)

_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_CJK_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def font(size, bold=False, cjk=False):
    path = (_CJK_BOLD if bold else _CJK) if cjk else (_DEJAVU_BOLD if bold else _DEJAVU)
    return ImageFont.truetype(path, size)


def canvas():
    """1280x720 vertical gradient background + draw handle."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))
    return img, d


def chip(d, x, y, text, size=20, bold=False, cjk=False, fg=TEXT, pad=10):
    """Dark rounded label chip; returns (w, h)."""
    f = font(size, bold, cjk)
    bb = d.textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.rounded_rectangle([x, y, x + w + 2 * pad, y + h + 2 * pad], radius=8,
                        fill=CHIP_BG, outline=CHIP_EDGE, width=1)
    d.text((x + pad, y + pad - bb[1]), text, font=f, fill=fg)
    return w + 2 * pad, h + 2 * pad


def chip_right(d, x1, y, text, **kw):
    """Chip pinned by its right edge."""
    size, pad = kw.get("size", 20), kw.get("pad", 10)
    f = font(size, kw.get("bold", False), kw.get("cjk", False))
    bb = d.textbbox((0, 0), text, font=f)
    w = bb[2] - bb[0] + 2 * pad
    return chip(d, x1 - w, y, text, **kw)


def dashed_rect(d, x0, y0, x1, y1, color, width=2, dash=14, gap=10):
    for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1),
                             (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        pos = 0.0
        while pos < length:
            seg = min(dash, length - pos)
            d.line([(ax + ux * pos, ay + uy * pos),
                    (ax + ux * (pos + seg), ay + uy * (pos + seg))],
                   fill=color, width=width)
            pos += dash + gap
