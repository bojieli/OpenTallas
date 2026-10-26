#!/usr/bin/env bash
# Candidate common833 FULL lane component programme; execute via ot-run.
set -euo pipefail
repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
out=$(realpath -m "${1:?fresh output directory}")
test ! -e "$out"
mkdir -p "$out/source"
cd "$repo"
python3 tools/hbm_static/su_arith_compile.py "$out/vec" > "$out/vec.log"
python3 - "$repo" "$out/source" <<'PY'
from pathlib import Path
import sys
root,out=map(Path,sys.argv[1:])
p=root/'rtl/hbm_accel/generic/adapters/static_su/arithmetic'
s=(p/'ot_hbm_su_static_kind2_lat4_leaf1_physical.sv').read_text()
s=s.replace('ot_hbm_su_static_kind2_lat4_leaf1_physical','ot_hbm_su_static_full_f12_candidate').replace('.ALAT(3)', '.ALAT(4)')
(out/'full.sv').write_text(s)
s=(p/'tb_su_static_lane_leaf.sv').read_text().replace('always #5 clk=~clk;', 'always #0.4165 clk=~clk;')
# Same compiled 64 fixed issues in every baseline class. High QID is VM identity,
# while the physical source explicitly selects FULL arithmetic independently.
s=s.replace('`timescale 1ns/1ps','`timescale 1ns/1fs')
(out/'tb.sv').write_text(s)
PY
S=rtl/hbm_accel/generic/adapters/static_su
src=("$out/source/tb.sv" "$out/source/full.sv" "$S/arithmetic/ot_hbm_su_static_lane_pinreg.sv" "$S/arithmetic/ot_hbm_su_static_lane.sv" "$S/arithmetic/ot_hbm_su_static_ins.sv"
 "$S/data_store/ot_hbm_su_static_pinned_bank.sv" "$S/data_store/ot_hbm_su_static_data_store.sv"
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
verilator --binary --timing -O1 -j "${CPUS:-4}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_su_static_lane_leaf +define+LEAF_TOP=ot_hbm_su_static_full_f12_candidate \
 -GMLAT=4 -GALAT=4 -GLEAF=1 -GLANE=256 -GPINREG=1 --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
bin="$out/obj/Vtb_su_static_lane_leaf"
"$bin" +DIR="$out/vec" > "$out/run.log" 2>&1
for mut in ADDR DATA PHASE; do
 set +e
 "$bin" +DIR="$out/vec" +MUT_"$mut" > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
done
cat "$out/run.log"
echo FULL_F12_LANE_COMPONENT_PASS
