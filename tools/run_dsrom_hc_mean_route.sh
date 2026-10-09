#!/bin/bash
set -euo pipefail
out=$1
export OT_ORFS_NUM_CORES=12 NUM_CORES=12
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl'
# Characterization only. Actual H VM and seed placement/arrival budgets are
# pending: generic IO fractions cannot qualify the parent token path.
python3 tools/run_abi3_physical.py --view asap7 --top ot_dsrom_hc_mean_capture \
 --param SINGLE_CAPTURE=1 \
 --source rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv \
 --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fastfp.sv \
 --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv \
 --source rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv \
 --macro-view ot_sram_1r1w_256x256_m2_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2 \
 --macro-place-halo 5 5 --clock-port clk --clock-period-ns 0.833333 \
 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner TC --hold-corners TC,BC --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 1000 1000 --core-area 5 5 995 995 --place-density 0.55 \
 --routing-layers M2 M7 --orfs-var ADDER_MAP_FILE= --hold-margin-ns 0.025 \
 --purpose characterization --nickname-tag dsrom_hc_mean_native \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$out/work" --output "$out/physical.json"
