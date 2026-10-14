(* blackbox *) module ot_hgi_hc_lane_sl #(
    parameter integer LM = 5, LA = 6, LMS = 6, ML = 7, AL = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_sw,
    input  wire [159:0]  i_op,               // {r3, r2, r1, r0, y} = op[4..0] of element e
    input  wire [159:0]  i_cf,               // {p, c3, c2, c1, c0} of row kk
    input  wire          i_mx,
    input  wire [127:0]  i_pre,
    input  wire          i_xov,
    input  wire [31:0]   i_xo,
    input  wire [31:0]   i_rh,
    input  wire          i_wov,
    input  wire [31:0]   i_wo,
    output reg           o_hv,
    output reg  [31:0]   o_ho,
    output reg           o_hf,
    output reg  [31:0]   o_xl,
    output reg           o_mf,
    output reg  [31:0]   o_sq,
    output reg           o_sf,
    output reg  [31:0]   o_qq,
    output reg           o_f1,
    output reg           o_f2
);
endmodule
