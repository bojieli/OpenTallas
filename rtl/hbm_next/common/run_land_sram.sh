#!/usr/bin/env bash
set -eu
out=${1:?output};mkdir -p "$out"
for phase in -2 0 2; do
 for mut in 0 1 2; do
  key=p${phase}_m$mut
  "${VERILATOR:-verilator}" --binary -j 4 -Wno-fatal --top-module tb_hnx_pl_land_sram -GPHASE=$phase -GMUT=$mut \
   rtl/hbm_next/common/{ot_pl_land,hnx_pl_land_sram,tb_hnx_pl_land_sram}.sv \
   physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.v \
   -Mdir "$out/obj_$key" > "$out/build_$key.log" 2>&1
  set +e
  "$out/obj_$key/Vtb_hnx_pl_land_sram" > "$out/$key.log" 2>&1;rc=$?
  set -e
  if [ "$mut" = 0 ];then test "$rc" = 0;grep 'HNXLAND PASS' "$out/$key.log";
  else test "$rc" != 0;grep -E 'HNXLAND.*(FAIL|fault)' "$out/$key.log";fi
 done
done
