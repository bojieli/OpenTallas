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
  # el1011-q-kvd-head: env HSUB=1 -> the hierarchical head tile (ot_qwen_nearhbm_head_hs, KVD_HSUB); HSMUT=1 its mutant
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $W/hdc/nearhbm/ot_qkh_subtiles.sv $W/lib/ot_rst_relay.sv"
  DEFS="+define+KVD_LFB=${LFB:-4} +define+KVD_ND=${ND:-1} ${HMUT:++define+KVD_HMUT} ${RMUT:++define+KVD_RMUT} ${VMUT:++define+KVD_VMUT} ${HSUB:++define+KVD_HSUB} ${HSMUT:++define+KVD_HSMUT} ${ESLOT:++define+KVD_ECTL_SLOT}"
  # q13-ectl: env ESLOT=1 -> the control tile in its TP8 contract slot structure (KVD_ECTL_SLOT: pin stages / relays, D1 4)
  # the head_hs sub-tiles use the real ot_hdc_fp32_add_lat_nr, whose ot_hdc_lzc32 lives in ot_hdc_fastfp.sv (the rest of
  # that file collides with the bench's fast-FP stand-ins): extract that one module verbatim
  mkdir -p $OUT && awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > $OUT/ot_hdc_lzc32_x.sv
  STK="$STK $OUT/ot_hdc_lzc32_x.sv"
  # q13-kvleaves: env ECTL3=1 -> the row-engine control cell as its three hard die leaves (qkd_ectl_a / _b / _c,
  # rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv; slot timing, DQ 128 only)
  if [ -n "${ECTL3:-}" ]; then DEFS="$DEFS +define+KVD_ECTL3"; STK="$STK $W/hdc/nearhbm/ot_qkd_ectl_parts.sv"; fi
elif [ "${STACK:-p}" = k ]; then
  # STACK=k (el1013-qwen-kvstrips): re-cut H engines + the aggregator strip built from its die masters (qkd_astk_pv /
  # _ep / _ex / _zn / _ctl, rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv) in the die wiring of
  # rtl/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv.  env AKMUT=1..4: one leaf mutant; AKRL: relay stations a net.
  STK="$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_k.sv $W/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv $W/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $W/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv $W/hdc/nearhbm/ot_qkh_subtiles.sv $P/physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v $P/physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v"
  DEFS="+define+KVD_LFB=4 +define+KVD_ND=1 +define+KVD_ERL=3 +define+KVD_AKMUT=${AKMUT:-0} +define+KVD_AKRL=${AKRL:-1} ${AKDBG:++define+KVD_AKDBG} ${HSUB:++define+KVD_HSUB}"
  mkdir -p $OUT && awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > $OUT/ot_hdc_lzc32_x.sv
  STK="$STK $OUT/ot_hdc_lzc32_x.sv"
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
# Opt-in reciprocal local-clock leaf for the hierarchical hub.
if [ "${RECIPLEAF:-0}" = 1 ]; then
  DEFS="$DEFS +define+QKH_RECIP_LEAF"
  STK="$STK $W/hdc/nearhbm/ot_qkh_recip_leaf.sv $W/lib/ot_rst_pipe.sv"
