#!/bin/bash
# FP32 lane: build + run tb_fp32_lat4_eq (Verilator).  Usage: run_eq.sh <out_dir> [n_random] [seed]
set -euo pipefail
WT=$(cd "$(dirname "$0")/../.." && pwd); OUT=${1:?out}; N=${2:-5000000}; SEED=${3:-12345}
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mkdir -p "$OUT"; cd "$OUT"
verilator --version | tee verilator.version
verilator --cc --exe --build -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_fp32_lat4_eq -Mdir obj \
  "$WT/rtl/hdc/ot_hdc_prefix.sv" "$WT/rtl/hdc/ot_hdc_fastfp.sv" "$WT/rtl/hdc/ot_hdc_fp32_add_lat.sv" \
  "$WT/rtl/hdc/ot_hdc_fp32_mul_lat.sv" "$WT/rtl/hdc/ot_hdc_fp32_f12.sv" "$WT/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv" \
  "$WT/tools/fp32_lat4/tb_fp32_lat4_eq.sv" "$WT/tools/fp32_lat4/tb_fp32_lat4_eq.cpp" > build.log 2>&1 || { tail -40 build.log; exit 2; }
./obj/Vtb_fp32_lat4_eq "$N" "$SEED" | tee eq_${SEED}.log
