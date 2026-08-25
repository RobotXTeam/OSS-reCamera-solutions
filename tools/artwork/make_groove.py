#!/usr/bin/env python3
"""groove-features showcase: production-line groove counter illustration."""
import os

import stylekit as sk

img, d = sk.canvas()

# titles
sk.chip(d, 24, 20, "Groove Features Counter", size=26, bold=True)
sk.chip(d, 24, 64, "凹槽特征计数器", size=24, cjk=True, fg=sk.TEXT_DIM)

# workpiece band
bx0, bx1, by0, by1 = 140, 1140, 280, 470
d.rounded_rectangle([bx0, by0, bx1, by1], radius=6, fill=(200, 208, 216),
                    outline=(90, 100, 112), width=2)
for yy in range(by0 + 14, by1, 18):
    d.line([(bx0 + 10, yy), (bx1 - 10, yy)], fill=(184, 192, 201), width=1)

# grooves + detection boxes
for x in [230, 420, 610, 800, 990]:
    d.rectangle([x, by0 + 12, x + 44, by1 - 12], fill=(42, 49, 56))
    d.rectangle([x - 10, by0 + 4, x + 54, by1 - 4], outline=sk.GREEN, width=3)

# ROI + readout
sk.dashed_rect(d, bx0 - 30, by0 - 34, bx1 + 30, by1 + 34, sk.AMBER)
d.text((bx0 - 26, by0 - 66), "ROI", font=sk.font(20, bold=True), fill=sk.AMBER)
d.text((bx1 - 260, by0 - 66), "count=5  frame_ms=7.4",
       font=sk.font(26, bold=True), fill=sk.GREEN)

# daemon log lines (match real output)
d.text((28, sk.H - 92), "[groove_features] count=5 frame_ms=7.42",
       font=sk.font(20), fill=(159, 232, 184))
d.text((28, sk.H - 62), "[groove_features] count=4 frame_ms=6.95",
       font=sk.font(20), fill=(110, 160, 128))

sk.chip_right(d, sk.W - 24, sk.H - 60, "OpenCV pipeline - no model - UDP JPEG+bbox to host", size=19)

img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "groove-features.png"))
print("ok", img.size)
