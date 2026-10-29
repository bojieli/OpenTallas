#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81-cores-resume1029
k=$r/kits/ot_s81sl_vq_planned_macro
sudo docker run --rm --name s81-vq-hold-eco1029 --cpus 4 --memory 16g --memory-swap 16g -v "$k":/work -v "$r/vq_hold_eco.tcl":/eco.tcl:ro -e OT_CORNER=FF -e OT_POSTCTS_GRT=1 -e ODB=/work/run/results/asap7/kl_ot_s81sl_vq_planned_macro/base/5_1_grt.odb -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /eco.tcl'
