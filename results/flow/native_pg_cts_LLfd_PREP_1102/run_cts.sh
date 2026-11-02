#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-cts-0219/cts_pg0_0253
K=$R/kit
B=$K/run/results/asap7/kl_dsfd_node_LLfd_c/base
EXPECTED=9a3294019241dbf4d52c284a6682f9a11978241f15c6451bb8e5751fecd480e1
python3 - "$R" "$EXPECTED" <<'PY'
from pathlib import Path
import json,sys
r=Path(sys.argv[1]);copy=json.loads((r/'INPUT_PG_COPY.json').read_text());audit=json.loads((r/'INPUT_SAVED_PG_AUDIT.json').read_text())
assert copy['output_sha256']==sys.argv[2]
assert copy['preserved_before']==copy['preserved_after']
assert audit['status']=='PASS' and audit['checked']==17802 and audit['failure_count']==0 and audit['mapping_error']==''
PY
[ "$(sha256sum "$B/3_place.odb" | cut -d' ' -f1)" = "$EXPECTED" ]
[ ! -e "$B/4_cts.odb" ] && [ ! -e "$B/4_1_cts.odb" ]
docker run --rm --network none --memory=8g --memory-swap=8g --cpus=2 -v "$K":/work -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1; python3 -I /work/native_pg_birth_wrap_runtime.py /OpenROAD-flow-scripts/flow/scripts --stage cts --driver /work/native_pg_birth_cts_driver.tcl; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-4_1_cts' > "$R/run_cts.log" 2>&1
[ "$(sha256sum "$B/3_place.odb" | cut -d' ' -f1)" = "$EXPECTED" ]
test -s "$B/4_1_cts.odb"
