#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-mesh-2249
K=$R/hd_mesh_e
docker run --rm --name codex-head-mesh-r4-2249 --memory=32g --memory-swap=32g --cpus=8 \
  -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow \
  openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair
openroad -no_init -exit /work/pin_eco.tcl > /work/pin_eco.log 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
$M grt HOLD_SLACK_MARGIN=10
O=/work/run/results/asap7/dp_hd_mesh_e/base/5_1_grt.odb
for C in TT FF; do
 OT_POSTCTS_GRT=1 OT_CORNER=$C ODB=$O openroad -no_init -exit /work/postcts_gate.tcl > /work/postcts_gate_$C.log 2>&1
 grep -q "OT_POSTCTS_GATE.*PASS" /work/postcts_gate_$C.log
done
$M route
$M do-finish
$M do-generate_abstract
chown -R "$HUID:$HGID" /work
' > "$R/run_r4.log" 2>&1
python3 "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff_r4" --docker docker
