`timescale 1ns/1ps
// hgi-1010/g2: the heap engine (ot_hgi_idx_topk_heap.sv) behind the historical ot_hgi_idx_topk name and ports; a build
// lists this file INSTEAD of ot_hgi_idx_topk.sv (the flop sorter), plus ot_hgi_idx_topk_heap.sv and rtl/lib/ot_rst_relay.sv.
// Drop-in core: the historical one-score-a-cycle port (IW 1, W 2 heaps).
module ot_hgi_idx_topk #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048,
 parameter bit MUTANT_TIE=0,
 parameter integer RST_RELAY=0,                     // accepted for wrapper compatibility (no reset net spans an array here)
 parameter integer W=`ifdef OT_TOPK_HEAP_W `OT_TOPK_HEAP_W `else 2 `endif,
 parameter integer MUT_BYP=`ifdef OT_TOPK_HEAP_MUT_BYP 1 `else 0 `endif,
 parameter integer MUT_CLR=`ifdef OT_TOPK_HEAP_MUT_CLR 1 `else 0 `endif,
 parameter integer MUT_REV=`ifdef OT_TOPK_HEAP_MUT_REV 1 `else 0 `endif
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [31:0] in_score,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output wire done, output wire [3:0] error
);
 ot_hgi_idx_topk_hw #(.ENABLE(ENABLE), .MAX_K(MAX_K), .MUTANT_TIE(MUTANT_TIE), .IW(1), .W(W), .MUT_BYP(MUT_BYP),
  .MUT_CLR(MUT_CLR), .MUT_REV(MUT_REV)) u (.clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_unit(cmd_unit),
  .cmd_op(cmd_op), .cmd_param(cmd_param), .cmd_n(cmd_n), .cmd_m(cmd_m), .cmd_values(cmd_values), .in_valid(in_valid),
  .in_ready(in_ready), .in_score(in_score), .in_nw(1'b1), .out_valid(out_valid), .out_ready(out_ready), .out_id(out_id),
  .out_score(out_score), .out_row(out_row), .out_last(out_last), .out_values_valid(out_values_valid), .done(done),
  .error(error));
endmodule
