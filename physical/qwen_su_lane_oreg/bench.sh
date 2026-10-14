#!/bin/bash
# r6 2026-10-14: lane cluster output register stage (ot_hdc_vstream_lane_t OREG / ot_hdc_vstream LOREG).
# usage: bench.sh <name> <outdir> [extra verilator args...]   (run from the repo root)
set -o pipefail
name=$1; out=$2; shift 2
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p $out
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN \
  -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_su_vm_bv -GRTREE=1 -GLT=1 -GVL=15 -GRD=2 -GRSRAM=1 -GLOFF=1 "$@" \
  --Mdir $out/$name rtl/test/qwen_vm_me/tb_qfd_su_vm_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_su_master_bv.sv \
  rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv \
  rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv \
  rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv \
  rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv \
  rtl/hdc/ot_hdc_vstream.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_reduce.sv \
  rtl/hdc/ot_hdc_reduce_q.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/proto/ot_fp32_mul_rne_pipe.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > $out/$name.build.log 2>&1 || { echo "BUILD_FAIL $name"; tail -20 $out/$name.build.log; exit 2; }
$out/$name/Vtb_qfd_su_vm_bv > $out/$name.log 2>&1
grep -E "^(PASS|FAIL) qfd_su_vm_bv" $out/$name.log | head -3
