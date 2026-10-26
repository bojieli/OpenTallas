#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
R=$(git rev-parse --show-toplevel);cd "$R"
S=physical/die_plan/hbm/bind/r18h5_bundle/rtl
for m in 0 2;do
 verilator --binary --timing -Wno-fatal --top-module tb_vmstat_obs -GMUT=$m \
  "$S/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" "$S/lib/ot_rst_relay.sv" \
  rtl/test/hbm_vmstat_obs/tb_vmstat_obs.sv --Mdir "$OUT/obj$m" -o tb > "$OUT/build$m.log" 2>&1
 if "$OUT/obj$m/tb" > "$OUT/run$m.log" 2>&1;then rc=0;else rc=$?;fi
 if [ "$m" = 0 ];then test "$rc" = 0;grep 'VMSTAT_OBS PASS' "$OUT/run$m.log";else test "$rc" != 0;grep 'VMSTAT_OBS FAIL' "$OUT/run$m.log";echo 'VMSTAT_OBS mutant dropped bit143 CAUGHT';fi
done
