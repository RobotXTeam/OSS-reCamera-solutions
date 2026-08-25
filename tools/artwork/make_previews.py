#!/usr/bin/env python3
"""Unified catalog previews for the legacy Other/ packages.

These debs ship no in-package image (their device art lives in the
supervisor firmware); the previews keep this repo's gallery artwork in
one visual family via the standard screenshot chrome.
"""
import os

import stylekit as sk

HERE = os.path.dirname(os.path.abspath(__file__))

PREVIEWS = [
    ("yolo-detector", "Object Detection", "通用目标检测",
     "YOLO - 80 classes - MQTT + RTSP"),
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
