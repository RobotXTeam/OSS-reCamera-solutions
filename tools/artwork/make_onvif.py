#!/usr/bin/env python3
"""onvif-yolo showcase: real device screenshot through the standard chrome."""
import os

import stylekit as sk

HERE = os.path.dirname(os.path.abspath(__file__))
img = sk.frame_screenshot(
    os.path.join(HERE, "sources", "onvif-yolo_raw.png"),
    "ONVIF YOLO Detector", "ONVIF 目标检测",
    "ONVIF Profile S - YOLO11n - RTSP :8554/live")
img.save(os.path.join(HERE, "onvif-yolo.png"))
print("ok", img.size)
