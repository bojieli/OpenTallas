#!/bin/bash
# CLAUDE S81-RERUN (owner MARGIN-FIRST): ot_dsrom_su_swiglu_lane IREG = 1 (pin registers on every input, fault OR
# registered at its pin), ROUTED = 1, IO TIMED (no --false-path-io), routed over-constrained at 0.770 ns (sign-off at
# 0.833333 with tools/w18/corner_sta.py), IO delay 0.26 T = 200 ps (150 ps die clock-arrival term + 50 ps wire).
# One variant.  usage: WT=<source tree> J=<job dir> launch.sh
set -e
: "${WT:?source tree}" "${J:?job dir}"
mkdir -p $J; cd $WT
exec python3 tools/run_abi3_physical.py --view asap7 --clock-period-ns 0.770 --clock-uncertainty-ns 0.06 \
 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.26 --stages pnr \
 --core-utilization 35 --place-density 0.55 --hold-margin-ns 0.015 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 \
 --orfs-var REMOVE_ABC_BUFFERS=1 --force --top ot_dsrom_su_swiglu_lane \
 --source rtl/hdc/v41x/ot_dsrom_su_swiglu.sv --source rtl/hdc/v41x/ot_dsrom_su_f12.sv --source rtl/hdc/v41x/ot_dsrom_su_add6.sv \
 --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fpu.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fastfp_lat_f12.sv \
 --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/ot_hdc_prefix.sv \
 --param LM=5 --param LA=4 --param ROUTED=1 --param IREG=1 \
 --output $J/physical.json --keep-workdir $J/work --nickname-tag swiglu_lane_ireg_m770 > $J/launch.log 2>&1
