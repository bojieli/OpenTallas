#!/bin/bash
# Build the verify-block near-HBM attention bench (VP lane sets on one K/V stream; ot_qwen_nearhbm_attn_die_tb_vp).
#   build_nearhbm_tb_vp.sh <outdir> <HD> <R> <real|dpi> <VP> [VMASK=1] [extra verilator args]
# Successor of build_nearhbm_tb.sh (untouched): same sources with the _vp stack and bench.
set -e
OUT=$1; HD=$2; RR=$3; FP=$4; VP=$5; VM=${6:-1}; shift 5; [ $# -gt 0 ] && shift
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$W/test/nearhbm/ot_qwen_nearhbm_attn_die_tb_vp.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_vp.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub.sv $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv \
 $W/hdc/ot_hdc_sfu.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv \
 $W/proto/ot_fp32_add_rne_pipe.sv"
CPP="$W/test/nearhbm/tb_qwen_nearhbm_attn_vp.cpp"
if [ "$FP" = "real" ]; then
  SRC="$SRC $W/hdc/ot_hdc_fastfp.sv $W/hdc/ot_hdc_prefix.sv $W/hdc/ot_hdc_fp32_add_lat.sv $W/hdc/ot_hdc_fp32_mul_lat.sv"
else
  SRC="$SRC $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv"
  CPP="$CPP $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
fi
SCALE=32\'h3DB504F3
[ "$HD" = "16" ] && SCALE=32\'h3E800000
mkdir -p $OUT
$VL --cc --exe --build -j ${JOBS:-16} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign fast --x-initial fast --top-module ot_qwen_nearhbm_attn_die_tb_vp \
  -GHD=$HD -GR=$RR -GVP=$VP -GVMASK=$VM -GSCALE="$SCALE" "$@" -CFLAGS "-O1 -DNHB_R=$RR -DNHB_HD=$HD -DNHB_VP=$VP" \
  --Mdir $OUT -o Vtb $SRC $CPP > $OUT/build.log 2>&1
echo built $OUT
