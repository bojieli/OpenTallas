#!/bin/bash
# Fleet only. Compile first with compile_layers.sh ROOT TREE FIX OUT.
# CUT_ROOT contains cuts/cut_* and cuts/K_cut_* from prep_cuts.sh.
# Optional KIT_ROOT contains K_cut_* (for kits staged separately).
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
exec python3 "$H/run_layers.py" "$@"
