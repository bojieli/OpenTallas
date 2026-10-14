`timescale 1ns/1ps
// One true own-flop lane of the original NC8 ordered FP32 tree (7 adders).
// The original pairing and LAT stay fixed. One request capture and one reply
// publication edge are explicit; parent reduction/index accounting must adopt
// both before this native hard interface can replace the retained tree.
module ot_hcoll_reduce_lane8 #(parameter integer LAT=7,MUT=0)(
 input wire clk,rst_n,valid,input wire[255:0]operands,input wire[15:0]index,
 output reg reply_v,output reg[31:0]reply,output reg[15:0]reply_index,output reg[1:0]reply_err
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg[255:0]pin_data;reg[15:0]pin_index;reg pin_v;
 always @(posedge clk)begin pin_data<=operands;pin_index<=index;end
 always @(posedge clk or negedge rr[0])if(!rr[0])pin_v<=0;else pin_v<=valid;
 wire[31:0]l1[0:3],l2[0:1],l3;wire[3:0]v1;wire[1:0]v2;wire v3;
 wire[1:0]e1[0:3],e2[0:1],e3;
 for(genvar a=0;a<4;a=a+1)begin:g_l1
  ot_hdc_fp32_add_lat #(.LAT(LAT))u_add(.clk(clk),.rst_n(rr[0]),.valid_in(pin_v),
   .a(pin_data[64*a+:32]),.b(pin_data[64*a+32+:32]),.y(l1[a]),.err(e1[a]),.valid_out(v1[a]));
 end
 for(genvar a=0;a<2;a=a+1)begin:g_l2
  ot_hdc_fp32_add_lat #(.LAT(LAT))u_add(.clk(clk),.rst_n(rr[0]),.valid_in(v1[2*a]),
   .a(l1[2*a]),.b(l1[2*a+1]),.y(l2[a]),.err(e2[a]),.valid_out(v2[a]));
 end
 ot_hdc_fp32_add_lat #(.LAT(LAT))u_l3(.clk(clk),.rst_n(rr[0]),.valid_in(v2[0]),
  .a(l2[0]),.b(l2[1]),.y(l3),.err(e3),.valid_out(v3));
 reg[15:0]idx[0:3*LAT-1];
 always @(posedge clk)begin
  idx[0]<=pin_index;for(integer d=1;d<3*LAT;d=d+1)idx[d]<=idx[d-1];
  reply<=(MUT==1)?(l3^32'd1):l3;reply_index<=idx[3*LAT-1];reply_err<=e3;
 end
 always @(posedge clk or negedge rr[0])if(!rr[0])reply_v<=0;else reply_v<=v3;
endmodule
