`timescale 1ns/1ps
// Equivalence bench top: the pipelined exp / reciprocal against the qualified short pipelines on the same input stream.
module ot_qwen_nearhbm_sfu_equiv_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] eq_y, ep_y, rq_y, rp_y,
    output wire        eq_v, ep_v, rq_v, rp_v,
    output wire        eq_f, ep_f, rq_f, rp_f
);
    ot_hdc_exp_q            u_eq (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(eq_y), .vo(eq_v), .fault(eq_f));
    ot_qwen_nearhbm_exp_p   u_ep (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(ep_y), .vo(ep_v), .fault(ep_f));
    ot_hdc_recip_q          u_rq (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(rq_y), .vo(rq_v), .fault(rq_f));
    ot_qwen_nearhbm_recip_p u_rp (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(rp_y), .vo(rp_v), .fault(rp_f));
endmodule
