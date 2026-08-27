#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

python3 "$ROOT/tools/validate_catalog.py"

if [ "$#" -eq 0 ]; then
    echo "Static package checks passed."
    echo "Before publishing, install every changed solution on a reCamera, then run:"
    echo "  ./tools/prepublish.sh <device-ip> <app-id>"
    exit 0
fi

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [<device-ip> <app-id>]" >&2
    exit 2
fi

REPORT="/tmp/recamera-transition-matrix-$2.json"
python3 "$ROOT/tools/device_transition_matrix.py" \
    --host "$1" \
    --required-app-id "$2" \
    --report "$REPORT"
echo "Complete real-device transition and H.264 matrix passed. Report: $REPORT"
