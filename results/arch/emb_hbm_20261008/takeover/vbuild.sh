#!/bin/bash
# usage: vbuild.sh <name> [-Gparam=v ...]
set -e
R=/srv/opentallas-scratch2/scratch/claude/emb-hbm
cd $R/src
N=$1; shift
S=rtl/qwen_sys/emb_hbm_20261008
mkdir -p $R/obj_$N
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -O3 --x-assign fast --x-initial fast \
  -Irtl/test/emb_hbm --top-module tb_emb_hbm_e2e -Mdir $R/obj_$N "$@" \
  $S/ot_qfd_emb_pkg.sv $S/ot_hbm_r14_stream_pc_srow.sv $S/ot_qwen_ctrl_pc_emb.sv $S/ot_qfd_emb_pcport.sv $S/ot_qfd_emb_strip.sv \
  $S/ot_qfd_link_far.sv $S/ot_qfd_emb_gw.sv $S/ot_qwen_die_hub_emb.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/lib/ot_async_fifo.sv \
  rtl/lib/ot_reset_sync.sv rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv \
  rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv rtl/test/emb_hbm/tb_emb_hbm_e2e.sv > $R/obj_$N/build.log 2>&1
echo built $N
