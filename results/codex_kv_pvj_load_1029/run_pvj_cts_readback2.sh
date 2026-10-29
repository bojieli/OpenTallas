#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-pvj-load-1029/kits/ot_qwen_tp8_pv_join_t__172.8x172.8
docker run --rm --name codex-pvj-cts-readback-1029 --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_cts.log 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 run RUN_SCRIPT=/work/pvj_cts_readback2.tcl RUN_LOG_NAME_STEM=4_cts_readback2' > "$K/run_cts_readback2.log" 2>&1
