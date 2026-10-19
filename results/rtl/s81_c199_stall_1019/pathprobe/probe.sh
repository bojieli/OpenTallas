#!/bin/bash
set -euo pipefail
lane=/srv/opentallas-scratch/claude/codex-s81-c199-pathprobe
original=/srv/opentallas-scratch/claude/ref_gate/s81sf_bfcol_c199r-20261019-072007
if [ ! -e "$lane/work/config.mk" ];then cp -a --reflink=auto "$original/routes/gate/work/orfs" "$lane/work";fi
docker run --rm -e LEC_CHECK=0 -v "$original/src":/src:ro -v "$lane/work":/work -v "$lane":/probe:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base PRE_CTS_TCL=/probe/pre_cts_probe.tcl do-4_1_cts' > "$lane/cts_probe.log" 2>&1
