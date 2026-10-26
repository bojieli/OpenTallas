`timescale 1ns/1ps
// Opt-in FILE-LIST selection only: replace ot_qw_land4.sv by this file plus ot_qw_land4_n32.sv.
// Original production files/default lists untouched; external names/ports/chunk-valid ABI preserved.
module ot_qw_lw #(parameter W=128,D=4,CB=24,C=(W+CB-1)/CB)(input ck,rsi,input [W-1:0] i,output [D*W-1:0] bank,output [D*C-1:0] vld);
 ot_qw_lw_n32 #(.W(W),.D(D),.CB(CB),.C(C)) u_safe(.*);
endmodule
module ot_qw_lr #(parameter W=128,D=4,K=2,CB=24,C=(W+CB-1)/CB,AW=(D<=2)?1:$clog2(D))(input ck,rsi,input [D*W-1:0] bank,input [D*C-1:0] vld,output [W-1:0] o);
 ot_qw_lr_n32 #(.W(W),.D(D),.K(K),.CB(CB),.C(C),.AW(AW)) u_safe(.*);
endmodule
module ot_qw_ring_delay #(parameter W=128,D=3,CB=16,C=(W+CB-1)/CB)(input clk,rst_n,input [W-1:0] d,output [W-1:0] q);
 ot_qw_ring_delay_n32 #(.W(W),.D(D),.CB(CB),.C(C)) u_safe(.*);
endmodule
