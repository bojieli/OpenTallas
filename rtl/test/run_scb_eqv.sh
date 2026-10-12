#!/bin/bash
# el1011-q-seq (2026-10-11): formal sequential equivalence of the spctl SC (b) mx write (registered slot maximum with write
# forwarding, pre-decoded lane rotate) against the original (SC 0) -- the RTL text itself: the slot-maximum / mx-write
# segment of ot_qwen_me_spctl_w12 (from 'reg [31:0] rk [0:IL-1];' to the end of the g_scb / g_nscb generate) is extracted
# and included twice in a wrapper (W 16, IL 8, AW 24, LV 10, PK 1 as ctlm_i's u_tt) whose tree top (valid, key), tree
# valid tv[LV] (0 in reset, as its async-reset register), async reset and ring output ttag_e (ttag = ttag_e one edge later, as g_ttreg) are free inputs.  Miter:
# mx_we / mx_addr / mx_mask / mx_data equal every cycle (with the slot-maximum invariant), from the all-zero state, by
# k-induction (yosys sat -tempinduct).
# usage: run_scb_eqv.sh <outdir> <SC of the copy: 1 exact | 3 mutant (no forwarding)>
set -e
O=$1; M=$2; mkdir -p "$O"
S=rtl/hdc/ot_qwen_me_spine_h_w12.sv
awk '/^    reg \[31:0\] rk \[0:IL-1\];/{on=1} on{print} on&&/g_nscb/{nb=1} on&&nb&&/end endgenerate/{exit}' $S > "$O/scb_seg.vh"
grep -q g_scb "$O/scb_seg.vh" && grep -q g_nscb "$O/scb_seg.vh"
cat > "$O/scb_chk_$M.v" <<V
module mxw #(parameter integer SC = 0) (input clk, input rst_n, input tvl, input top_v, input [31:0] top_key,
        input [1+3+1+24-1:0] ttag_e, output reg mx_we, output reg [23:0] mx_addr, output reg [15:0] mx_mask,
        output reg [16*32-1:0] mx_data, output [8*32-1:0] rko, output [7:0] rso, output [31:0] rkj, output rsj,
        output [2:0] tj, output [28:0] tq);
    localparam integer W = 16, IL = 8, LW = 4, AW = 24, LV = 10, PK = 1;
    localparam integer LVT = LV;   // AMI: the tree-top valid tap (LV + 1 under AMI 1); the tap is a free input here
    wire [LVT:0] tv = {tvl && rst_n, {LVT{1'b0}}};   // tv is an async-reset register in the RTL: 0 while rst_n is low
    reg  [1+3+1+AW-1:0] ttag_q;
    always @(posedge clk) ttag_q <= ttag_e;
    wire [1+3+1+AW-1:0] ttag = ttag_q, ttag_ew = ttag_e;
    wire t_rmax, t_opend; wire [2:0] t_j; wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
    wire [31:0] rk_jx; wire rseen_jx;
\`include "scb_seg.vh"
    assign rko = {rk[7], rk[6], rk[5], rk[4], rk[3], rk[2], rk[1], rk[0]};
    assign rso = rseen; assign rkj = rk_jx; assign rsj = rseen_jx; assign tj = t_j; assign tq = ttag_q;
endmodule
module chk(input clk, input rst_n, input tvl, input top_v, input [31:0] top_key, input [28:0] ttag_e, output ok);
    wire a_we, b_we; wire [23:0] a_ad, b_ad; wire [15:0] a_m, b_m; wire [511:0] a_d, b_d;
    wire [255:0] a_rk, b_rk; wire [7:0] a_rs, b_rs; wire [31:0] a_kj, b_kj; wire a_sj, b_sj; wire [2:0] a_tj, b_tj; wire [28:0] a_tq, b_tq;
    mxw #(.SC(0)) u_a (.clk(clk), .rst_n(rst_n), .tvl(tvl), .top_v(top_v), .top_key(top_key), .ttag_e(ttag_e), .mx_we(a_we), .mx_addr(a_ad), .mx_mask(a_m), .mx_data(a_d), .rko(a_rk), .rso(a_rs), .rkj(a_kj), .rsj(a_sj), .tj(a_tj), .tq(a_tq));
    mxw #(.SC($M)) u_b (.clk(clk), .rst_n(rst_n), .tvl(tvl), .top_v(top_v), .top_key(top_key), .ttag_e(ttag_e), .mx_we(b_we), .mx_addr(b_ad), .mx_mask(b_m), .mx_data(b_d), .rko(b_rk), .rso(b_rs), .rkj(b_kj), .rsj(b_sj), .tj(b_tj), .tq(b_tq));
    // outputs equal, plus the inductive invariant: same slot maxima / seen bits / tag, and the SC copy's registered
    // slot maximum equal to rk[t_j] / rseen[t_j] (so the proof closes at induction length 1)
    assign ok = (a_we == b_we) && (a_ad == b_ad) && (a_m == b_m) && (a_d == b_d) && (a_rk == b_rk) && (a_rs == b_rs) &&
                (a_tq == b_tq) && (b_kj == b_rk[32*b_tj +: 32]) && (b_sj == b_rs[b_tj]);
endmodule
V
Y=${YOSYS:-yosys}
if (cd "$O" && "$Y" -q -p "read_verilog -sv $OLDPWD/rtl/hdc/ot_qwen_w12_arith.sv scb_chk_$M.v; prep -top chk; flatten; memory_map; opt_clean; async2sync; dffunmap; sat -tempinduct -prove ok 1 -set-init-zero -seq 1 -maxsteps 4 -verify" > "scb_eqv_$M.log" 2>&1); then
    echo "PASS scb_eqv SC=$M (mx write == SC 0 every cycle, k-induction)"
else
    echo "FAIL scb_eqv SC=$M"; exit 1
fi
