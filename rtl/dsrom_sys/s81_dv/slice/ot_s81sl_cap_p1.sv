`timescale 1ns/1ps
`default_nettype none
// Optional native boundary pipeline around the immutable hardened capture core.
// PINPIPE=0 preserves its original contract. PINPIPE=1 adds one coherent input
// edge and one coherent output edge, with identical sustained item rate.
module ot_s81sl_cap_p1 #(parameter integer PINPIPE=0, parameter integer MUT=0) (
 input wire clk, rst_n,
 input wire [279:0] rt_w,rt_e,
 input wire cfg_v, input wire [159:0] cfg_d,
 output wire [5:0] cw_s_v, output wire [71:0] cw_s_a, output wire [191:0] cw_s_d,
 output wire [3:0] cw_n_v, output wire [47:0] cw_n_a, output wire [127:0] cw_n_d,
 output wire fault
);
 wire [279:0] wi,ei; wire cv; wire [159:0] cd; wire ri;
 wire [5:0] sv; wire [71:0] sa; wire [191:0] sd;
 wire [3:0] nv; wire [47:0] na; wire [127:0] nd; wire fl;
 generate if(PINPIPE) begin:g_pin
   // Only the two reset landing flops see rst_n. Local reset drives 14 loads:
   // three hard-child reset pins plus ten output-valid flops and fault.
   (* async_reg="true", keep="true", dont_touch="true" *) reg rst_l0,rst_l1;
   always @(posedge clk or negedge rst_n)
     if(!rst_n) begin rst_l0<=0; rst_l1<=0; end
     else begin rst_l0<=1; rst_l1<=rst_l0; end
   assign ri=rst_l1;
   // Payload registers need no reset. The core stays reset until both input
   // pipeline and local reset have filled, and validity is reset at the output.
   (* keep="true" *) reg [279:0] wq,eq;
   (* keep="true" *) reg cvq; (* keep="true" *) reg [159:0] cdq;
   always @(posedge clk) begin wq<=rt_w; eq<=rt_e; cvq<=cfg_v; cdq<=cfg_d; end
   assign wi=wq; assign ei=eq; assign cv=(MUT==2)?cfg_v:cvq; assign cd=cdq;
   (* keep="true" *) reg [5:0] svq; (* keep="true" *) reg [3:0] nvq; (* keep="true" *) reg fq;
   (* keep="true" *) reg [71:0] saq; (* keep="true" *) reg [191:0] sdq;
   (* keep="true" *) reg [47:0] naq; (* keep="true" *) reg [127:0] ndq;
   always @(posedge clk) begin saq<=sa; sdq<=sd; naq<=na; ndq<=nd; end
   always @(posedge clk or negedge rst_l1)
     if(!rst_l1) begin svq<=0; nvq<=0; fq<=0; end
     else begin svq<=sv; nvq<=nv; fq<=fl; end
   assign cw_s_v=(MUT==1)?sv:svq; assign cw_n_v=(MUT==1)?nv:nvq;
   assign cw_s_a=saq; assign cw_s_d=sdq; assign cw_n_a=naq; assign cw_n_d=ndq; assign fault=fq;
 end else begin:g_plain
   assign wi=rt_w; assign ei=rt_e; assign cv=cfg_v; assign cd=cfg_d; assign ri=rst_n;
   assign cw_s_v=sv; assign cw_s_a=sa; assign cw_s_d=sd;
   assign cw_n_v=nv; assign cw_n_a=na; assign cw_n_d=nd; assign fault=fl;
 end endgenerate
 ot_s81sl_cap u_core(.clk(clk),.rst_n(ri),.rt_w(wi),.rt_e(ei),.cfg_v(cv),.cfg_d(cd),
   .cw_s_v(sv),.cw_s_a(sa),.cw_s_d(sd),.cw_n_v(nv),.cw_n_a(na),.cw_n_d(nd),.fault(fl));
endmodule
`default_nettype wire
