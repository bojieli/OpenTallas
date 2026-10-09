#!/bin/bash
# Standalone TT characterization. Generic20%IO does not establish die budgets.
# Run only on an admitted remote host from a pinned source snapshot.
set -euo pipefail
W=$1; SRC=${SRC:-$(pwd)}; mkdir -p "$W"; cd "$SRC"
export OT_ORFS_NUM_CORES=${CORES:-4} NUM_CORES=${CORES:-4}
python3 tools/run_abi3_physical.py --view asap7 --top dsfd_sp_hc_cmd_bridge_pf \
 --source physical/s81_ctrl/rtl/dsfd_sp_hc_cmd_bridge_pf.sv \
 --source rtl/dsrom_sys/s81_ctrl/ot_s81_hc_cmd_bridge.sv \
 --clock-port clk --clock-period-ns 0.833 --clock-uncertainty-ns 0.060 \
 --clock-uncertainty-hold-ns 0.025 --orfs-corner TC --hold-corners TC,BC \
 --io-delay-fraction 0.2 --stages synth,pnr --core-utilization 45 --place-density 0.55 \
 --routing-layers M2 M7 --orfs-var ADDER_MAP_FILE= \
 --orfs-var 'CTS_ARGS=-sink_clustering_enable -repair_clock_nets -apply_ndr none' \
 --hold-margin-ns 0.025 --purpose characterization --nickname-tag hc_native_pf \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$W/work" --force --output "$W/physical.json" > "$W/run.log" 2>&1
python3 tools/w18/corner_sta.py --orfs-dir "$W/work/orfs" --output "$W/corner_sta.json" > "$W/corner.log" 2>&1
