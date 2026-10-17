#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
for m in 0 1;do
 iverilog -g2012 -s tb -Ptb.MUT=$m -o "$out/m$m.vvp" "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pin_skid2_h9.sv" "$d/tb_hbm_pc_h9_skid_equiv.sv" > "$out/m$m.build.log" 2>&1
 if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1;then
  test "$m" = 0 || { echo H9_SKID_MUTANT_SURVIVED;exit 1; }
  grep 'H9_SKID_EQUIV PASS' "$out/m$m.log"
 else
  test "$m" = 1 || { cat "$out/m$m.log";exit 1; }
  grep 'H9_SKID_MISMATCH' "$out/m$m.log"
  echo H9_SKID_MUTANT_REJECTED
 fi
done
