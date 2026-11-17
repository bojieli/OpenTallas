#!/bin/bash
# Copy only input/, source.f, component_constants.svh, component_pw.hex,
# stale_pw.hex, dw.hex, preparation.json, generate_masks.py and run.sh to a NEW
# private directory. Existing traces/failure evidence are never overwritten.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I generate_masks.py
exec bash run.sh
