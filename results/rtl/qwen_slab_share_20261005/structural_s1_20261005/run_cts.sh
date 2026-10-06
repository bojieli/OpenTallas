#!/bin/bash
# run_cts.sh <old|new>: ORFS do-4_1_cts on Codex twoface_570's placed design with that SDC (src read-only)
set -u
S=/srv/opentallas-scratch/claude/qwen-slab-ctx; W=$S/cts_$1
SRC=/srv/opentallas-scratch/codex/ampere-qwen-slab-fanout-20261005/src
docker run --rm --name qss_ctx_$1 -v $SRC:/src:ro -v $W:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base $( [ $1 = new ] && echo PRE_CTS_TCL=/work/pre_cts.tcl ) do-4_1_cts > /work/cts_make.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $W/cts.exit
