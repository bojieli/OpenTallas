`timescale 1ns/1ps
`default_nettype none
// PRIVATE candidate. Source-owned input and output registers; disable automatic pin regs.
module ot_hbm_sm_pv_merge_distributed #(parameter integer MUT=0)(
 input wire clk,rst_n,ev,input wire [511:0] sum,input wire [15:0] tag_d,
 output reg pv_v,output reg [511:0] pv_y,output reg [15:0] pv_tag,output reg fault,
 input wire pub_start,input wire [2:0] pub_slot,
 output reg pub_v,output reg [31:0] pub_data,output reg [3:0] pub_word,
 output reg [2:0] pub_out_slot,output reg [15:0] pub_tag,
 input wire fold_start,input wire [2:0] fold_a,fold_b
);
 wire [1:0] reset_first_n; wire [7:0] reset_second_n; wire [51:0] reset_core_n;
 generate
 for(genvar ri=0;ri<2;ri=ri+1) begin:g_reset_first
  ot_pvm_reset_release #(.ID(ri)) u(.clk(clk),.rn(rst_n),.q(reset_first_n[ri]));
 end
 for(genvar ri=0;ri<8;ri=ri+1) begin:g_reset_second
  ot_pvm_reset_release #(.ID(2+ri)) u(.clk(clk),.rn(reset_first_n[ri/4]),.q(reset_second_n[ri]));
 end
 for(genvar ri=0;ri<52;ri=ri+1) begin:g_reset_core
  ot_pvm_reset_release #(.ID(10+ri)) u(.clk(clk),.rn(reset_second_n[ri/8]),.q(reset_core_n[ri]));
 end
 endgenerate
 wire [3:0] ev1; wire [96:0] ev2; wire first1; wire [31:0] first2;
 generate
 for(genvar ei=0;ei<4;ei=ei+1) begin:g_event_first
  ot_pvm_capture #(.ID(ei),.RESET(1)) u(.clk(clk),.rn(reset_second_n[ei]),.d(ev),.q(ev1[ei]));
 end
 for(genvar ei=0;ei<97;ei=ei+1) begin:g_event_second
  ot_pvm_capture #(.ID(4+ei),.RESET(1)) u(.clk(clk),.rn(reset_second_n[ei%8]),.d(ev1[ei/25]),.q(ev2[ei]));
 end
 endgenerate
 ot_pvm_capture #(.ID(101)) u_first_tag(.clk(clk),.rn(1'b1),.d(tag_d[14]),.q(first1));
 generate for(genvar ti=0;ti<32;ti=ti+1) begin:g_first_tag
  ot_pvm_capture #(.ID(102+ti)) u(.clk(clk),.rn(1'b1),.d(first1),.q(first2[ti]));
 end endgenerate
 reg [511:0] sum1,sum2; reg [15:0] tag1,tag2;
 reg [2:0] pubslot1,pubslot2,folda1,folda2,foldb1,foldb2;
 reg pub1,pub2,fold1,fold2;
 always @(posedge clk) begin
  sum1<=sum;sum2<=sum1;tag1<=tag_d;tag2<=tag1;
  pubslot1<=pub_slot;pubslot2<=pubslot1;
  folda1<=fold_a;folda2<=folda1;foldb1<=fold_b;foldb2<=foldb1;
 end
 always @(posedge clk or negedge reset_second_n[0])
  if(!reset_second_n[0]) begin pub1<=0;pub2<=0;end else begin pub1<=pub_start;pub2<=pub1;end
 always @(posedge clk or negedge reset_second_n[1])
  if(!reset_second_n[1]) begin fold1<=0;fold2<=0;end else begin fold1<=fold_start;fold2<=fold1;end
 wire cpv,cpub,cfault;wire [511:0] cy;wire [15:0] ctag,cptag;wire[31:0] cdata;wire[3:0] cword;wire[2:0] cslot;
 ot_hbm_sm_pv_merge_distributed_core #(.TAGW(16),.LV(4),.MUT(MUT),.PUBLISH(1),.TURNREG(1),.SAFE(2)) u_core(
  .clk(clk),.rst_core_n(reset_core_n),.ev_operand(ev2[31:0]),.ev_write(ev2[95:32]),.first_operand(first2),
  .ev(ev2[96]),.sum(sum2),.tag_d(tag2),.pv_v(cpv),.pv_y(cy),.pv_tag(ctag),.fault(cfault),
  .pub_start(pub2),.pub_slot(pubslot2),.pub_v(cpub),.pub_data(cdata),.pub_word(cword),.pub_out_slot(cslot),.pub_tag(cptag),
  .fold_start(fold2),.fold_a(folda2),.fold_b(foldb2));
 // Existing one output edge retained. Valid/fault reset distributed in <=32 group.
 always @(posedge clk) begin pv_y<=cy;pv_tag<=ctag;pub_data<=cdata;pub_word<=cword;pub_out_slot<=cslot;pub_tag<=cptag;end
 always @(posedge clk or negedge reset_core_n[15])
  if(!reset_core_n[15]) begin pv_v<=0;pub_v<=0;fault<=0;end
  else begin pv_v<=cpv;pub_v<=cpub;fault<=cfault;end
endmodule
// ID makes every kept copy a distinct paramod; native audit must verify survival.
(* keep_hierarchy="yes" *) module ot_pvm_reset_release #(parameter integer ID=0)(input wire clk,rn,output reg q);
 (* keep *) wire d=1'b1;
 always @(posedge clk or negedge rn) if(!rn) q<=1'b0;else q<=d;
endmodule
(* keep_hierarchy="yes" *) module ot_pvm_capture #(parameter integer ID=0,RESET=0)(input wire clk,rn,d,output reg q);
 generate if(RESET) begin:g_reset
  always @(posedge clk or negedge rn) if(!rn) q<=0;else q<=d;
 end else begin:g_data
  always @(posedge clk) q<=d;
 end endgenerate
endmodule
`default_nettype wire
