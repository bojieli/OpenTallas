#!/bin/bash
# Qwen TP8 split die link bench (tb_qwen_split_link.sv).  usage: run_split_link.sh <outdir> [-Ptb_qwen_split_link.X=v ...]
# Prints the bench's SPLIT_LINK_PASS / SPLIT_LINK_FAIL line.  iverilog -g2012 (no DPI, no macros).
set -eu
OUT=$1; shift
W=$(cd "$(dirname "$0")/../.." && pwd)
P=$(cd "$W/.." && pwd)
K=$W/qwen_sys/kv_die_20261009
SRC="$W/test/qwen_split/tb_qwen_split_link.sv \
 $W/qwen_sys/split_20261014/ot_qwen_split_lvl.sv $W/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv \
 $W/qwen_sys/split_20261014/ot_qfd_split_romlink.sv \
 $K/ot_qkvd_fifo.sv $K/ot_qkvd_fifo_sb.sv $K/ot_qkvd_fifo_sl.sv $K/ot_qkvd_buf_tiles.sv $K/ot_qkvd_d2d.sv \
 $K/ot_qkvd_rom_end.sv $K/ot_qkvd_kv_end.sv $K/ot_qkvd_ke_cluster.sv $K/ot_qkvd_ke_tiles.sv \
 $W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $K/ot_qkvd_kv_seq_merged.sv $K/ot_qkvd_kv_desc.sv $W/qwen_sys/system_20261008/ot_qfd_dctl.sv \
 $W/lib/ot_rst_relay.sv $W/hdc/ot_hdc_delay.sv \
 $P/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
mkdir -p $OUT
iverilog -g2012 -s tb_qwen_split_link "$@" -o $OUT/tb.vvp $SRC > $OUT/build.log 2>&1 || { cat $OUT/build.log | head -40; exit 2; }
vvp -n $OUT/tb.vvp > $OUT/run.log 2>&1 || true
grep -E "SPLIT_LINK_(PASS|FAIL)" $OUT/run.log | tail -1
