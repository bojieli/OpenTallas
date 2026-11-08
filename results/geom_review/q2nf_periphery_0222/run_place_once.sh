#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-q2nf-0222/kit_periphery_vC
R=/srv/opentallas-scratch2/claude/codex-q2nf-0222
python3 -I - <<'PY'
from pathlib import Path
import json
r=Path('/srv/opentallas-scratch2/claude/codex-q2nf-0222');p=json.loads((r/'parity_probe/compare_result.json').read_text());assert p['counts']=={'proved':55722} and not p['unproved']
k=r/'kit_periphery_vC';assert all((k/n).exists()for n in['HOLD_CTS','HOLD_ROUTE','DO_NOT_COUNT','PLACE_ONLY']);d=json.loads((k/'SOURCE_REUSE.json').read_text());assert d['new_pin_cycles']==0
PY
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-q2nf-periphery-place-0222 --memory=32g --memory-swap=32g --cpus=8 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
trap '\''rc=$?; chown -R 1000:1000 /work; exit $rc'\'' EXIT
if grep -q "^override export OT_HOLD_MM = 1" /work/config.mk;then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1;fi
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8)
"${M[@]}" do-floorplan > /work/run_floorplan_candidate.log 2>&1
"${M[@]}" do-place > /work/run_place_candidate.log 2>&1
bash /work/layout_render_hook.sh 3_5_place_dp 0
printf "%s\n" "PLACE complete; CTS/GRT/route/count remain HELD" > /work/PLACE_DONE.txt
'
