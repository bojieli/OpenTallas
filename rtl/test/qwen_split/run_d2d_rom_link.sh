#!/bin/bash
# Compute-die link end qfd_d2d_rom (rtl/qwen_split/qfd_link_slots.sv) in the kvsys lead's FULL link bench
# (tb_qwen_split_link.sv, LLR=1: real KV end + bridge + sequencer + PHY model pair, 38-stage decode step): the bench's own
# compute end (ot_qfd_split_romlink u_rl + ot_qkvd_d2d_llr u_lc) is replaced, at run time, by ONE qfd_d2d_rom instance
# wired to the same nets (the bench file itself is not edited).  usage: run_d2d_rom_link.sh <outdir> [-P...=v ...]
# -Ptb_qwen_split_link.D2D_MUT=1 = the wrapper's crossed-tag mutant (must FAIL).  Prints SPLIT_LINK_(PASS|FAIL).
set -eu
OUT=$1; shift
W=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p $OUT
python3 - "$W/test/qwen_split/tb_qwen_split_link.sv" "$OUT/tb_d2d.sv" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
a = t.index('        ot_qfd_split_romlink #(')
b = t.index('.fault(faults_link[0]), .fault_cause(c_fc));', a) + len('.fault(faults_link[0]), .fault_cause(c_fc));')
new = """        wire [10:0] c_fcw;
        assign c_fc = c_fcw[7:0];
        qfd_d2d_rom #(.XS(2 * C_ST + 48), .OCR_AR(2 * C_ST + 40), .RB_RES(32), .MUT(D2D_MUT)) u_d2d (.ck(clk), .rst_n(rst_n),
            .x3_v(c_x3_v), .x3_d(c_x3[511:0]), .x3_tag(c_x3[522:512]), .x3_cr(c_x3_cr),
            .ea_v(1'b0), .ea_kind(1'b0), .ea_addr(24'd0), .ea_cr(), .eq_v(), .eq_d(),
            .ar_v(c_ar_v), .ar_d(c_ar), .ar_cr(c_ar_cr), .dc(c_sd), .dh(c_ds), .pw(c_pw), .kvd(c_kvd),
            .fdi_tx_up(c_pup), .fdi_tx_v(c_ptv), .fdi_tx_flit(c_ptf), .fdi_rx_v(c_prv), .fdi_rx_flit(c_prf),
            .fault(faults_link[0]), .fault_cause(c_fcw));"""
t = t[:a] + new + t[b:]
# the bench's own compute-side retry layer is inside the wrapper now
a = t.index('            ot_qkvd_d2d_llr #(.FW(FW), .MUT(MUT == 4 ? 1 : (MUT == 5 ? 2 : 0))) u_lc (')
b = t.index('.fault(llr_f[0]), .fault_cause(fc0));', a) + len('.fault(llr_f[0]), .fault_cause(fc0));')
t = t[:a] + "            assign llr_f[0] = 1'b0; assign fc0 = 3'd0;   // compute-side llr inside qfd_d2d_rom (its fault -> faults_link[0])" + t[b:]
# the wrapper always carries the llr: the run must be LLR=1; the wiring between the wrapper's PHY side and the PHY model
# moves before the PHY declarations it uses
m = re.search(r'\n(\s*)parameter integer LLR\s*=\s*1;', t)
assert m, 'LLR parameter'
t = t.replace(m.group(0), m.group(0) + '\n' + m.group(1) + 'parameter integer D2D_MUT = 0;', 1)
open(sys.argv[2], 'w').write(t)
PY
P=$(cd "$W/.." && pwd)
K=$W/qwen_sys/kv_die_20261009
SRC="$OUT/tb_d2d.sv $W/qwen_split/qfd_link_slots.sv \
 $W/qwen_sys/split_20261014/ot_qwen_split_lvl.sv $W/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv \
 $W/qwen_sys/split_20261014/ot_qfd_split_romlink.sv \
 $K/ot_qkvd_fifo.sv $K/ot_qkvd_fifo_sb.sv $K/ot_qkvd_fifo_sl.sv $K/ot_qkvd_buf_tiles.sv $K/ot_qkvd_d2d.sv \
 $K/ot_qkvd_rom_end.sv $K/ot_qkvd_kv_end.sv $K/ot_qkvd_ke_cluster.sv $K/ot_qkvd_ke_tiles.sv \
 $W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $K/ot_qkvd_kv_seq_merged.sv $K/ot_qkvd_kv_desc.sv $W/qwen_sys/system_20261008/ot_qfd_dctl.sv \
 $W/lib/ot_rst_relay.sv $W/hdc/ot_hdc_delay.sv \
 $P/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
 $P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
iverilog -g2012 -s tb_qwen_split_link -Ptb_qwen_split_link.LLR=1 "$@" -o $OUT/tb.vvp $SRC > $OUT/build.log 2>&1 || { head -40 $OUT/build.log; exit 2; }
vvp -n $OUT/tb.vvp > $OUT/run.log 2>&1 || true
grep -E "SPLIT_LINK_(PASS|FAIL)" $OUT/run.log | tail -1
