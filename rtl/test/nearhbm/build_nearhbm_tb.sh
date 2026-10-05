#!/bin/bash
# Build the near-HBM attention die bench (4 stacks + hub + links) with Verilator 5.
#   build_nearhbm_tb.sh <outdir> <HD> <R> <real|dpi> [extra verilator args]
#   real: the RTL arithmetic units (ot_hdc_fp32_{add,mul}_lat, ot_hdc_fastfp) -- head_dim 16 fits this machine
#   dpi : the host-float stand-ins (sim_nhb_fp_lat_dpi.sv, sim_hdc_v41x_fastfp_dpi.sv) -- head_dim 128
set -e
OUT=$1; HD=$2; RR=$3; FP=$4; shift 4
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$W/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub.sv $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv \
 $W/hdc/ot_hdc_sfu.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv \
 $W/proto/ot_fp32_add_rne_pipe.sv"
CPP="$W/test/nearhbm/tb_qwen_nearhbm_attn.cpp"
if [ "$FP" = "real" ]; then
  SRC="$SRC $W/hdc/ot_hdc_fastfp.sv $W/hdc/ot_hdc_prefix.sv $W/hdc/ot_hdc_fp32_add_lat.sv $W/hdc/ot_hdc_fp32_mul_lat.sv"
else
  SRC="$SRC $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv"
  CPP="$CPP $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
fi
SCALE=32\'h3DB504F3
[ "$HD" = "16" ] && SCALE=32\'h3E800000
mkdir -p $OUT
$VL --cc --exe --build -j 16 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign fast --x-initial fast --top-module ot_qwen_nearhbm_attn_die_tb \
  -GHD=$HD -GR=$RR -GSCALE="$SCALE" "$@" -CFLAGS "-O1 -DNHB_R=$RR -DNHB_HD=$HD" --Mdir $OUT -o Vtb $SRC $CPP \
  > $OUT/build.log 2>&1
echo built $OUT
