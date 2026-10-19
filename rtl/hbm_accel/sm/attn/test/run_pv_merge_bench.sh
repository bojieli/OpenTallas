#!/bin/bash
# HH-2 2026-10-19 smh_pvm bench (run from the repo root): run_pv_merge_bench.sh <workdir> [MUT] [SAFE] [TIGHT] [PUBEARLY];
# Verilator 5.050 (daemon pin).  SAFE / TIGHT / PUBEARLY: tb_pv_merge parameters (HBM-PVM-SAFE 10-19).
set -u
W=$1; M=${2:-0}; S=${3:-0}; TI=${4:-0}; PE=${5:-0}
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
T=rtl/hbm_accel/sm/attn/test
mkdir -p "$W"; W=$(realpath "$W")
python3 $T/pv_merge_golden.py gen "$W/stim.hex"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSTIM="\"$W/stim.hex\"" \
  -GMUT=$M -GSAFE=$S -GTIGHT=$TI -GPUBEARLY=$PE ${PVM_VFLAGS:-} --top-module tb_pv_merge --Mdir "$W/obj" -o tb \
  $T/tb_pv_merge.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$W/build.log" 2>&1 \
  || { tail -20 "$W/build.log"; echo "PVM BUILD FAIL"; exit 1; }
"$W/obj/tb" > "$W/run.log"; tail -2 "$W/run.log"
python3 $T/pv_merge_golden.py check "$W/stim.hex" "$W/run.log" $([ "$TI" = 1 ] && echo tight) | tee "$W/check.log"
grep -q "^PVM PASS" "$W/check.log"
