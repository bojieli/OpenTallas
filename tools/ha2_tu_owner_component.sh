#!/bin/bash
# Remote only, source tree is pinned clean before invoking this script.
set -eu
out=$1
mkdir -p "$out"
common=(rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce.sv
 rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_runtime.sv rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_adapter.sv
 rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv rtl/link/ot_link_afifo.sv
 rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_owner.sv)
rc=0
for bench in tb_ha2_tu_owner_adapter tb_ha2_tu_owner_parent; do
 if iverilog -g2012 -s "$bench" -o "$out/$bench.vvp" "${common[@]}" "rtl/hbm_accel/ha2_ar/$bench.sv" >"$out/$bench.compile.log" 2>&1; then
   vvp "$out/$bench.vvp" >"$out/$bench.log" 2>&1 || rc=$?
 else rc=$?; fi
 if [ "$rc" != 0 ]; then break; fi
done
printf '%s\n' "$rc" >"$out/exit"
exit "$rc"
