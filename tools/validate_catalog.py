#!/usr/bin/env python3
"""Validate every reCamera solution package before it is published.

This is intentionally strict: a solution shown as installable in Studio must
provide the H.264-over-WebSocket contract consumed by the WebUI. UDP and RTSP
may be offered as additional outputs, but they do not satisfy that contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog.json"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SAFE_FILE = re.compile(r"^[A-Za-z0-9._+-]+\.deb$")
SAFE_CONFIG_KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CONFIG_TYPES = {"number", "boolean", "enum", "string", "zone", "line"}
CATEGORY_DIRS = {
    "factory": "Factory",
    "building": "Building",
    "medical": "Medical",
    "ecology": "Ecology",
    "other": "Other",
}


def run(*args: str, check: bool = True) -> str:
    proc = subprocess.run(args, text=True, capture_output=True)
    if check and proc.returncode:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    return proc.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def executable(path: Path) -> bool:
    return path.is_file() and bool(path.stat().st_mode & stat.S_IXUSR)


def package_path(entry: dict) -> Path:
    category = entry.get("category", "other")
    folder = CATEGORY_DIRS.get(category)
    if not folder:
        raise ValueError(f"unsupported category: {category!r}")
    return ROOT / "packages" / folder / entry.get("package_file", "")


def validate_config_schema(schema: object, fail) -> None:
    if not isinstance(schema, dict):
        fail("manifest config_schema must be an object")
        return
    groups = schema.get("groups")
    if not isinstance(groups, list) or not groups:
        fail("config_schema.groups must be a non-empty list")
        return
    seen: set[str] = set()
    for group_index, group in enumerate(groups):
        if not isinstance(group, dict):
            fail(f"config_schema.groups[{group_index}] must be an object")
            continue
        items = group.get("items")
        if not isinstance(items, list) or not items:
            fail(f"config group {group_index} must contain at least one item")
            continue
        for item_index, item in enumerate(items):
            label = f"config item {group_index}.{item_index}"
            if not isinstance(item, dict):
                fail(f"{label} must be an object")
                continue
            key = item.get("key", "")
            if not SAFE_CONFIG_KEY.fullmatch(key):
                fail(f"{label} has invalid key {key!r}")
            elif key in seen:
                fail(f"duplicate config key {key!r}")
            seen.add(key)
            item_type = item.get("type")
            if item_type not in CONFIG_TYPES:
                fail(f"{label} has unsupported type {item_type!r}")
                continue
            if not isinstance(item.get("title"), str) or not isinstance(item.get("title_zh"), str):
                fail(f"{label} requires title and title_zh")
            default = item.get("default")
            if item_type == "number":
                low, high = item.get("min"), item.get("max")
                if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (low, high, default)):
                    fail(f"{label} number requires numeric min, max and default")
                elif low >= high or not low <= default <= high:
                    fail(f"{label} requires min < max and default inside the range")
            elif item_type == "boolean" and not isinstance(default, bool):
                fail(f"{label} boolean requires a boolean default")
            elif item_type == "string" and not isinstance(default, str):
                fail(f"{label} string requires a string default")
            elif item_type == "enum":
                options = item.get("options")
                if not isinstance(options, list) or not options:
                    fail(f"{label} enum requires non-empty options")


def validate_entry(entry: dict, seen_ids: set[str], seen_files: set[str]) -> list[str]:
    errors: list[str] = []
    app_id = entry.get("app_id", "")
    filename = entry.get("package_file", "")
    prefix = app_id or filename or "<unknown>"

    def fail(message: str) -> None:
        errors.append(f"{prefix}: {message}")

    if not SAFE_ID.fullmatch(app_id):
        fail("app_id must match ^[a-z0-9][a-z0-9-]{0,62}$")
    if app_id in seen_ids:
        fail("duplicate app_id")
    seen_ids.add(app_id)

    if not SAFE_FILE.fullmatch(filename):
        fail("package_file must be a safe .deb filename")
    if filename in seen_files:
        fail("duplicate package_file")
    seen_files.add(filename)

    try:
        deb = package_path(entry)
    except ValueError as exc:
        fail(str(exc))
        return errors
    if not deb.is_file():
        fail(f"package missing: {deb.relative_to(ROOT)}")
        return errors

    actual_size = deb.stat().st_size
    if entry.get("size") != actual_size:
        fail(f"catalog size {entry.get('size')} != file size {actual_size}")
    actual_sha = sha256(deb)
    if entry.get("sha256") != actual_sha:
        fail(f"catalog sha256 does not match ({actual_sha})")

    urls = entry.get("urls")
    if not isinstance(urls, list) or not urls:
        fail("urls must contain at least one download URL")
    elif not all(isinstance(url, str) and url.startswith("https://") and url.endswith(filename) for url in urls):
        fail("every download URL must be HTTPS and end with package_file")

    try:
        members = run("ar", "t", str(deb)).splitlines()
    except RuntimeError as exc:
        fail(str(exc))
        return errors
    required_members = {"debian-binary", "control.tar.gz", "data.tar.gz"}
    if set(members) != required_members:
        fail(
            "device opkg requires exactly debian-binary, control.tar.gz and "
            f"data.tar.gz; found {', '.join(members)}"
        )

    try:
        fields = [
            run("dpkg-deb", "-f", str(deb), field).strip()
            for field in ("Package", "Version", "Architecture")
        ]
    except RuntimeError as exc:
        fail(str(exc))
        return errors
    if len(fields) < 3:
        fail("missing Package/Version/Architecture control fields")
        return errors
    package_name, package_version, architecture = fields[:3]
    if package_name != entry.get("package_name"):
        fail(f"control Package {package_name!r} != catalog package_name")
    if package_version != entry.get("package_version"):
        fail(f"control Version {package_version!r} != catalog package_version")
    if architecture != "riscv64":
        fail(f"Architecture must be riscv64, found {architecture!r}")

    with tempfile.TemporaryDirectory(prefix="recamera-package-") as tmp:
        root = Path(tmp)
        try:
            run("dpkg-deb", "-x", str(deb), str(root))
        except RuntimeError as exc:
            fail(str(exc))
            return errors

        manifest_path = root / "usr/share/supervisor/apps" / f"{app_id}.json"
        if not manifest_path.is_file():
            fail(f"missing manifest /usr/share/supervisor/apps/{app_id}.json")
            return errors
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"invalid manifest JSON: {exc}")
            return errors

        expected = {
            "id": app_id,
            "package": package_name,
            "package_version": package_version,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                fail(f"manifest {key} must be {value!r}")

        init_script = manifest.get("init_script", "")
        if not init_script.startswith("/etc/init.d/K92"):
            fail("manifest init_script must use /etc/init.d/K92<app-id>")
        elif not executable(root / init_script.lstrip("/")):
            fail(f"init script is missing or not executable: {init_script}")

        image = manifest.get("image", "")
        if not image.startswith("/appimg/"):
            fail("manifest image must use /appimg/<file>")
        else:
            packaged_image = root / "userdata/local/apps/img" / Path(image).name
            if not packaged_image.is_file():
                fail(f"manifest image is not packaged: {image}")

        required_files = manifest.get("required_files")
        if not isinstance(required_files, list) or not required_files:
            fail("manifest required_files must be a non-empty list")
        else:
            for required in required_files:
                if not isinstance(required, str) or not required.startswith("/"):
                    fail(f"invalid required_files entry: {required!r}")
                    continue
                if not (root / required.lstrip("/")).exists():
                    fail(f"required file is not packaged: {required}")

        debug_ws = manifest.get("debug_ws")
        if not isinstance(debug_ws, dict):
            fail("WebUI preview requires manifest.debug_ws")
        else:
            if debug_ws.get("port") != 8001:
                fail("debug_ws.port must be 8001")
            if debug_ws.get("video_path") != "/":
                fail("debug_ws.video_path must be /")
            if debug_ws.get("results_path") != "/results":
                fail("debug_ws.results_path must be /results")

        if "config_schema" in manifest:
            validate_config_schema(manifest["config_schema"], fail)
            run_script = root / "userdata/local/apps" / app_id / "run.sh"
            if not executable(run_script):
                fail(f"configurable solution requires executable {run_script.relative_to(root)}")
            else:
                run_text = run_script.read_text(encoding="utf-8", errors="replace")
                if ".config.json" not in run_text or app_id not in run_text:
                    fail("configurable solution run.sh must consume <app-id>.config.json")

        binary = root / "usr/local/bin" / app_id
        if not executable(binary):
            fail(f"missing executable /usr/local/bin/{app_id}")
        else:
            binary_strings = run("strings", str(binary), check=False)
            if "Upgrade: WebSocket" not in binary_strings or "debug_stream" not in binary_strings:
                fail(
                    "binary does not contain the Studio H.264-over-WebSocket "
                    "debug_stream implementation"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    args = parser.parse_args()

    missing_tools = [tool for tool in ("ar", "dpkg-deb", "strings") if not shutil.which(tool)]
    if missing_tools:
        print(f"missing required tools: {', '.join(missing_tools)}", file=sys.stderr)
        return 2

    try:
        catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid catalog: {exc}", file=sys.stderr)
        return 2

    entries = catalog.get("entries")
    if catalog.get("format") != 1 or not isinstance(entries, list) or not entries:
        print("catalog format must be 1 and entries must be a non-empty list", file=sys.stderr)
        return 2

    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("catalog entry must be an object")
            continue
        errors.extend(validate_entry(entry, seen_ids, seen_files))

    if errors:
        print(f"FAILED: {len(errors)} package contract error(s)", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"PASS: {len(entries)} packages satisfy the reCamera Studio contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
