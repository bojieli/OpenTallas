#!/bin/bash
# IDX.TOPK tk2 gate (el1013 redesign-idx): everything that qualifies ot_hgi_idx_tk2 behaviourally, in one command.
#   usage (repo root): tools/hgi_unit_tput/run_idx_tk2.sh OUT
#   1 production throughput gate  run_idx.sh         (t0 PASS exact + cycles, t1 / t2 mutants FAIL, old variants unchanged)
#   2 CF-TOPK conformance         run_idx_unit_cf.sh (k0 / k1 PASS, k0m1 / k0m2 / k0m3 FAIL)
#   3 directed random             idx_tk2_vectors.py 96 vectors: r0 (TK2 1) PASS, r1 / r2 / r3 (MUT_TK2 1 / 2 / 3) FAIL
# Exit status 0 only if all three hold (a build that fails is a gate failure, never a silent pass).
set -uo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"; VL=${VERILATOR:-verilator}; PY=${PYTHON:-python3}
rc=0
$PY tools/hgi_unit_tput/idx_vectors.py --out "$out/vec" > "$out/vec.log" 2>&1 || { echo "TK2 GATE FAIL: tput vectors"; exit 1; }
bash tools/hgi_unit_tput/run_idx.sh "$out/vec" "$out/tput" || rc=1
bash tools/hgi_unit_tput/run_idx_unit_cf.sh "$out/cf" || rc=1
$PY tools/hgi_unit_tput/idx_tk2_vectors.py "$out/rvec" 96 > "$out/rvec.log" 2>&1 || { echo "TK2 GATE FAIL: random vectors"; exit 1; }
src=(rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv rtl/hbm_accel/generic/idx/tb_hgi_idx_unit.sv
     rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv)
for mu in 0 1 2 3; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -GTK2=1 -GMUT_TK2=$mu --top-module tb_hgi_idx_unit \
    -Mdir "$out/r$mu.obj" -o sim "${src[@]}" > "$out/r$mu.build" 2>&1 &
done; wait
for mu in 0 1 2 3; do
  if [ -x "$out/r$mu.obj/sim" ]; then timeout 600 "$out/r$mu.obj/sim" +DIR="$out/rvec" > "$out/r$mu.log" 2>&1 || true
  else echo "BUILD FAILED" > "$out/r$mu.log"; rc=1; fi
done
grep -q "PASS HGI-IDX" "$out/r0.log" || rc=1
for mu in 1 2 3; do grep -q "PASS HGI-IDX" "$out/r$mu.log" && rc=1; grep -q "BUILD FAILED" "$out/r$mu.log" && rc=1; done
{ echo "tput: $(cat "$out/tput/gate" 2>/dev/null)"; echo "cf: $(cat "$out/cf/gate" 2>/dev/null)"
  for mu in 0 1 2 3; do echo "random MUT_TK2=$mu: $(grep -E 'PASS HGI-IDX|FAIL|FATAL' "$out/r$mu.log" | tail -1)"; done
  grep -h "^TPUT" "$out/tput/t0.log" 2>/dev/null; } > "$out/SUMMARY"
cat "$out/SUMMARY"
[ $rc = 0 ] && echo "IDX_TK2 GATE PASS" | tee "$out/gate" || { echo "IDX_TK2 GATE FAIL" | tee "$out/gate"; exit 1; }
