#!/bin/bash
set -u
cd "$SRC"
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
export OT_ORFS_NUM_CORES=4 NUM_CORES=4
# Distinct full91FF boot composition; do not reuse or overwrite r4 collar-only.
/srv/opentallas-scratch/admit.sh 8 -- python3 tools/run_abi3_physical.py \
 --view asap7 --top ot_hbm_production_clock_digital_body \
 --source rtl/hbm_accel/control/ot_hbm_production_clock_digital_body.sv \
 --source rtl/hbm_accel/control/ot_hbm_clock_reset_boundary.sv \
 --source rtl/hbm_accel/control/ot_hbm_reset_seq.sv \
 --clock-port clk_stream --clock-period-ns 0.833333333 \
 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --sdc-append physical/hbm_accel_die_views/clock_boundary/production_body.sdc \
 --orfs-corner TC --hold-corners TC,BC --stages pnr \
 --die-area 0 0 100.224 99.36 --core-area 0 0.54 100.224 98.82 \
 --place-density 0.55 --routing-layers M2 M7 \
 --orfs-var ADDER_MAP_FILE= --orfs-var 'CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none' \
 --slew-margin-percent 60 --hold-margin-ns 0.010 \
 --purpose characterization --nickname-tag ta15_production_boot \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$OUT/work" --output "$OUT/physical.json" > "$OUT/route.log" 2>&1
status=$?
printf '%s\n' "$status" > "$OUT/route.exit"
if [ "$status" = 0 ]; then
 /srv/opentallas-scratch/admit.sh 4 -- python3 tools/w18/corner_sta.py \
  --orfs-dir "$OUT/work/orfs" --output "$OUT/corner_sta.json" > "$OUT/corner.log" 2>&1
 printf '%s\n' "$?" > "$OUT/corner.exit"
fi
