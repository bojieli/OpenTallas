`timescale 1ns/1ps
// Route top for the feasibility fixes: ot_hbm_norm_engine_view with RLY=1 XST=1.  A separate top (same ports) instead of
// VERILOG_TOP_PARAMS, because ORFS hierarchical synthesis (SYNTH_HIERARCHICAL=1) throws in its KEEP_HIERARCHY pass on a
// parameter-overridden top (hbm-norm-rly-xst-pm1400a/b-d0e50cc63 calibrate, 1_2_yosys.log).
module ot_hbm_norm_engine_view_rx (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 go,
    input  wire                 in_v,
    input  wire [4*64*32-1:0]   in_x,
    input  wire [127:0]         pre,
    input  wire [31:0]          n_f,
    input  wire [31:0]          eps,
    input  wire                 wl_v,
    input  wire [7:0]           wl_i,
    input  wire [64*32-1:0]     wl_d,
    input  wire [31:0]          cos_t,
    input  wire [31:0]          sin_t,
    output wire                 y_v,
    output wire [7:0]           y_i,
    output wire [64*32-1:0]     y,
    output wire                 r_v,
    output wire [31:0]          r,
    output wire                 q_v,
    output wire [7:0]           q_i,
    output wire [2*256-1:0]     q_codes,
    output wire [2*10-1:0]      q_e,
    output wire [2*512-1:0]     q_y,
    output wire                 ro_v,
    output wire [64*32-1:0]     ro,
    output wire                 fault
);
    ot_hbm_norm_engine_view #(.RLY(1), .XST(1)) u_view (.clk(clk), .rst_n(rst_n), .go(go), .in_v(in_v), .in_x(in_x), .pre(pre), .n_f(n_f), .eps(eps), .wl_v(wl_v), .wl_i(wl_i), .wl_d(wl_d), .cos_t(cos_t), .sin_t(sin_t), .y_v(y_v), .y_i(y_i), .y(y), .r_v(r_v), .r(r), .q_v(q_v), .q_i(q_i), .q_codes(q_codes), .q_e(q_e), .q_y(q_y), .ro_v(ro_v), .ro(ro), .fault(fault));
endmodule
