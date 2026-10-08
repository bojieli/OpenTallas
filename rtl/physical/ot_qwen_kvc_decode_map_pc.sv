`timescale 1ns/1ps
// Full-width map+decode leaf. Eight pipeline edges; 16 prepaid downstream slots.
// Counter is supplied by the PC ordinal owner; expected sector is computed here.
// Option-M table period96 is equivalent to golden m_p2l for every PC/index.
// KV_MAP0 is retained as an elaboration option for independent comparison only.
module ot_qwen_kvc_decode_map_pc #(parameter integer ENABLE=0,KV_MAP=1)(
 input wire clk,rst_n,
 input wire i_v,input wire [255:0] i_data,
 input wire [16:0] i_sec,input wire [6:0] i_port,
 input wire [12:0] i_pos,input wire [7:0] i_row,i_layer,
 input wire [10:0] i_count,i_limit,input wire i_active,i_done,
 input wire o_cr,
 output wire i_cr,o_v,output wire [255:0] o_data,
 output wire [10:0] o_tile0,o_tile1,output wire [6:0] o_loc0,o_loc1,
 output wire [1:0] o_sel0,o_sel1,o_n,
 output wire o_isk,o_tail,o_bad,o_drop,output wire [3:0] o_tail_lanes,
 output wire fault
);
 (* keep *) reg [325:0] body0;
 reg [325:0] body1,body2,body3;
 (* keep *) reg [6:0] port0;
 (* keep *) reg [9:0] index0;
 reg [6:0] port1,port2;
 reg [9:0] index1,index2;
 reg [3:0] quotient1;
 reg [6:0] rem1;
 reg [8:0] entry2,base2;
 reg [16:0] expected3;
 reg v0,v1,v2,v3;
 wire [8:0] lookup;
 ot_qwen_kvc_map_lut lut(.key({port1[6:5],rem1}),.value(lookup));
 wire [8:0] g2=base2+entry2[5:0];
 always @(posedge clk) begin
  body0<={i_data,i_sec,i_pos,i_row,i_layer,i_count,i_limit,i_active,i_done};
  port0<=i_port;index0<=i_count[9:0];
  body1<=body0;body2<=body1;body3<=body2;
  port1<=port0;port2<=port1;index1<=index0;index2<=index1;
  quotient1<=index0/96;rem1<=index0%96;
  entry2<=lookup;base2<=quotient1*48;
  expected3<=(KV_MAP!=0) ? {entry2[8],port2[4],g2,port2[3:0],entry2[7:6]} :
    {index2[0],port2[4],index2[9:1],port2[3:0],port2[6:5]};
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin v0<=0;v1<=0;v2<=0;v3<=0;end
  else begin v0<=i_v;v1<=v0;v2<=v1;v3<=v2;end
 end
 wire [255:0] data3;wire [16:0] sec3;wire [12:0] pos3;
 wire [7:0] row3,layer3;wire [10:0] count3,limit3;wire active3,done3;
 assign {data3,sec3,pos3,row3,layer3,count3,limit3,active3,done3}=body3;
 ot_qwen_kvc_decode_pc #(.ENABLE(ENABLE),.CREDITS(16)) decode(
  .clk(clk),.rst_n(rst_n),.i_v(v3),.i_data(data3),.i_sec(sec3),.i_expected(expected3),
  .i_pos(pos3),.i_row(row3),.i_layer(layer3),.i_count(count3),.i_limit(limit3),
  .i_active(active3),.i_done(done3),.o_cr(o_cr),.i_cr(i_cr),.o_v(o_v),.o_data(o_data),
  .o_tile0(o_tile0),.o_tile1(o_tile1),.o_loc0(o_loc0),.o_loc1(o_loc1),
  .o_sel0(o_sel0),.o_sel1(o_sel1),.o_n(o_n),.o_isk(o_isk),.o_tail(o_tail),
  .o_bad(o_bad),.o_drop(o_drop),.o_tail_lanes(o_tail_lanes),.fault(fault));
endmodule
