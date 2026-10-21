// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind
(* blackbox *) module ot_s81sl_ve (
    input wire clk,
    input wire rst_n,
    input wire r_v,
    input wire [1:0] r_c,
    input wire [127:0] r_h,
    input wire [127:0] r_k,
    input wire [127:0] r_w,
    output wire p_v,
    output wire [1:0] p_c,
    output wire [31:0] p_hh,
    output wire [31:0] p_kk,
    output wire [31:0] p_dd,
    input wire a_v,
    input wire [1:0] a_c,
    input wire [255:0] a_h,
    input wire [255:0] a_val,
    input wire [31:0] a_g,
    output wire o_v,
    output wire [1:0] o_c,
    output wire [255:0] o_y,
    output wire fault
);
endmodule
