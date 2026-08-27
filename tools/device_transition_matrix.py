#!/usr/bin/env python3
"""Exercise every directed transition between installed Studio camera apps."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_REWEB = Path("/home/steven/.codex/skills/reweb")
DEFAULT_STREAM_TEST = Path(__file__).with_name("device_stream_test.py")


def run(args: list[str], timeout: int = 180, check: bool = True) -> str:
    proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}")
    return proc.stdout.strip()


def euler_transitions(vertices: list[str], start: str) -> list[str]:
    """Return a restoring Euler circuit for all ordered pairs without self-loops."""
    adjacency = {
        vertex: [other for other in reversed(vertices) if other != vertex]
        for vertex in vertices
    }
    stack = [start]
    circuit: list[str] = []
    while stack:
        vertex = stack[-1]
        if adjacency[vertex]:
            stack.append(adjacency[vertex].pop())
        else:
            circuit.append(stack.pop())
    return list(reversed(circuit))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.168.2.102")
    parser.add_argument("--reweb", type=Path, default=DEFAULT_REWEB)
    parser.add_argument("--stream-test", type=Path, default=DEFAULT_STREAM_TEST)
    parser.add_argument(
        "--required-app-id",
        help="fail unless this newly installed application is present in the matrix",
    )
    parser.add_argument("--observe-seconds", type=float, default=2.0)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    ssh_wrapper = args.reweb / "scripts/recamera-ssh.sh"
    lib = args.reweb / "scripts/lib.sh"
    if not ssh_wrapper.is_file() or not lib.is_file() or not args.stream_test.is_file():
        print("required reweb wrapper or stream tester is missing", file=sys.stderr)
        return 2

    def ssh(command: str, timeout: int = 30) -> str:
        return run([str(ssh_wrapper), command], timeout=timeout)

    def sudo(command: str, timeout: int = 180) -> str:
        shell = f". {shlex.quote(str(lib))}; recamera_sudo_sh {shlex.quote(command)}"
        return run(["bash", "-lc", shell], timeout=timeout)

    scripts = [
        line for line in ssh(
            'for s in /etc/init.d/K92*; do [ -x "$s" ] && echo "$s"; done'
        ).splitlines() if line.startswith("/etc/init.d/K92")
    ]
    if len(scripts) < 2:
        print("fewer than two installed camera applications found", file=sys.stderr)
        return 2

    by_id = {Path(script).name.removeprefix("K92"): script for script in scripts}
    if args.required_app_id and args.required_app_id not in by_id:
        print(
            f"required application is not installed: {args.required_app_id}",
            file=sys.stderr,
        )
        return 2
    original_script = ssh(
        "sed -n 's/.*\"active_script\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p' "
        "/userdata/local/apps/state.json | head -n 1"
    )
    original_id = next(
        (app_id for app_id, script in by_id.items() if script == original_script),
        sorted(by_id)[0],
    )
    ids = sorted(by_id)
    sequence = euler_transitions(ids, original_id)
    expected_edges = len(ids) * (len(ids) - 1)
    if len(sequence) != expected_edges + 1 or sequence[-1] != original_id:
        raise RuntimeError("failed to generate a complete restoring transition circuit")

    report: dict[str, object] = {
        "host": args.host,
        "apps": ids,
        "original": original_id,
        "required_app_id": args.required_app_id,
        "expected_transitions": expected_edges,
        "started_at": int(time.time()),
        "results": [],
    }
    failures = 0
    try:
        for index, (source, target) in enumerate(zip(sequence, sequence[1:]), 1):
            started = time.monotonic()
            result: dict[str, object] = {"index": index, "from": source, "to": target}
            print(f"[{index:02d}/{expected_edges}] {source} -> {target}", flush=True)
            command = f"""
set -eu
result=$(/usr/share/supervisor/scripts/main.sh app_handoff {shlex.quote(by_id[source])} {shlex.quote(by_id[target])})
[ "$result" = "OK" ]
owner=$(sed -n 's/^script=//p' /var/run/recamera-camera-owner)
[ "$owner" = {shlex.quote(by_id[target])} ]
holders=$(fuser /dev/cvi-vpss 2>/dev/null | tr ' ' '\\n' | sed -n '/^[0-9][0-9]*$/p' | sort -nu)
[ "$(printf '%s\\n' "$holders" | sed '/^$/d' | wc -l)" -eq 1 ]
netstat -ltn 2>/dev/null | grep -q ':8001 '
printf 'owner=%s holder=%s\\n' "$owner" "$holders"
"""
            try:
                verification = sudo(command, timeout=170)
                stream = run([
                    sys.executable, str(args.stream_test), "--host", args.host,
                    "--app-id", target, "--timeout", "25", "--min-frames", "3",
                    "--observe-seconds", str(args.observe_seconds),
                ], timeout=40)
                result.update({
                    "status": "passed",
                    "seconds": round(time.monotonic() - started, 2),
                    "verification": verification,
                    "stream": json.loads(stream),
                })
                print(f"  PASS {result['seconds']}s", flush=True)
            except Exception as exc:
                failures += 1
                result.update({
                    "status": "failed",
                    "seconds": round(time.monotonic() - started, 2),
                    "error": str(exc),
                })
                print(f"  FAIL {exc}", flush=True)
            report["results"].append(result)
    finally:
        owner = sudo("sed -n 's/^script=//p' /var/run/recamera-camera-owner 2>/dev/null || true")
        if owner != original_script and original_script:
            try:
                sudo(
                    f"/usr/share/supervisor/scripts/main.sh app_handoff "
                    f"{shlex.quote(owner or '-')} {shlex.quote(original_script)}",
                    timeout=170,
                )
            except Exception as exc:
                failures += 1
                report["restore_error"] = str(exc)

    report["finished_at"] = int(time.time())
    report["passed"] = expected_edges - failures
    report["failed"] = failures
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"REPORT {args.report}")
    print(f"SUMMARY passed={report['passed']} failed={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
