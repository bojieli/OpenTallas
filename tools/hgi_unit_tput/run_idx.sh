#!/bin/bash
# IDX unit throughput bench (hgi-1010/g): tools/hgi_unit_tput/run_idx.sh <vectors dir> <out dir>   (from the repo root)
# variants: m0 (PASS) / m1 (MUT 1, FAIL) on the default reader; p0 (PREF 1, PASS) / p1 (PREF 1 + MUT 1, FAIL) /
# p2 (PREF 1 + MUT_PREF 1, FAIL) on the opt-in streaming reader.
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
src=(rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv
     rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv
     rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/hbm_accel/generic/idx/tb_hgi_idx_tput.sv)
declare -A G=([m0]="-GMUT=0" [m1]="-GMUT=1" [p0]="-GPREF=1" [p1]="-GPREF=1 -GMUT=1" [p2]="-GPREF=1 -GMUT_PREF=1")
for v in m0 m1 p0 p1 p2; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style ${G[$v]} --top-module tb_hgi_idx_tput \
    -Mdir "$out/$v.obj" -o sim "${src[@]}" > "$out/$v.build" 2>&1 &
done
wait
for v in m0 m1 p0 p1 p2; do "$out/$v.obj/sim" +DIR="$vec" > "$out/$v.log" 2>&1 || true; done
ok=1
for v in m0 p0; do grep -q "PASS HGI_IDX_TPUT" "$out/$v.log" || ok=0; done
for v in m1 p1 p2; do grep -q "PASS HGI_IDX_TPUT" "$out/$v.log" && ok=0; done
[ $ok = 1 ] && echo "IDX_TPUT GATE PASS (m0/p0 PASS, m1/p1/p2 FAIL)" | tee "$out/gate" || { echo "IDX_TPUT GATE FAIL" | tee "$out/gate"; exit 1; }
