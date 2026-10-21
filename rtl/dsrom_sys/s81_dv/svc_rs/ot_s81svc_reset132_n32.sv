`timescale 1ns/1ps
// Exact G4 active transpose forest:194 plain FF+264 exact controller ASR FF.
module ot_s81svc_reset3_used #(parameter integer W=8,SHORT=0)(input wire clk,d,output wire[W-1:0]q);
 wire a,b;
 ot_hdc_v41x_kreg #(.W(1),.R(0))u_a(.clk(clk),.rst_n(1'b1),.d(d),.q(a));
 ot_hdc_v41x_kreg #(.W(1),.R(0))u_b(.clk(clk),.rst_n(1'b1),.d(a),.q(b));
 if(SHORT==0)begin:g_full
  ot_hdc_v41x_kreg #(.W(W),.R(0))u_q(.clk(clk),.rst_n(1'b1),.d({W{b}}),.q(q));
 end else begin:g_short assign q={W{b}};end
endmodule
module ot_s81svc_reset132_n32 #(parameter integer MUT=0)(input wire clk,reset_early9,output wire[131:0]reset_leaf);
 wire[2:0]roots;wire[131:0]pre;
 ot_s81svc_reset3_used #(.W(3))u_root(.clk(clk),.d(reset_early9),.q(roots));
 for(genvar a=0;a<3;a=a+1)begin:g_root
  localparam integer MW=(a<2)?8:1;
  wire[MW-1:0]mid;
  ot_s81svc_reset3_used #(.W(MW))u_mid(.clk(clk),.d(roots[a]),.q(mid));
  for(genvar b=0;b<MW;b=b+1)begin:g_mid
   localparam integer BASE=64*a+8*b,LW=(BASE+8<=132)?8:132-BASE;
   ot_s81svc_reset3_used #(.W(LW),.SHORT((MUT==1&&a==0&&b==0)?1:0))u_leaf(.clk(clk),.d(mid[b]),.q(pre[BASE+:LW]));
  end
 end
 for(genvar k=0;k<132;k=k+1)begin:g_asr
  (* keep="true" *)reg[1:0]rs;
  always@(posedge clk or negedge pre[k])if(!pre[k])rs<=0;else rs<={rs[0],1'b1};
  assign reset_leaf[k]=rs[1];
 end
endmodule
