#!/bin/bash
set -euo pipefail
export SRC="$PWD" OUT="$PWD/out" JOBS=8 REPLAY=slice/replay/replay CYCLES=10000
bash run_slice_vehicle.sh
python3 - <<'CHECK'
from pathlib import Path
s=Path('out/run.log').read_text()
assert 'SLICE_PASS' in s and 'SLICE_CHECK_FAIL' not in s, s[-3000:]
CHECK
