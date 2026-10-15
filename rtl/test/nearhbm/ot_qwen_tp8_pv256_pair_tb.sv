`timescale 1ns/1ps
// Opt-in raw-row candidate, one pair owns 128 canonical c residues.
// Rows are n-major, c-minor, preserving each c's serial FP32 addition order.
// Readout occurs after drain; retained SRAM supplies stable backpressured leaves.
module ot_qwen_tp8_pv256_pair_tb #(parameter integer PAIR=0, parameter integer TREE=0,
 parameter integer STATIC_SCHEDULE=0,parameter integer FIRST_INPUT_AGE=146)(
 input wire clk,rst_n,start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire in_valid,output wire in_ready,input wire[1023:0] in_v,input wire[63:0] in_e,
 input wire[6:0] in_c,input wire[13:0] in_t,input wire[15:0] in_epoch,
 input wire in_first,in_last,
 output wire out_valid,input wire out_ready,output wire[16383:0] out_leaf,
 output wire[6:0] out_c,output wire[15:0] out_epoch,
 output reg fault,output wire busy,output reg[31:0] accepted,committed,
 output reg[7:0] peak_inflight
);
// Simulation-only adapter: all independent related roots have equal phase.
 ot_qwen_tp8_pv256_pair #(.PAIR(PAIR),.TREE(TREE),.STATIC_SCHEDULE(STATIC_SCHEDULE),
  .FIRST_INPUT_AGE(FIRST_INPUT_AGE)) u_pair(.slice_clk({32{clk}}),.*);
endmodule
