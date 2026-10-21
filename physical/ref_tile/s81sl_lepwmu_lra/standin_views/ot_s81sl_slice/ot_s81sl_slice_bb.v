// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind
(* blackbox *) module ot_s81sl_slice (
    input wire clk,
    input wire rst_n,
    input wire [3:0] sid,
    input wire [1103:0] ri_w,
    input wire [1103:0] ri_e,
    output wire [1103:0] ro_e,
    output wire [1103:0] ro_w,
    input wire [275:0] vi,
    output wire [275:0] vo,
    input wire [1103:0] bi,
    output wire [512:0] bo,
    output wire [4415:0] xc,
    input wire [559:0] rt,
    output wire [15:0] ck_line,
    output wire [1:0] ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0] ck_rt,
    output wire fault
);
endmodule
