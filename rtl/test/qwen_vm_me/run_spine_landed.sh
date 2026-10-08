#!/bin/bash
# Build and run the ME result-path end-to-end bench.  Usage: run_spine_landed.sh <out_dir> <-Gparams...>
# (run from the repository root; Verilator 5.050).  Prints PASS / FAIL qfd_spine_landed.
out=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv
   rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_hdc_cg.sv
   rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv
   rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
   rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv
   rtl/test/qwen_vm_me/tb_qfd_spine_landed.sv"
mkdir -p $out
$V --binary --timing -j ${JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN \
   --x-assign 0 --x-initial 0 --top-module tb_qfd_spine_landed --Mdir $out/obj "$@" $F > $out/build.log 2>&1 \
   || { echo "BUILD_FAIL"; tail -20 $out/build.log; exit 2; }
$out/obj/Vtb_qfd_spine_landed | tee $out/result.txt | grep -E "^(PASS|FAIL)"
