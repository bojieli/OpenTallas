#!/bin/bash
set -uo pipefail
K=$1
python3 - "$K" <<'PY'
from pathlib import Path
import sys,json,hashlib
k=Path(sys.argv[1]);i=json.loads((k/'source_proof_identity.json').read_text());d=json.loads((k/'source_proof/lec.json').read_text());assert d['verdict']=='EQUIVALENT' and d['counts']['differs']==0 and d['counts']['undecided']==0
assert hashlib.sha256((k/'source_proof/lec.json').read_bytes()).hexdigest()==i['receipt_sha256']
for f,h in i['inputs_sha256'].items():assert hashlib.sha256((k/f).read_bytes()).hexdigest()==h,f
assert hashlib.sha256((k/'run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r1_1131/base/3_place.odb').read_bytes()).hexdigest()==i['corrected_odb_sha256']=='9e083b125cb3b1ba8029c46f71b0510bf279b99fce05bf1232f539af9e2487da'
assert not (k/'run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r1_1131/base/4_cts.odb').exists(),'fresh CTS output required'
PY
rc=$?; [ "$rc" = 0 ] || exit "$rc"
docker run --rm --name bksel-ab-r1N-canonical-mmcts-1557 --memory 8g --memory-swap 8g --cpus 8 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1; rc=$?; cat /work/orfs_hold_mm.log; [ "$rc" = 0 ] || exit "$rc"; python3 -I /work/kit_modes.py check /work --step cts --session "tc bc" --hold-repair; rc=$?; [ "$rc" = 0 ] || exit "$rc"; make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 HOLD_SLACK_MARGIN=10 cts > /work/cts_make_n.log 2>&1; rc=$?; [ "$rc" = 0 ] || exit "$rc"; if grep -E "flow/scripts/(synth|floorplan|global_place|detailed_place)\.tcl|scripts/3_[12345]" /work/cts_make_n.log; then echo FORBIDDEN_EARLIER_REBUILD;exit 91;fi; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 HOLD_SLACK_MARGIN=10 cts' > "$K/run_cts.log" 2>&1
rc=$?
printf 'cts_exit=%s at=%s\n' "$rc" "$(TZ=America/Los_Angeles date --iso-8601=seconds)" > "$K/cts.status"
exit "$rc"
