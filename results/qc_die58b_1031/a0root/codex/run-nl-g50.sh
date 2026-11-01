#!/bin/bash
set -eu
k=/srv/opentallas-scratch2/claude/codex-qca0/nl-b3-g50
sudo docker run --rm --cpus 2 --memory 24g --memory-swap 24g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/mm_patch.log 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-5_1_grt' > "$k/g50.log" 2>&1
