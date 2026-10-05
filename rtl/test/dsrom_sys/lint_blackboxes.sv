// Port-exact blackboxes of the field's submodules (pair, return node, root) for the structural lint of
// ot_v41_field_w17w10 / ot_v41_field_w17w10_sys (run_field_sys_bench.py: yosys 'check' lists every undriven bit).
(* blackbox *) module ot_v41_pair_w17w10 #(parameter integer NSEG=8, NCH=16, XF=4, LV=5, BF16=0, MTP=1, EARLY=1, FAST=0, PP=0, BP=0, PHW=6, parameter INSTANCE="") (
 input wire clk, rst_n, cfg_go, input wire [PHW-1:0] cfg_ph, input wire [2:0] cfg_np, input wire go, go_bf, xs_v,
 input wire [7:0] xs_p, input wire [2:0] xs_b, input wire [1:0] xs_sv, input wire [255:0] xs_q0, input wire [9:0] xs_e0,
 input wire [255:0] xs_q1, input wire [9:0] xs_e1, input wire [2:0] xs_pos, xb_pos, input wire xb_v, input wire [2:0] xb_b,
 input wire [3:0] xb_sv, input wire [31:0] xb_u, input wire [1023:0] xb_d,
 output wire [1:0] pv, output wire [63:0] pval, output wire [31:0] prow, output wire [9:0] pseg, pnseg, output wire [1:0] perr,
 output wire [5:0] ppos, output wire busy, fault, quiet);

endmodule
(* blackbox *) module ot_v41_retn_w17w10 #(parameter integer RD=64, RST=1, BYPASS=1) (input wire clk, rst_n, a_v, input wire [31:0] a_t, a_d, input wire a_e, b_v, input wire [31:0] b_t, b_d, input wire b_e, output wire o_v, output wire [31:0] o_t, o_d, output wire o_e, fault, quiet); endmodule
(* blackbox *) module ot_v41_ret_root #(parameter integer D=16, QD=16) (input wire clk, rst_n, i_v, input wire [31:0] i_t, i_d, input wire i_e, output wire r_v, output wire [15:0] r_row, output wire [2:0] r_pos, output wire [31:0] r_fp32, output wire [15:0] r_bf16, output wire r_e, fault); endmodule
