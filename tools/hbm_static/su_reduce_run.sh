#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
python3 tools/hbm_static/su_reduce_compile.py "$OUT/base"
python3 tools/hbm_static/su_reduce_compile.py "$OUT/wrongtree" --wrong-tree
verilator --cc --exe --build -j 1 -Wno-fatal --top-module ot_hbm_su_reduce_static --Mdir "$OUT/obj" \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 "$(pwd)/tools/hbm_static/su_reduce_tb.cpp" > "$OUT/build.log" 2>&1
"$OUT/obj/Vot_hbm_su_reduce_static" "$OUT/base" > "$OUT/base.log" 2>&1
for mut in identity phase wrongtree;do
 set +e
 dir=base
 if [ "$mut" = wrongtree ];then dir=wrongtree;fi
 "$OUT/obj/Vot_hbm_su_reduce_static" "$OUT/$dir" "$mut" > "$OUT/$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q FAIL "$OUT/$mut.log";then exit 1;fi
 printf '%s\n' "$rc" > "$OUT/$mut.exit"
done
"$OUT/obj/Vot_hbm_su_reduce_static" "$OUT/base" poison_max > "$OUT/finite_fault.log" 2>&1
cat "$OUT/base.log"
echo 'SU_REDUCE SUITE PASS'
