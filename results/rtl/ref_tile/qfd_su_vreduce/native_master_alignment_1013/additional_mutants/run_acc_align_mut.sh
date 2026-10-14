#!/bin/bash
set -e
out=${1:-result/acc};lt=${2:-1};lmin=${3:-15};mut=${4:-0};am=${5:-0};sm=${6:-0};vm=${7:-0}
mkdir -p "$out"
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_su_vm_bv_acc -GLT="$lt" -GLMIN="$lmin" -GVL=7 -GRD=2 -GLOFF=1 -GSEED=11 -GMUT="$mut" -GAMUT="$am" -GSMUT="$sm" -GVMUT="$vm" --Mdir "$out" tb_acc_align_mut.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_master_bv_acc.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_vstream.sv rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_reduce.sv rtl/hdc/ot_hdc_reduce_q.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/proto/ot_fp32_mul_rne_pipe.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v >"$out/compile.log" 2>&1
"$out/Vtb_qfd_su_vm_bv_acc" >"$out/run.log" 2>&1
cat "$out/run.log"

if grep -q '^FAIL qfd_su_vm_bv ' "$out/run.log"; then exit 1; fi
if ! grep -q '^PASS qfd_su_vm_bv ' "$out/run.log"; then exit 2; fi