fi
for a in "$@"; do case $a in -GR=*) RR=${a#-GR=};; -GROM_ST=*) RST=${a#-GROM_ST=};; esac; done
SRC="$W/test/qwen_kv_die/ot_qkvd_layer_tb.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_fifo_sb.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_buf_tiles.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_fifo_sl.sv $W/lib/ot_rst_relay.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_d2d.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_cbridge.sv \
 $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_rom_end.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_merge.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_ke_cluster.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_ke_tiles.sv $P/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv \
 $STK \
 $W/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv $W/hdc/nearhbm/ot_nhb_tiles.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_t.sv $W/hdc/ot_hdc_fp32_add_lat_nr.sv $W/hdc/ot_hdc_prefix.sv \
 $W/hdc/nearhbm/ot_qwen_nearhbm_prod.sv $W/hdc/ot_hdc_sfu_q.sv $W/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv \
 $W/hdc/ot_hdc_sfu.sv $W/hdc/ot_hdc_delay.sv $W/hdc/ot_hdc_fpu.sv $W/hdc/ot_hdc_fp32_mul_pipe.sv \
 $W/proto/ot_fp32_add_rne_pipe.sv \
 $W/test/nearhbm/sim_nhb_fp_lat_dpi.sv $W/test/sim_hdc_v41x_fastfp_dpi.sv $W/test/sim_hdc_v41x_fastfp_wrap.sv \
 $W/test/qwen_kv_die/ot_qkvd_hbm_timed_stack.sv $W/hdc/v41x/ot_hdc_v41x_idx_hbm.sv \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
CPP="$W/test/qwen_kv_die/tb_qkvd_layer.cpp $W/test/nearhbm/sim_nhb_fp_lat_dpi.cpp $W/test/sim_hdc_v41x_fastfp_dpi.cpp"
mkdir -p $OUT
# el1011-q-kvd 2026-10-11: the ANR adders (ot_hdc_fp32_add_lat_sel NR=1, used by the hardened hub tiles) need
# ot_hdc_lzc32; ot_hdc_fastfp.sv cannot be added whole (its fast fp units collide with the DPI wrappers), so the one
# self-contained module is extracted from it here.
awk '/^module ot_hdc_lzc32/,/^endmodule/' $W/hdc/ot_hdc_fastfp.sv > $OUT/ot_hdc_lzc32_only.sv
SRC="$SRC $OUT/ot_hdc_lzc32_only.sv"
# el1011-q-kvd 2026-10-12: HSUB=1 puts ~3,800 real ot_hdc_fp32_add_lat_nr (bit-level prefix networks) into the HD 128
# 4-stack bench (16 ot_qkh_lane8 per head); Verilator peaked at 491 GiB and never finished.  As for ot_hdc_fp32_add_lat
# (sim_nhb_fp_lat_dpi.sv), the bench runs the DPI stand-in rtl/test/nearhbm/sim_nhb_fp_lat_nr_dpi.sv, checked
# cycle-exact against the real unit by rtl/test/nearhbm/run_nr_standin_equiv.sh; the rest of the real file
# (ot_hdc_fp32_add_lat_sel, ot_hdc_w11_cut_v, ot_hdc_add_hcopy36) is kept.  NR_REAL=1 forces the real units.
if { [ -n "${HSUB:-}" ] || [ "${STACK:-p}" = k ]; } && [ -z "${NR_REAL:-}" ]; then   # STACK=k: 2,112 ANR adders in the tree cells
  awk '/^module ot_hdc_fp32_add_lat_nr /{s=1} !s{print} s&&/^endmodule/{s=0}' $W/hdc/ot_hdc_fp32_add_lat_nr.sv > $OUT/ot_hdc_fp32_add_lat_nr_rest.sv
  SRC="${SRC/$W\/hdc\/ot_hdc_fp32_add_lat_nr.sv/$OUT/ot_hdc_fp32_add_lat_nr_rest.sv $W/test/nearhbm/sim_nhb_fp_lat_nr_dpi.sv}"
fi
$VL --cc --exe --build -j 16 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --x-assign fast --x-initial fast --top-module ot_qkvd_layer_tb -GHD=128 $DEFS ${HPS:++define+KVD_HPSRAM=1} ${PBMUT:++define+KVD_PBMUT} ${SBD:++define+KVD_SBD=$SBD} ${SBP:++define+KVD_SBP=$SBP} ${HT:++define+KVD_HT} ${PF:++define+KVD_PF} ${SPL:++define+KVD_SPL} ${PQ:++define+KVD_PQ=$PQ} ${HUBT:++define+KVD_HUBT} ${FSBMUT:++define+KVD_FSBMUT} "$@" \
  -CFLAGS "-O1 -DKVD_R=$RR -DKVD_ROM_ST=$RST" --Mdir $OUT -o Vtb $SRC $CPP > $OUT/build.log 2>&1
echo built $OUT
