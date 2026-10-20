#!/bin/bash
# PVM distributed-source bench (run from the repo root):
#   run_pv_merge_distributed_bench.sh <workdir> [MUT] [SAFE] [TIGHT] [PUBEARLY] [REASSERT] [XRAND]
# Verilator 5.050 (daemon pin).  Candidate vs reference SAFE2 one-input/one-output wrapper at +1 age, every output bit
# every edge (XRAND 1: random initial state, payload compared under valid); golden check on the reference stream.
set -u
W=$1; M=${2:-0}; S=${3:-0}; TI=${4:-0}; PE=${5:-0}; RA=${6:-0}; XR=${7:-0}
XF=""; XA=""
[ "$XR" = 1 ] && { XF="--x-assign unique --x-initial unique"; XA="+verilator+rand+reset+2 +verilator+seed+${PVM_SEED:-7}"; }
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
T=rtl/hbm_accel/sm/attn/test
mkdir -p "$W"; W=$(realpath "$W")
python3 $T/pv_merge_golden.py gen "$W/stim.hex"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSTIM="\"$W/stim.hex\"" \
  -GMUT=$M -GSAFE=$S -GTIGHT=$TI -GPUBEARLY=$PE -GREASSERT=$RA -GXRAND=$XR $XF ${PVM_VFLAGS:-} --top-module tb_pv_merge_distributed --Mdir "$W/obj" -o tb \
  $T/tb_pv_merge_distributed.sv rtl/hbm_accel/sm/attn/test/pvm_reference_pin_wrapper.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_s3.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_distributed.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_distributed_core.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.v > "$W/build.log" 2>&1 \
  || { tail -20 "$W/build.log"; echo "PVM BUILD FAIL"; exit 1; }
"$W/obj/tb" $XA > "$W/run.log" 2>&1; grep -E "STOPCLK|REASSERT|MISMATCH|CANDIDATE|NOT_|Error|fatal" "$W/run.log" | head -5; tail -2 "$W/run.log"
python3 $T/pv_merge_golden.py check "$W/stim.hex" "$W/run.log" $([ "$TI" = 1 ] && echo tight) | tee "$W/check.log"
grep -q "^PVM PASS" "$W/check.log"
