`timescale 1ns/1ps
// Source candidate: replace nine existing SAME-CLOCK plain reset-pad edges.
// Both assertion and release propagate in nine edges; no asynchronous shortcut.
// Actual LP composition must feed this after prefix2, replacing its former4+7
// pad age11. Never append nine edges to an existing child reset or alias clocks.
module ot_s81svc_reset3_branch8 #(parameter integer SHORT=0)(
 input wire clk,input wire d,output wire[7:0]q);
 wire a,b;
 ot_hdc_v41x_kreg #(.W(1),.R(0))u_a(.clk(clk),.rst_n(1'b1),.d(d),.q(a));
 ot_hdc_v41x_kreg #(.W(1),.R(0))u_b(.clk(clk),.rst_n(1'b1),.d(a),.q(b));
 generate if(SHORT==0)begin:g_full
  ot_hdc_v41x_kreg #(.W(8),.R(0))u_q(.clk(clk),.rst_n(1'b1),.d({8{b}}),.q(q));
 end else begin:g_short
  assign q={8{b}};
 end endgenerate
endmodule
module ot_s81svc_reset9_n32 #(parameter integer MUT=0)(
 input wire clk,input wire reset_early9,output wire[511:0]reset_leaf);
 wire[7:0]r0;wire[63:0]r1;
 ot_s81svc_reset3_branch8 u_root(.clk(clk),.d(reset_early9),.q(r0));
 for(genvar a=0;a<8;a=a+1)begin:g_a
  ot_s81svc_reset3_branch8 u_mid(.clk(clk),.d(r0[a]),.q(r1[8*a+:8]));
  for(genvar b=0;b<8;b=b+1)begin:g_b
   ot_s81svc_reset3_branch8 #(.SHORT((MUT==1&&a==0&&b==0)?1:0))u_leaf
    (.clk(clk),.d(r1[8*a+b]),.q(reset_leaf[64*a+8*b+:8]));
  end
 end
endmodule

// Exact controller u_rl reset semantics after nine plain landing edges:
// asynchronous assertion, two-clock deassertion. No initialized values assumed.
module ot_s81svc_reset9_rl2_n32(input wire clk,reset_early9,output wire[511:0]reset_leaf);
 wire[511:0]pre;
 ot_s81svc_reset9_n32 u_pre(.clk(clk),.reset_early9(reset_early9),.reset_leaf(pre));
 ot_s81svc_reset_rl2_n32 u_leaf(.clk(clk),.pre(pre),.reset_leaf(reset_leaf));
endmodule
module ot_s81svc_reset_rl2_n32(input wire clk,input wire[511:0]pre,output wire[511:0]reset_leaf);
 for(genvar k=0;k<512;k=k+1)begin:g_leaf
  (* keep = "true" *)reg[1:0]rs;
  always@(posedge clk or negedge pre[k])if(!pre[k])rs<=2'b00;else rs<={rs[0],1'b1};
  assign reset_leaf[k]=rs[1];
 end
endmodule
