#!/bin/bash
set -euo pipefail
out=$1
export OT_ORFS_NUM_CORES=8 NUM_CORES=8
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl'
# Characterization only; actual registered receive/seed endpoints and clock
# budgets remain pending. Use the actual three-macro protected join.
python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_hc_seed_join \
 --source rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv \
 --source rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv \
 --macro-view ot_sram_1r1w_256x256_m2_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2 \
 --macro-place-halo 5 5 --clock-port clk --clock-period-ns 0.833333 \
 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner TC --hold-corners TC,BC --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 500 500 --core-area 5 5 495 495 --place-density 0.55 \
 --routing-layers M2 M7 --orfs-var ADDER_MAP_FILE= --hold-margin-ns 0.025 \
 --purpose characterization --nickname-tag dsrom_hc_join_native \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$out/work" --output "$out/physical.json"
