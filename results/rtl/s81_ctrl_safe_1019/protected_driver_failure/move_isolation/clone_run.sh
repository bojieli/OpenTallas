#!/bin/bash
set -euo pipefail
p=/srv/opentallas-scratch/claude/codex-s81-ctrl-driver-replay-clone
src=/srv/opentallas-scratch/claude/ref_gate/s81ctrl_rg2_sram-20261019-090615
if [ ! -e "$p/work/config.mk" ];then cp -a "$src/routes/gate/work/orfs" "$p/work";fi
# The original snapshot is mounted read-only. All replay outputs are separate.
docker run --rm -e LEC_CHECK=0 -v "$src/src":/src:ro -v "$p/work":/work -v "$p":/probe:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base PRE_CTS_TCL=/probe/pre_cts.tcl do-4_1_cts' > "$p/cts_clone.log" 2>&1
