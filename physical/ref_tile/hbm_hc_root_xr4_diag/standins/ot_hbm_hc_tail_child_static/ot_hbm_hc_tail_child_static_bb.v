// DIAGNOSTIC stand-in blackbox (tools/qwen_dv/slice_standin.py); never bind
(* blackbox *) module ot_hbm_hc_tail_child_static (
    input wire clk,
    input wire rst_n,
    input wire launch,
    input wire [767:0] mixes,
    input wire [767:0] bases,
    input wire [95:0] scales,
    output wire result_v,
    output wire [767:0] result,
    output wire fault
);
endmodule
