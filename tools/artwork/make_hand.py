#!/usr/bin/env python3
"""hand-gesture showcase: 21-landmark MediaPipe skeleton + gesture classes."""
import os

import stylekit as sk

LM = {
    0: (0.50, 0.86), 1: (0.45, 0.72), 2: (0.42, 0.60), 3: (0.40, 0.50),
    4: (0.38, 0.42), 5: (0.44, 0.55), 6: (0.43, 0.42), 7: (0.42, 0.33),
    8: (0.42, 0.25), 9: (0.50, 0.53), 10: (0.50, 0.39), 11: (0.50, 0.30),
    12: (0.50, 0.22), 13: (0.56, 0.55), 14: (0.57, 0.42), 15: (0.575, 0.33),
    16: (0.58, 0.26), 17: (0.62, 0.60), 18: (0.64, 0.48), 19: (0.65, 0.40),
    20: (0.66, 0.34),
}
CONN = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
        (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

# normalized -> canvas (skeleton lives in the right 60%)
P = {i: (460 + (nx - 0.30) * 1150, 100 + (ny - 0.20) * 800)
     for i, (nx, ny) in LM.items()}

img, d = sk.canvas()

# titles
sk.chip(d, 24, 20, "Hand Gesture Recognition", size=26, bold=True)
sk.chip(d, 24, 64, "手势识别", size=24, cjk=True, fg=sk.TEXT_DIM)

# gesture class list (left column)
sk.chip(d, 24, 140, "GESTURE CLASSES", size=18, bold=True, fg=sk.GREEN)
gestures = ["None", "Closed_Fist", "Open_Palm", "Pointing_Up",
            "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"]
y = 190
for g in gestures:
    active = g == "Open_Palm"
    w, h = sk.chip(d, 24, y, g, size=17,
                   fg=sk.GREEN if active else sk.TEXT_DIM)
    if active:
        d.rounded_rectangle([24, y, 24 + w, y + h], radius=8,
                            outline=sk.GREEN, width=2)
    y += h + 10

# skeleton
for a, b in CONN:
    d.line([P[a], P[b]], fill=sk.CYAN, width=3)
for i, (x, y_) in P.items():
    r = 7 if i == 0 else 5
    d.ellipse([x - r, y_ - r, x + r, y_ + r], fill=sk.CYAN)

# palm attention box + label
xs = [p[0] for p in P.values()]
ys = [p[1] for p in P.values()]
sk.dashed_rect(d, min(xs) - 40, min(ys) - 40, max(xs) + 40, max(ys) + 40, sk.AMBER)
sk.chip(d, min(xs) - 40, min(ys) - 92, "Open_Palm 0.98", size=20, bold=True, fg=sk.GREEN)

sk.chip_right(d, sk.W - 24, sk.H - 60, "4-model NPU pipeline - 21 landmarks - UDP", size=19)

img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand-gesture.png"))
print("ok", img.size)
