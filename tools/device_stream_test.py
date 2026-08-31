#!/usr/bin/env python3
"""Check that a running solution honors the full Studio integration contract.

Verified live against the device (the app must be the active camera owner):

1. Main H.264-over-WebSocket preview (--path, default /) — real H.264 frames.
2. Results JSON channel (--results-path, default /results) — at least one
   parseable JSON message carrying the sscma-node envelope (timestamp,
   frame_id, resolution, boxes).
3. Sub H.264 stream (--sub-path, default /sub; pass --sub-path '' to skip) —
   real H.264 frames on the secondary Studio route.
4. RTSP external output (--rtsp-port, default 8554; pass --rtsp-port 0 to
   skip) — the TCP listener answers, i.e. the RTSP server is up.

Backward compatible: a plain --host/--app-id invocation runs all four checks.
"""

from __future__ import annotations

import argparse
import base64
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
            raise RuntimeError("WebSocket closed before a complete message arrived")
        data.extend(chunk)
    return bytes(data)


def websocket_connect(host: str, port: int, path: str, timeout: float) -> socket.socket:
    connect_deadline = time.monotonic() + timeout
    key = base64.b64encode(os.urandom(16)).decode()
    expected = base64.b64encode(
        __import__("hashlib").sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    ).decode()

    sock: socket.socket | None = None
    last_connect_error: OSError | None = None
    while True:
        remaining = connect_deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(
                f"cannot connect to {host}:{port}{path}: {last_connect_error}"
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
    return sock


def read_websocket_message(sock: socket.socket) -> tuple[int, bytes]:
    """Read one frame; returns (opcode, payload)."""
    first, second = recv_exact(sock, 2)
    opcode = first & 0x0F
    length = second & 0x7F
    if length == 126:
        (length,) = struct.unpack(">H", recv_exact(sock, 2))
    elif length == 127:
        (length,) = struct.unpack(">Q", recv_exact(sock, 8))
    mask = recv_exact(sock, 4) if second & 0x80 else None
    payload = recv_exact(sock, length)
    if mask:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return opcode, payload


def websocket_video_frames(
    host: str,
    port: int,
    path: str,
    timeout: float,
    min_frames: int,
    observe_seconds: float,
) -> list[bytes]:
    sock = websocket_connect(host, port, path, timeout)
    started = time.monotonic()
    deadline = started + timeout
    first_frame_at: float | None = None
    frames: list[bytes] = []
    try:
        while time.monotonic() < deadline:
            opcode, payload = read_websocket_message(sock)
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
                    return frames
            if opcode == 0x8:
                raise RuntimeError("server closed the video channel")
        raise RuntimeError(
            f"only {len(frames)} frame(s) within {timeout:.0f}s "
            f"(need {min_frames} over {observe_seconds:.0f}s)"
        )
    finally:
        sock.close()


def websocket_results_json(
    host: str,
    port: int,
    path: str,
    timeout: float,
    min_messages: int = 1,
) -> dict:
    """Collect results-channel JSON messages and validate the envelope."""
    sock = websocket_connect(host, port, path, timeout)
    deadline = time.monotonic() + timeout
    messages: list[dict] = []
    envelope_keys = {"timestamp", "frame_id", "resolution", "boxes"}
    try:
        while time.monotonic() < deadline:
            opcode, payload = read_websocket_message(sock)
            if opcode == 0x1 and payload:
                try:
                    doc = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise RuntimeError("results message is not valid JSON")
                if not isinstance(doc, dict) or not envelope_keys.issubset(doc):
                    raise RuntimeError(
                        "results JSON lacks the sscma-node envelope "
                        f"{sorted(envelope_keys)}"
                    )
                messages.append(doc)
                if len(messages) >= min_messages:
                    return messages[-1]
            if opcode == 0x8:
                raise RuntimeError("server closed the results channel")
        raise RuntimeError(f"no results JSON within {timeout:.0f}s")
    finally:
        sock.close()


def rtsp_reachable(host: str, port: int, timeout: float) -> bool:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(b"OPTIONS rtsp://%s:%d/ RTSP/1.0\r\nCSeq: 1\r\n\r\n" % (host.encode(), port))
        response = sock.recv(256)
    return b"RTSP/1.0" in response


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
    parser.add_argument("--results-path", default="/results",
                        help="results JSON route ('' to skip)")
    parser.add_argument("--sub-path", default="/sub",
                        help="sub H.264 route ('' to skip)")
    parser.add_argument("--rtsp-port", type=int, default=8554,
                        help="RTSP listener port (0 to skip)")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--min-frames", type=int, default=3)
    parser.add_argument("--observe-seconds", type=float, default=5.0)
    args = parser.parse_args()

    report: dict = {
        "app_id": args.app_id,
        "checks": {},
    }
    failures: list[str] = []

    def check(name: str, fn):
        try:
            report["checks"][name] = fn()
        except (OSError, RuntimeError, ValueError) as exc:
            report["checks"][name] = {"status": "failed", "error": str(exc)}
            failures.append(f"{name}: {exc}")

    # 1) Main H.264 preview.
    def video_check():
        frames = websocket_video_frames(
            args.host, args.port, args.path, args.timeout,
            max(1, args.min_frames), max(0.0, args.observe_seconds),
        )
        return {
            "status": "passed",
            "endpoint": f"ws://{args.host}:{args.port}{args.path}",
            "frames": len(frames),
            "first_frame_bytes": len(frames[0]),
            "h264": True,
        }

    check("video", video_check)

    # 2) Results JSON envelope.
    if args.results_path:
        check("results", lambda: dict(
            {"status": "passed", "envelope": True},
            sample_keys=sorted(
                websocket_results_json(
                    args.host, args.port, args.results_path, args.timeout
                ).keys()
            ),
        ))

    # 3) Sub stream.
    if args.sub_path:
        check("sub_video", lambda: {
            "status": "passed",
            "endpoint": f"ws://{args.host}:{args.port}{args.sub_path}",
            "frames": len(websocket_video_frames(
                args.host, args.port, args.sub_path, args.timeout,
                max(1, args.min_frames), 0.0,
            )),
            "h264": True,
        })

    # 4) RTSP external output.
    if args.rtsp_port > 0:
        check("rtsp", lambda: {
            "status": "passed",
            "endpoint": f"rtsp://{args.host}:{args.rtsp_port}/",
            "answered": rtsp_reachable(args.host, args.rtsp_port, 5.0),
        })

    report["status"] = "failed" if failures else "passed"
    print(json.dumps(report, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
