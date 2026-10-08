#!/bin/bash
# qwen-band-integrate: build and run the split-spine end-to-end bench (tb_qfd_spine_band) under Verilator 5.050.
# Usage (from the repository root): run_spine_band.sh <out_dir> [-GNAME=VALUE ...].  Prints PASS / FAIL qfd_spine_band;
# exits 0 only on PASS.
out=$1; shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_qwen_w12_matvec.sv
   rtl/hdc/ot_qwen_w12_arith.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_hdc_cg.sv
   rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv
   rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
   rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv
   rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/qwen_sys/band_integrate_20261008/ot_qfd_spine_band.sv
   rtl/test/qwen_band_integrate/tb_qfd_spine_band.sv"
mkdir -p $out
$V --binary --timing -j ${JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN \
   --x-assign 0 --x-initial 0 --top-module tb_qfd_spine_band --Mdir $out/obj "$@" $F > $out/build.log 2>&1 \
   || { echo "BUILD_FAIL"; tail -20 $out/build.log; exit 2; }
$out/obj/Vtb_qfd_spine_band > $out/result.txt 2>&1
grep -E "^(PASS|FAIL|split)" $out/result.txt
grep -q "^PASS qfd_spine_band" $out/result.txt   # exit status: 0 on PASS only (a mutant run must exit non-zero)
