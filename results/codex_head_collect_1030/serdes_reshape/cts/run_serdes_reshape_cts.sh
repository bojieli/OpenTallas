#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape
K=$R/kit
mkdir -p "$R/cts"
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-serdes-reshape-cts-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -v "$R/cts":/out -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e;source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;cd /OpenROAD-flow-scripts/flow
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /out/hold_patch.log 2>&1
python3 -I /work/kit_modes.py check /work --step cts --session "tc bc" --hold-repair > /out/modes.log 2>&1
set +e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts > /out/run_cts.log 2>&1
rc=$?;echo $rc > /out/cts.rc
chown -R $HUID:$HGID /work /out
exit $rc'
