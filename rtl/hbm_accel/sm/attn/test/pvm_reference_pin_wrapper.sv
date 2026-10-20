`timescale 1ns/1ps
`default_nettype none
module ot_pvm_reference_pin_wrapper #(parameter integer MUT=0)(
 input wire clk,rst_n,ev,input wire [511:0] sum,input wire [15:0] tag_d,
 output reg pv_v,output reg [511:0] pv_y,output reg [15:0] pv_tag,output reg fault,
 input wire pub_start,input wire [2:0] pub_slot,
 output reg pub_v,output reg [31:0] pub_data,output reg [3:0] pub_word,
 output reg [2:0] pub_out_slot,output reg [15:0] pub_tag,
 input wire fold_start,input wire [2:0] fold_a,fold_b
);
 reg r0,r1;
 always @(posedge clk or negedge rst_n) if(!rst_n) r0<=0;else r0<=1;
 always @(posedge clk or negedge r0) if(!r0) r1<=0;else r1<=1;
 reg ev1,pub1,fold1;reg[511:0]sum1;reg[15:0]tag1;reg[2:0]ps1,fa1,fb1;
 always @(posedge clk or negedge r1) if(!r1) begin ev1<=0;pub1<=0;fold1<=0;end else begin ev1<=ev;pub1<=pub_start;fold1<=fold_start;end
 always @(posedge clk)begin sum1<=sum;tag1<=tag_d;ps1<=pub_slot;fa1<=fold_a;fb1<=fold_b;end
 wire cpv,cpub,cf;wire[511:0]cy;wire[15:0]ct,cpt;wire[31:0]cd;wire[3:0]cw;wire[2:0]cs;
 ot_hbm_sm_pv_merge_s3 #(.TAGW(16),.LV(4),.MUT(MUT),.PUBLISH(1),.TURNREG(1),.SAFE(2)) u_core(
 .clk(clk),.rst_n(r1),.ev(ev1),.sum(sum1),.tag_d(tag1),.pv_v(cpv),.pv_y(cy),.pv_tag(ct),.fault(cf),
 .pub_start(pub1),.pub_slot(ps1),.pub_v(cpub),.pub_data(cd),.pub_word(cw),.pub_out_slot(cs),.pub_tag(cpt),
 .fold_start(fold1),.fold_a(fa1),.fold_b(fb1));
 wire[2:0]bp=u_core.bp+3'd1;
 always @(posedge clk) begin pv_y<=cy;pv_tag<=ct;pub_data<=cd;pub_word<=cw;pub_out_slot<=cs;pub_tag<=cpt;end
 always @(posedge clk or negedge r1)if(!r1)begin pv_v<=0;pub_v<=0;fault<=0;end else begin pv_v<=cpv;pub_v<=cpub;fault<=cf;end
endmodule
`default_nettype wire
