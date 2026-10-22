`timescale 1ns/1ps
`default_nettype none
// Diagnostic source-clock forwarding of all four bank slots AND written flags.
// Same nominal reset epoch as source writer. No read schedule adoption implied:
// shifted window is (K-1)T+phi setup and (D-K+1)T-phi overwrite gap.
(* keep_hierarchy="yes" *)
module qfd_c_bank_flags_safe22(input wire ck,rst_l0,input wire[21:0]vld,output wire[21:0]qvld);
 (* keep=1 *)reg r2;
 (* keep=1 *)reg[21:0]flags;
 always@(posedge ck)begin
  r2<=rst_l0;
  if(!r2)flags<=0;else flags<=vld;
 end
 assign qvld=flags;
endmodule
module qfd_c_bank_forward_safe #(parameter W=258)(
 input wire ck,rsi,input wire[4*W-1:0]bank,input wire[43:0]vld,
 output reg[4*W-1:0]qbank,output wire[43:0]qvld);
 (* keep=1 *)reg rst_l0;
 always@(posedge ck)begin rst_l0<=rsi;qbank<=bank;end
 genvar j;
 generate for(j=0;j<2;j=j+1)begin:g
  qfd_c_bank_flags_safe22 u(ck,rst_l0,vld[22*j+:22],qvld[22*j+:22]);
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<257||W>258)$fatal(1,"unsupported bank-forward shape");
`endif
endmodule
module qfd_c_bank_fwd258_safe(input wire ck,rsi,input wire[515:0]bank_w,bank_e,input wire[43:0]vld,
 output wire[515:0]qbank_w,qbank_e,output wire[43:0]qvld);
 qfd_c_bank_forward_safe #(.W(258))u(ck,rsi,{bank_e,bank_w},vld,{qbank_e,qbank_w},qvld);
endmodule
`default_nettype wire
