#!/bin/bash
# kv-die 2026-10-09: build the end-to-end attention layer step through the ROM die <-> KV die link (Verilator 5).
#   build_qkvd_tb.sh <outdir> [-GR=8 -GLINK=.. -GROM_ST=.. -GKV_ST=.. -GPHY_LAT=.. -GMUT=..]   (HD 128, DPI FP stand-ins,
#   the near-HBM stack and hub TIMING SUCCESSORS _p through their bench shims)
set -e
OUT=$1; shift
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=$(cd "$(dirname "$0")/../.." && pwd)
P=$(cd "$W/.." && pwd)
RR=8; RST=24
# STACK=c: the re-cut stack (rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_c.sv, LFB / LBD via KVD_LFB / KVD_LBD)
if [ "${STACK:-p}" = c ]; then
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_c.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_c.sv"
  DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_LBD=${LBD:-2}"
elif [ "${STACK:-p}" = h ]; then
  # STACK=h: re-cut H (re-cut D with the row engine as hard sub-tiles: 4 head tiles + an engine control tile)
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv"
  DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_ND=${ND:-1} ${HMUT:++define+KVD_HMUT}"
elif [ "${STACK:-p}" = e ]; then
  # STACK=e: re-cut E (D with levels 1-3 on the lane loop adders; rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_e.sv)
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_e.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_e.sv"
  DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_ND=${ND:-1}"
elif [ "${STACK:-p}" = d ]; then
  # STACK=d: re-cut D (P.V levels 1-3 in the engine; rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_d.sv, LFB / ND via KVD_LFB / KVD_ND)
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_d.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_d.sv"
  DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_ND=${ND:-1}"
else
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv"; DEFS=""
fi
for a in "$@"; do case $a in -GR=*) RR=${a#-GR=};; -GROM_ST=*) RST=${a#-GROM_ST=};; esac; done
SRC="$W/test/qwen_kv_die/ot_qkvd_layer_tb.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_d2d.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_cbridge.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_rom_end.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_merge.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv $P/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv \
 $STK \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv \
 $W/hdc/ot_hdc_sfu.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv \
 $W/proto/ot_fp32_add_rne_pipe.sv \
 $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv"
CPP="$W/test/qwen_kv_die/tb_qkvd_layer.cpp $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
mkdir -p $OUT
$VL --cc --exe --build -j 16 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign fast --x-initial fast --top-module ot_qkvd_layer_tb -GHD=128 $DEFS "$@" \
  -CFLAGS "-O1 -DKVD_R=$RR -DKVD_ROM_ST=$RST" --Mdir $OUT -o Vtb $SRC $CPP > $OUT/build.log 2>&1
echo built $OUT
