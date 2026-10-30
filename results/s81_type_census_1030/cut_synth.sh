#!/bin/bash
set -euo pipefail
k=/srv/opentallas-scratch2/claude/codex-s81types-1030/kv_cut
# Diagnostic mapped parent census only: no P&R, no view adoption.
docker run --rm --name codex_s81kv_cut1030 --cpus=8 --memory=48g --memory-swap=48g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 /work/run/results/asap7/dp_ot_s81sl_kv_leaf__t1/base/1_2_yosys.v' > "$k/synth.log" 2>&1
