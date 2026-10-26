#!/bin/bash
# Run through ot-run. This runner permits exactly the reviewed CTS stage, never route.
set -euo pipefail
K=${1:?kit directory}
HERE=$(cd "$(dirname "$0")" && pwd)
python3 "$HERE/guard.py" "$K"
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
TEMP_RUNNER=$(mktemp "$K/../cts_runner.XXXXXX.sh")
python3 - "$ROOT" "$TEMP_RUNNER" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tools/die_plan'))
import gen_phys
Path(sys.argv[2]).write_text(gen_phys.RUN_KIT)
PY
bash "$TEMP_RUNNER" "$K" cts 24 8
