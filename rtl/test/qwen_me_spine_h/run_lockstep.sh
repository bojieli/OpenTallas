#!/bin/bash
# Build and run the spine lockstep bench.  Usage: run_lockstep.sh <out_dir> <cycles> <-Gparams...>
# (run from the repository root; Verilator 5.050)
out=$1; n=$2; shift 2
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv
   rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_me_array_w12.sv
   rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/test/qwen_me_spine_h/tb_qwen_me_spine_h_lockstep.sv"
mkdir -p $out
$V --cc --exe --build -j ${JOBS:-16} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --x-assign 0 --x-initial 0 \
   --top-module tb_qwen_me_spine_h_lockstep --prefix Vtb --Mdir $out/obj "$@" $F \
   rtl/test/qwen_me_spine_h/tb_qwen_me_spine_h_lockstep.cpp -o tb -CFLAGS -O1 > $out/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $out/build.log; exit 2; }
$out/obj/tb $n | tee $out/result.json
