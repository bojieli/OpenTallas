#!/bin/bash
# Component route of the actual installed owner's 545-bit TU boundary.
# Full PF384 capacity; never a PF64 or enclosing shared8 qualification claim.
set -eu
util=$1
out=$2
mkdir -p "$out"
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited OT_ORFS_NUM_CORES=16
export MAKEFLAGS=-j16
rc=0
python3 tools/run_abi3_physical.py --view asap7 --top ot_ha2_tu_owner_adapter \
 --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
 --source rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv \
 --source rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_runtime.sv \
 --source rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_adapter.sv \
 --param NC=8 --param NOG=8 --param PFMAX=384 --param NPT=8 --param INJ=2 \
 --param LANES=16 --param BF16=1 --param LAT=7 --param SLOTREG=1 \
 --clock-period-ns .833 --clock-uncertainty-ns .06 --clock-uncertainty-hold-ns .025 \
 --io-delay-fraction .2 --orfs-corner WC --hold-corners WC,BC \
 --core-utilization "$util" --place-density .55 --hold-margin-ns .01 --slew-margin-percent 30 \
 --orfs-var ADDER_MAP_FILE= --purpose signoff_target --stages synth,pnr \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --nickname-tag "ha2_tu_owner_pf384_u$util" --keep-workdir "$out/work" \
 --output "$out/physical.json" >"$out/run.log" 2>&1 || rc=$?
printf '%s\n' "$rc" >"$out/exit"
exit "$rc"
