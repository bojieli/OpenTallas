#!/usr/bin/env bash
# split-spine SU latency campaign (qwen-system): tb_qfd_su_vm_bv with per-op latency, SW 8 / 64, CRX 2 / 4 / 6
# usage: run_su_lat.sh <repo> <work dir>   (run from <repo>)
set -uo pipefail; repo=$1; wd=$2; mkdir -p $wd; cd $repo
VER=verilator
VFL="--binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT"
SRC="rtl/qwen_sys/vm_me_20261008/ot_qfd_su_master_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_vstream.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_reduce.sv rtl/hdc/ot_hdc_reduce_q.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/proto/ot_fp32_mul_rne_pipe.sv"
for sw in 8 64; do for crx in 2 4 6; do
  n=sw${sw}_crx${crx}
  ( $VER $VFL -j 8 --top-module tb_qfd_su_vm_bv -GSW=$sw -GCRX=$crx -GSEED=11 -GOPS=120 --Mdir $wd/$n rtl/test/qwen_vm_me/tb_qfd_su_vm_bv.sv $SRC > $wd/$n.build 2>&1 && $wd/$n/Vtb_qfd_su_vm_bv > $wd/$n.log 2>&1; echo "$n: $(grep -h 'SU_LAT\|PASS\|FAIL' $wd/$n.log | tr '\n' ' ')" ) &
done; done; wait
