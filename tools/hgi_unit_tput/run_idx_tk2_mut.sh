#!/bin/bash
# IDX.TOPK tk2 MUTANT bench (el1013 redesign-idx): the production throughput vectors on ot_hgi_idx_tk2 with MUT_TK2 = 1
# (the ascending-id order ranks by score).  Must print "HGI_IDX_TPUT FAIL <n>"; a build failure prints BUILD FAILED and
# exits 2 (so it is never mistaken for the mutant being killed).
#   usage (repo root): tools/hgi_unit_tput/run_idx_tk2_mut.sh OUT [MUT_TK2=1]
set -uo pipefail
out=$(realpath -m "$1"); mu=${2:-1}; mkdir -p "$out"; VL=${VERILATOR:-verilator}; PY=${PYTHON:-python3}
$PY tools/hgi_unit_tput/idx_vectors.py --out "$out/vec" > "$out/vec.log" 2>&1 || { echo "BUILD FAILED: vectors"; exit 2; }
src=(rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv
     rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/hbm_accel/generic/idx/tb_hgi_idx_tput.sv
     rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_heap.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv)
"$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -GTK2=1 -GMUT_TK2=$mu --top-module tb_hgi_idx_tput \
  -Mdir "$out/obj" -o sim "${src[@]}" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; echo "BUILD FAILED"; exit 2; }
timeout 1200 "$out/obj/sim" +DIR="$out/vec" > "$out/run.log" 2>&1 || true
grep -E "HGI_IDX_TPUT" "$out/run.log" | tail -1
grep -q "PASS HGI_IDX_TPUT" "$out/run.log" && exit 0
grep -q "HGI_IDX_TPUT FAIL" "$out/run.log" && exit 1
echo "BUILD FAILED: no verdict"; exit 2
