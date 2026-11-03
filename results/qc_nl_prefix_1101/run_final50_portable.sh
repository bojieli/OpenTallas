#!/bin/bash
set -eu
r=$(cd "$(dirname "$0")" && pwd)
k=$r/kit
python3 "$r/guard.py"
trap 'sudo chown -R "$(id -u):$(id -g)" "$k"' EXIT
sudo docker run --rm --cpus 2 --memory 12g --memory-swap 12g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -eu
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/normal_mm_bootstrap.log 2>&1
python3 -I /work/input_selector.py
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/normal_mode_check.log 2>&1
HM=$(sed -n "s/^export OT_HOLD_FF_MARGIN = //p" /work/config.mk)
test "$HM" = 10
make HOLD_SLACK_MARGIN="$HM" DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-5_1_grt
' > "$r/final50.log" 2>&1
python3 "$k/final_check.py"
