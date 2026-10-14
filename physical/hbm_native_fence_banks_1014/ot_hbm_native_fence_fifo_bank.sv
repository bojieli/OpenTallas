`timescale 1ns/1ps
// Actual storage/control factor of the recovered closed FIFO. The parent owns
// pointers/occupancy and registered pin capture. Every bank output is a flop Q;
// read selection remains the unchanged AND-OR in the parent. No latency added.
(* keep_hierarchy *)
module ot_hbm_native_fence_fifo_bank #(parameter integer W=128,S=2)(
 input wire clk,rst_n,
 input wire [W-1:0] din,
 input wire [S-1:0] write_next,read_next,
 output wire [S*W-1:0] slots,
 output wire [S-1:0] read_select
);
 for(genvar i=0;i<S;i=i+1) begin:g_s
  wire write_enable;
  reg [W-1:0] data;
  ot_sc_rep_ff #(.RV(i==0)) u_we(.clk(clk),.rst_n(rst_n),.d(write_next[i]),.q(write_enable));
  ot_sc_rep_ff #(.RV(i==0)) u_rs(.clk(clk),.rst_n(rst_n),.d(read_next[i]),.q(read_select[i]));
  always @(posedge clk) if(write_enable) data<=din;
  assign slots[i*W+:W]=data;
 end
endmodule
