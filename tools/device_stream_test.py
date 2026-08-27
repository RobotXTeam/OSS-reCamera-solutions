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


def websocket_video_frames(
    host: str,
    port: int,
    path: str,
    timeout: float,
    min_frames: int,
    observe_seconds: float,
) -> list[bytes]:
    connect_deadline = time.monotonic() + timeout
    key = base64.b64encode(os.urandom(16)).decode()
    expected = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    ).decode()
    last_connect_error: OSError | None = None
    while True:
        remaining = connect_deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(
                f"debug stream did not open {host}:{port} within {timeout:.1f}s"
                + (f": {last_connect_error}" if last_connect_error else "")
            )
        try:
            sock = socket.create_connection((host, port), timeout=min(2.0, remaining))
            break
        except OSError as exc:
            last_connect_error = exc
            time.sleep(min(0.25, max(0.0, remaining)))
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

    started = time.monotonic()
    deadline = started + timeout
    first_frame_at: float | None = None
    frames: list[bytes] = []
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
            if not looks_like_h264(payload):
                raise RuntimeError(
                    f"received {len(payload)} bytes, but no H.264 NAL unit was found"
                )
            frames.append(payload)
            if first_frame_at is None:
                first_frame_at = time.monotonic()
            observed = time.monotonic() - first_frame_at
            if len(frames) >= min_frames and observed >= observe_seconds:
                sock.close()
                return frames
        if opcode == 0x8:
            raise RuntimeError("WebSocket closed without a binary video frame")
    raise RuntimeError(
        f"stream was not stable for {observe_seconds:.1f}s "
        f"({len(frames)}/{min_frames} H.264 frames received)"
    )


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
    parser.add_argument("--min-frames", type=int, default=3)
    parser.add_argument("--observe-seconds", type=float, default=5.0)
    args = parser.parse_args()

    try:
        frames = websocket_video_frames(
            args.host,
            args.port,
            args.path,
            args.timeout,
            max(1, args.min_frames),
            max(0.0, args.observe_seconds),
        )
    except (OSError, RuntimeError) as exc:
        print(json.dumps({"app_id": args.app_id, "status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({
        "app_id": args.app_id,
        "status": "passed",
        "endpoint": f"ws://{args.host}:{args.port}{args.path}",
        "frames": len(frames),
        "first_frame_bytes": len(frames[0]),
        "observed_seconds": args.observe_seconds,
        "h264": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
