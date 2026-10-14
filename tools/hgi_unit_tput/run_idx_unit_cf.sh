#!/bin/bash
# CF-TOPK conformance of ot_hgi_idx_unit on the 4-outstanding VM model (hgi-1010/g): default reader and PREF=1, plus
# MUT 1 (ascending sort compares scores) on both -- must FAIL.   usage: run_idx_unit_cf.sh <out dir>  (from the repo root)
# k0 / k1 (el1013): TK2 1 on the default reader / on PREF 1 + TOPKW 1 + TWIW 8 (k <= 8 vectors run on ot_hgi_idx_tk2, k 512
# on the selected old path); k0m1 / k0m2 / k0m3: MUT_TK2 1 (order ranks scores) / 2 (ties to the higher index) / 3 (merge
# skips lane 3) -- must FAIL.
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"; VL=${VERILATOR:-verilator}
python3 tools/hgi_idx_unit_vectors.py "$out/vec" > "$out/gen.log"
src=(rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv rtl/hbm_accel/generic/idx/tb_hgi_idx_unit.sv
     rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv)
declare -A G=([p0]="-GPREF=0" [p1]="-GPREF=1" [p0m]="-GPREF=0 -GMUT=1" [p1m]="-GPREF=1 -GMUT=1" [w1]="-GPREF=1 -GTOPKW=1" [w0]="-GPREF=0 -GTOPKW=1" [w1m]="-GPREF=1 -GTOPKW=1 -GMUT=1" [x1]="-GPREF=1 -GTOPKW=1 -GTWIW=8" [x0]="-GPREF=0 -GTOPKW=1 -GTWIW=8" [x1m]="-GPREF=1 -GTOPKW=1 -GTWIW=8 -GMUT=1" [k0]="-GTK2=1" [k1]="-GTK2=1 -GPREF=1 -GTOPKW=1 -GTWIW=8" [k0m1]="-GTK2=1 -GMUT_TK2=1" [k0m2]="-GTK2=1 -GMUT_TK2=2" [k0m3]="-GTK2=1 -GMUT_TK2=3")
for v in p0 p1 p0m p1m w1 w0 w1m x1 x0 x1m k0 k1 k0m1 k0m2 k0m3; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style ${G[$v]} --top-module tb_hgi_idx_unit -Mdir "$out/$v.obj" -o sim "${src[@]}" > "$out/$v.build" 2>&1 &
done; wait
for v in p0 p1 p0m p1m w1 w0 w1m x1 x0 x1m k0 k1 k0m1 k0m2 k0m3; do "$out/$v.obj/sim" +DIR="$out/vec" > "$out/$v.log" 2>&1 || true; done
ok=1; for v in p0 p1 w1 w0 x1 x0 k0 k1; do grep -q "PASS HGI-IDX" "$out/$v.log" || ok=0; done; for v in p0m p1m w1m x1m k0m1 k0m2 k0m3; do grep -q "PASS HGI-IDX" "$out/$v.log" && ok=0; done
[ $ok = 1 ] && echo "IDX_UNIT_CF GATE PASS" | tee "$out/gate" || { echo "IDX_UNIT_CF GATE FAIL" | tee "$out/gate"; exit 1; }
