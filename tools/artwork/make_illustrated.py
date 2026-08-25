#!/usr/bin/env python3
"""ILLUSTRATED showcases: flat SVG scenes -> cairosvg -> standard chrome.

No real camera footage anywhere in the gallery art (repo policy): scenes
are authored as vector illustrations in illustrations/<id>.svg, rasterized
at 1280x720 and passed through stylekit.frame_screenshot() so the chrome
matches the FRAMED previews. Requires: pip install cairosvg.
"""
import os
import tempfile

import cairosvg

import stylekit as sk

HERE = os.path.dirname(os.path.abspath(__file__))

ITEMS = [
    ("groove-features", "Groove Features Counter", "凹槽特征计数器",
     "OpenCV pipeline - no model - UDP JPEG+bbox to host"),
    ("hand-gesture", "Hand Gesture Recognition", "手势识别",
     "4-model NPU pipeline - 21 landmarks - UDP"),
    ("onvif-yolo", "ONVIF YOLO Detector", "ONVIF 目标检测",
     "ONVIF Profile S - YOLO11n - RTSP :8554/live"),
]

for app_id, en, zh, footer in ITEMS:
    png = cairosvg.svg2png(url=os.path.join(HERE, "illustrations", app_id + ".svg"),
                           output_width=sk.W, output_height=sk.H)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png)
        tmp = f.name
    img = sk.frame_screenshot(tmp, en, zh, footer)
    os.unlink(tmp)
    img.save(os.path.join(HERE, app_id + ".png"))
    print("ok", app_id, img.size)
