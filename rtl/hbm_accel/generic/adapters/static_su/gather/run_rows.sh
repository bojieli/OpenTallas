#!/usr/bin/env bash
# H-MTP2/sudma: P-row indexed scalar gather bench: MUT 0 must pass, MUT 1..3 must fail the exact comparison.
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
OUT=$(realpath -m "$1");mkdir -p "$OUT"
for m in 0 1 2 3;do
 verilator --binary --timing -j 1 -Wno-fatal --top-module tb_indexed_scalar_rows -GMUT=$m -Mdir "$OUT/obj$m" rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar_rows.sv rtl/hbm_accel/generic/adapters/static_su/gather/tb_indexed_scalar_rows.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build$m.log" 2>&1
 set +e
 "$OUT/obj$m/Vtb_indexed_scalar_rows" > "$OUT/run$m.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$OUT/run$m.exit"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'GATHER_ROWS FAIL' "$OUT/run$m.log";fi
 grep -E "GATHER_ROWS|ERR|variable" "$OUT/run$m.log" | head -4
done
echo ALL_OK
