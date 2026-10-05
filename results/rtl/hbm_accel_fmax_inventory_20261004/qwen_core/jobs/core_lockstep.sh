#!/bin/bash
# core_lockstep.sh <snapshot> <outdir> "<-G params>" "<runs>": generate the two emitted cores and run the lockstep bench
R=/srv/opentallas-scratch/claude/hbm-fmax-qcore; src=$1; out=$2; prm=$3; runs=$4
cd $R/$src && python3 rtl/test/hbm_accel_qwen/fmax/gen_core_lockstep.py $out/gen > /dev/null || exit 3
exec $R/jobs/vl_bench.sh $src $out tb_qwen_core_f12_lockstep "$prm" "$runs" rtl/test/hbm_accel_qwen/fmax/tb_qwen_core_f12_lockstep.sv \
  $out/gen/core_ref.sv $out/gen/core_f12.sv $out/gen/ctx_ref.sv $out/gen/ctx_f12.sv $out/gen/stubs_ref.sv $out/gen/stubs_f12.sv \
  rtl/hbm_accel/qwen/fmax/ot_qwen_hbmacc_gate_f12.sv rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_fastfp_lat.sv \
  rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  rtl/hdc/ot_hdc_stream.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_reduce_q.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_sfu.sv
