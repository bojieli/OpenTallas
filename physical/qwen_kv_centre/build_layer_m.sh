#!/bin/bash
# Qwen ROM TP8 track B: build the attention layer step through the MERGED-die KV sequencer (Verilator 5; the two-die
# form is rtl/test/qwen_kv_die/build_qkvd_tb.sh, whose STACK=h source set this follows).
#   build_layer_m.sh <outdir> [-GROM_ST=.. -GLINK=.. -GQX=.. -GRX=.. -GKVL=.. -GMUT=..]    env CLUSTER=1: DUT = the
#   hardened-leaf cluster qkd_seq (the slots file under rtl); SEQMUT=1: its wiring mutant.
set -e
OUT=$1; shift
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=$(cd "$(dirname "$0")/../.." && pwd)
W=$P/rtl
mkdir -p $OUT
awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > $OUT/ot_hdc_lzc32_only.sv
STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $W/hdc/nearhbm/ot_qkh_subtiles.sv"
DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_ND=${ND:-1} ${CLUSTER:++define+KVD_CLUSTER} ${SEQMUT:++define+OT_QKD_SEQ_MUT}"
SRC="$W/test/qwen_kv_die/ot_qkvd_layer_m_tb.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv $P/rtl/physical/ot_qwen_kv_centre_slots.sv \
 $W/qwen_sys/ot_qwen_sys_rst_seq.sv $W/lib/ot_reset_sync.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv $W/qwen_sys/system_20261008/ot_qfd_dctl.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_merge.sv $W/lib/ot_rst_relay.sv \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv $STK \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv $W/hdc/nearhbm/ot_nhb_tiles.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_t.sv $W/hdc/ot_hdc_fp32_add_lat_nr.sv $W/hdc/ot_hdc_prefix.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv \
 $W/hdc/ot_hdc_sfu.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv \
 $W/proto/ot_fp32_add_rne_pipe.sv \
 $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv \
 $W/test/qwen_kv_die/ot_qkvd_hbm_timed_stack.sv $W/hdc/v41x/ot_hdc_v41x_idx_hbm.sv \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $OUT/ot_hdc_lzc32_only.sv"
CPP="$W/test/qwen_kv_die/tb_qkvd_layer_m.cpp $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
$VL --cc --exe --build -j ${VJ:-16} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign fast --x-initial fast --top-module ot_qkvd_layer_m_tb -GHD=128 $DEFS "$@" \
  -CFLAGS "-O1 -DKVD_R=8" --Mdir $OUT -o Vtb $SRC $CPP > $OUT/build.log 2>&1
echo built $OUT
