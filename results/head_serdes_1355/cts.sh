#!/bin/bash
set -euo pipefail
R=$(cd -- "$(dirname -- "$0")" && pwd)
K="$R/kit"
python3 - "$K" <<'PY'
import json,sys
from pathlib import Path
k=Path(sys.argv[1]);d=json.loads((k/"lec/lec.json").read_text());assert d["verdict"]=="EQUIVALENT",d["verdict"]
assert (k/"run/results/asap7/hbc_ot_s81_kp4_dchn/base/3_place.odb").exists()
assert not (k/"FAIL_PREFLOOR").exists()
PY
docker run --rm --name codex-head-serdes-1355-cts --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set -e; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts' > "$R/cts.log" 2>&1
