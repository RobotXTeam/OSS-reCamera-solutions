#!/usr/bin/env python3
"""Check that a running solution sends real H.264 frames to the Studio WebUI."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import time


def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RuntimeError("WebSocket closed before a video frame arrived")
        data.extend(chunk)
    return bytes(data)


def websocket_video_frame(host: str, port: int, path: str, timeout: float) -> bytes:
    key = base64.b64encode(os.urandom(16)).decode()
    expected = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    ).decode()
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(timeout)
    request = (
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(request.encode())
    response = bytearray()
    while b"\r\n\r\n" not in response:
        response.extend(sock.recv(4096))
        if len(response) > 16384:
            raise RuntimeError("oversized WebSocket handshake")
    headers = response.decode("latin1", errors="replace")
    if " 101 " not in headers.split("\r\n", 1)[0]:
        raise RuntimeError(f"WebSocket upgrade failed: {headers.splitlines()[0]}")
    if expected.lower() not in headers.lower():
        raise RuntimeError("invalid Sec-WebSocket-Accept")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        first, second = recv_exact(sock, 2)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", recv_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", recv_exact(sock, 8))[0]
        if second & 0x80:
            mask = recv_exact(sock, 4)
        else:
            mask = None
        payload = recv_exact(sock, length)
        if mask:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 0x2 and payload:
            sock.close()
            return payload
        if opcode == 0x8:
            raise RuntimeError("WebSocket closed without a binary video frame")
    raise RuntimeError("timed out waiting for a binary video frame")


def looks_like_h264(payload: bytes) -> bool:
    for marker in (b"\x00\x00\x00\x01", b"\x00\x00\x01"):
        pos = payload.find(marker)
        if pos >= 0 and pos + len(marker) < len(payload):
            nal_type = payload[pos + len(marker)] & 0x1F
            if nal_type in {1, 5, 6, 7, 8, 9}:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--path", default="/")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        payload = websocket_video_frame(args.host, args.port, args.path, args.timeout)
        if not looks_like_h264(payload):
            raise RuntimeError(f"received {len(payload)} bytes, but no H.264 NAL unit was found")
    except (OSError, RuntimeError) as exc:
        print(json.dumps({"app_id": args.app_id, "status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({
        "app_id": args.app_id,
        "status": "passed",
        "endpoint": f"ws://{args.host}:{args.port}{args.path}",
        "first_frame_bytes": len(payload),
        "h264": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
