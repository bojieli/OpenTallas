#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pc-geo80-1102
D=$R/repair
python3 - "$R" <<'PY'
from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);d=r/'repair';rec=json.loads((d/'PC_GEO80_PREPARED.json').read_text());b='run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/'
assert hashlib.sha256((d/'original_route.odb').read_bytes()).hexdigest()==rec['source_hashes'][b+'5_2_route.odb']
for rel in ('constraint.sdc',b+'6_final.spef',b+'4_1_cts.odb',b+'1_2_yosys.v'):
 assert hashlib.sha256((d/rel).read_bytes()).hexdigest()==rec['source_hashes'][rel],rel
for n in ('prd_targeted.tcl','prd_hook_checkpoint.tcl'):
 assert hashlib.sha256((r/'prep'/n).read_bytes()).hexdigest()==json.loads((r/'prep/PREP.json').read_text())['files'][n]
assert (d/'prd_targeted.tcl').read_bytes()==(r/'prep/prd_targeted.tcl').read_bytes()
assert (d/'prd_hook.tcl').read_bytes()==(r/'prep/prd_hook_checkpoint.tcl').read_bytes()
assert not (r/'DISPATCH_STARTED').exists()
(r/'DISPATCH_STARTED').touch()
PY
. "$D/variant.env"
export OT_MAX_FANOUT OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF OT_PRD_FROM OT_PRD_TARGETED OT_PRD_MAX_WIRE_LENGTH
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-geo80-repair-1102 --cpus=8 --memory=16g --memory-swap=16g -v "$D":/work -e OT_MAX_FANOUT -e OT_SLEW_MARGIN -e OT_SETUP_MARGIN -e OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP -e OT_HOLD_MAXBUF -e OT_PRD_FROM -e OT_PRD_TARGETED -e OT_PRD_MAX_WIRE_LENGTH -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1' > "$D/repair_phase.log" 2>&1
$DK run --rm -v "$D":/work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 chown -R "$(id -u):$(id -g)" /work
[ -s "$D/repair_checkpoint.odb" ] && [ -s "$D/REPAIR_CHECKPOINT" ] || exit 10
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$D/repair_checkpoint.clock.tsv" --json "$D/repair_checkpoint.clock_diff.json"
printf 'REPAIR_CHECKPOINT_READY_UNQUALIFIED_GRT\n' > "$D/RESULT"
