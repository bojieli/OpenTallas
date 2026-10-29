#!/bin/bash
# Same-synth HNX successor, existing data-only CTS hold mechanism.
set -euo pipefail
K=$(cd "$(dirname "$0")/kit" && pwd)
R=$K/run/results/asap7/hbc_hnx_lane_x/base
mkdir -p "$K/inherited_cts"
for f in "$R"/4*; do [ ! -e "$f" ] || mv "$f" "$K/inherited_cts/"; done
cp "$K/3_place_anchor.odb" "$R/3_place.odb"
python3 - "$K/config.mk" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
assert 'override export OT_IO_HOLD_PAD = 1' not in s
p.write_text(s+'\n# Coordinator approved one data-only same-synth trial 2026-10-29.\noverride export OT_IO_HOLD_PAD = 1\n')
PY
docker run --rm --name codex-hnx-iopad-0310 --cpus 16 --memory 32g --memory-swap 32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_iopad.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 cts > /work/run_cts_iopad.log 2>&1
'
