#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
OUT=$(realpath -m "$1");mkdir -p "$OUT"
for m in 0 1 2 3;do
 verilator --binary --timing -j 1 -Wno-fatal --top-module tb_indexed_scalar -GMUT=$m -Mdir "$OUT/obj$m" rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar.sv rtl/hbm_accel/generic/adapters/static_su/gather/tb_indexed_scalar.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build$m.log" 2>&1
 set +e
 "$OUT/obj$m/Vtb_indexed_scalar" > "$OUT/run$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$OUT/run$m.exit"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'GATHER_NATIVE FAIL' "$OUT/run$m.log";fi
 cat "$OUT/run$m.log" | tail -3
done
