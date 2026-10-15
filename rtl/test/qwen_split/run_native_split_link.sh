#!/bin/bash
# Qwen TP8 split die link bench (tb_qwen_split_link.sv).  usage: run_split_link.sh <outdir> [-Ptb_qwen_split_link.X=v ...]
# Prints the bench's SPLIT_LINK_PASS / SPLIT_LINK_FAIL line.  iverilog -g2012 (no DPI, no macros).
set -eu
OUT=$1; shift
W=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
python3 - "$W/test/qwen_split/tb_qwen_split_link.sv" "$OUT/tb_native.sv" <<'PYGEN'
import sys
from pathlib import Path
t = Path(sys.argv[1]).read_text()
a = t.index('        ot_qfd_split_romlink #(')
b = t.index('.fault(faults_link[0]), .fault_cause(c_fc));', a) + len('.fault(faults_link[0]), .fault_cause(c_fc));')
t = t[:a] + """        wire [10:0] c_native_cause;
        assign c_fc = c_native_cause[7:0];
        qfd_d2d_rom #(.XS(C_X3 + C_X3_CR + 48), .OCR_AR(C_AR + C_AR_CR + 40), .RB_RES(32)) u_native_compute (
            .ck(clk), .llr_ck0(clk), .llr_ck1(clk), .llr_ck2(clk), .llr_ck3(clk), .llr_ck4(clk), .rst_n(rst_n),
            .x3_v(c_x3_v), .x3_d(c_x3[511:0]), .x3_tag(c_x3[522:512]), .x3_cr(c_x3_cr),
            .ar_v(c_ar_v), .ar_d(c_ar), .ar_cr(c_ar_cr), .ea_v(1'b0), .ea_kind(1'b0), .ea_addr(24'd0), .ea_cr(),
            .eq_v(), .eq_d(), .dc(c_sd), .kvd(c_kvd), .dh(c_ds), .pw(c_pw),
            .fdi_tx_up(c_pup), .fdi_tx_v(c_ptv), .fdi_tx_flit(c_ptf), .fdi_rx_v(c_prv), .fdi_rx_flit(c_prf),
            .fault(faults_link[0]), .fault_cause(c_native_cause));""" + t[b:]
# Remove both stand-alone LLRs; they now live inside the native die wrappers.
a = t.index('        if (LLR) begin : g_llr')
b = t.index('        // ---- KV/system die link end + bridge ----', a)
t = t[:a] + "        assign llr_f = 2'b00; // native wrappers include LLR faults\n" + t[b:]
a = t.index('        ot_qkvd_kv_end #(')
b = t.index('.fault(faults_link[1]), .fault_cause(k_fc));', a) + len('.fault(faults_link[1]), .fault_cause(k_fc));')
t = t[:a] + """        wire [7:0] k_native_cause;
        assign k_fc = k_native_cause[4:0];
        qkd_d2d #(.QD(8), .UCX(64), .FCR_RES(32), .SPL(KVE_SPL),
            .LLR_MUT(MUT == 4 ? 1 : (MUT == 5 ? 2 : (MUT == 6 ? 3 : 0)))) u_native_kv (
            .ck(clk), .llr_ck0(clk), .llr_ck1(clk), .llr_ck2(clk), .llr_ck3(clk), .llr_ck4(clk), .rst_n(rst_n),
            .t_v(kt_v), .t_d(kt_d), .t_cr(kt_cr), .r_v(kr_v), .r_d(kr_d), .r_cr(kr_cr),
            .tx_up(k_pup), .tx_v(k_ptv), .tx_flit(k_ptf), .rx_v(k_prv), .rx_flit(k_prf),
            .fault(faults_link[1]), .fault_cause(k_native_cause));""" + t[b:]
Path(sys.argv[2]).write_text(t)
PYGEN
P=$(cd "$W/.." && pwd)
K=$W/qwen_sys/kv_die_20261009
SRC="$OUT/tb_native.sv $W/qwen_split/qfd_link_slots.sv $W/qwen_sys/split_20261014/qkd_d2d.sv \
 $W/qwen_sys/split_20261014/ot_qwen_split_lvl.sv $W/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv \
 $W/qwen_sys/split_20261014/ot_qfd_split_romlink.sv \
 $K/ot_qkvd_fifo.sv $K/ot_qkvd_fifo_sb.sv $K/ot_qkvd_fifo_sl.sv $K/ot_qkvd_buf_tiles.sv $K/ot_qkvd_d2d.sv \
 $K/ot_qkvd_rom_end.sv $K/ot_qkvd_kv_end.sv $K/ot_qkvd_ke_cluster.sv $K/ot_qkvd_ke_tiles.sv \
 $W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $K/ot_qkvd_kv_seq_merged.sv $K/ot_qkvd_kv_desc.sv $W/qwen_sys/system_20261008/ot_qfd_dctl.sv \
 $W/lib/ot_rst_relay.sv $W/hdc/ot_hdc_delay.sv \
 $P/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
mkdir -p $OUT
iverilog -g2012 -s tb_qwen_split_link -Ptb_qwen_split_link.LLR=1 -Ptb_qwen_split_link.KVE_SPL=1 "$@" -o $OUT/tb.vvp $SRC > $OUT/build.log 2>&1 || { cat $OUT/build.log | head -40; exit 2; }
vvp -n $OUT/tb.vvp > $OUT/run.log 2>&1 || true
grep -E "SPLIT_LINK_(PASS|FAIL)" $OUT/run.log | tail -1
