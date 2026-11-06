#!/bin/bash
# KV-ING-5 vF: vE kit + cut 19 (st_wa_r carry-select, spliced netlist) + registered reset fan-out (OT_RESET_REPLICA_LOADS=64).
# Same steps as Codex run_vE2.sh + resume_vE_ff.sh (FF-frame GRT hold margin 10), from the spliced 1_2_yosys.v.
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
exec docker run --rm --name kving5-vF --memory=32g --memory-swap=32g --cpus=8 -e HUID=$(id -u) -e HGID=$(id -g) -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap "chown -R $HUID:$HGID /work" EXIT
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics_vF.log 2>&1
python3 -c "import runpy,pathlib; m=runpy.run_path(\"/work/orfs_hold_mm.py\"); print(m[\"patch_final_dpl\"](pathlib.Path(\"/OpenROAD-flow-scripts/flow/scripts\")))"
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
B=/work/run/results/asap7/hc_qkd_hr_ingest_eng__362_88x362_88/base
cp /work/constraint.sdc $B/1_2_yosys.sdc
$M do-1_synth
printf "read_db %s\nwrite_verilog /work/1_synth_odb.v\n" $B/1_synth.odb > /work/synth_odb_v.tcl
openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1 || true
$M do-floorplan
$M do-place
$M do-cts
OT_VCLK_CORNER=ff $M do-5_1_grt HOLD_SLACK_MARGIN=10
$M do-5_2_route do-5_3_fillcell do-5_route
cp "$B/5_1_grt.sdc" "$B/5_route.sdc"
$M do-finish
echo VF_FLOW_DONE
'
