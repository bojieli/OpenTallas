`timescale 1ns/1ps
// Two existing selector edges; dense leaves, <=16 select bits per final kept selector (<=32 mapped loads).
// SVCATT 10-21: the earlier LIVE-compacted form ($countones over a 1060-bit parameter slice) crashes yosys 0.68
// (SIGSEGV in AST derive of ot_hdc_v41x_attn_s); the function is unchanged: every bit takes bank1 iff the
// source select two edges earlier (same two edges) was 1.  Unconsumed bits are pruned by synthesis, so LIVE is
// only kept as an interface parameter.
module ot_hdc_v41x_stagepick_n32 #(parameter integer W=1,parameter[W-1:0]LIVE={W{1'b1}})(
 input wire clk,input wire source_select,legacy_select,input wire[W-1:0]bank0,bank1,output wire[W-1:0]word_out);
 localparam integer N=(W+15)/16,C=(N+31)/32;
 wire[C-1:0]early;wire[N-1:0]late;
 for(genvar c=0;c<C;c=c+1)begin:g_cohort
  ot_hdc_v41x_kreg #(.W(1),.R(0))u_first(.clk(clk),.rst_n(1'b1),.d(source_select),.q(early[c]));
 end
 for(genvar s=0;s<N;s=s+1)begin:g_leaf
  ot_hdc_v41x_kreg #(.W(1),.R(0))u_second(.clk(clk),.rst_n(1'b1),.d(early[s/32]),.q(late[s]));
 end
 for(genvar b=0;b<W;b=b+1)begin:g_bit
  assign word_out[b]=late[b/16]?bank1[b]:bank0[b];
 end
endmodule
