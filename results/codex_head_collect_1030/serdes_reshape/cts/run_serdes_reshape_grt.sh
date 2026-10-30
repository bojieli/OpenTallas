#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape
K=$R/kit
python3 - "$K" <<'PY'
import json,sys
from pathlib import Path
for c in ('tt','ff'):
 x=json.load(open(Path(sys.argv[1])/('postcts_gate_'+c+'.json')))
 assert x['verdict']=='PASS',x
PY
mkdir -p "$R/grt"
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-serdes-reshape-grt-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -v "$R/grt":/out -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e;source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;cd /OpenROAD-flow-scripts/flow
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /out/hold_patch.log 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /out/modes.log 2>&1
set +e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt HOLD_SLACK_MARGIN=10 > /out/run_grt.log 2>&1
rc=$?;echo $rc > /out/grt.rc
chown -R $HUID:$HGID /work /out
exit $rc'
