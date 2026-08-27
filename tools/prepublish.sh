#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

python3 "$ROOT/tools/validate_catalog.py"

if [ "$#" -eq 0 ]; then
    echo "Static package checks passed."
    echo "Before publishing, install and start every changed solution on a reCamera, then run:"
    echo "  python3 tools/device_stream_test.py --host <device-ip> --app-id <app-id>"
    exit 0
fi

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [<device-ip> <app-id>]" >&2
    exit 2
fi

python3 "$ROOT/tools/device_stream_test.py" --host "$1" --app-id "$2"
