#!/bin/bash
# HH-6 / HBM-SURED 10-18: SU reducer pre-tree bench on Verilator 5.050 (the closure daemon's version).
# usage: su_pretree_run.sh OUT [MUT]   (MUT 0 PASS; 1,3,4 pretree_s, 512 late operand, 1024 join pairing: must FAIL)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$VL" ] || VL=verilator
S=rtl/hbm_accel/generic/adapters/static_su
python3 tools/hbm_static/su_pretree_bench.py "$out" > "$out/gen.log"
$VL --version | tee "$out/verilator_version.txt"
$VL --binary --timing -j 8 --top-module tb_hbm_su_red_pretree -GMUT=$mut -Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC \
 -DOT_FP_DATA_NORST --Mdir "$out/obj" -o vtb \
 $S/reduction/ot_hbm_su_red_pretree.sv $S/top/ot_hbm_su_static_qcore_r5.sv $S/reduction/ot_hbm_su_reduce_static.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_su_red_pretree.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 2; }
(cd "$out" && ./obj/vtb $(cat plusargs.txt)) | tee "$out/bench.log" | tail -12
