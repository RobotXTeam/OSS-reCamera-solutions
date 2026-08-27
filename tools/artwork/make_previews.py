#!/usr/bin/env python3
"""Unified catalog previews for the Other/ application packages.

The previews are used both by the online catalog and inside each package.
"""
import os

import stylekit as sk

HERE = os.path.dirname(os.path.abspath(__file__))

PREVIEWS = [
    ("face-analysis", "Face Analysis", "人脸分析",
     "on-device gender / age / emotion"),
    ("ppocr-reader", "PP-OCR Text Reader", "PP-OCR 文字识别",
     "detect + recognize - CN/EN"),
]

for app_id, en, zh, footer in PREVIEWS:
    img = sk.frame_screenshot(os.path.join(HERE, "sources", f"{app_id}_raw.png"),
                              en, zh, footer)
    img.save(os.path.join(HERE, f"{app_id}.png"))
    print("ok", app_id, img.size)
