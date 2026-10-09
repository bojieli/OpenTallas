`timescale 1ns/1ps
// Enable only on an existing pass-through lane3..7 RESERVED for stage control.
// Ordinary core traffic on that lane is a schedule/configuration error, not a
// competing arbitrary552-bit subtype. Other lanes and the reliable endpoint
// are untouched; native link last flag remains protected by that endpoint.
module ot_s81_ctrl_lane_adapter #(parameter integer ENABLE=0,MUT=0)(
 input wire clk,rst_n,
 input wire core_lo_v,output wire core_lo_r,input wire[552:0] core_lo_d,
 output wire core_li_v,input wire core_li_r,output wire[552:0] core_li_d,
 output wire lane_lo_v,input wire lane_lo_r,output wire[552:0] lane_lo_d,
 input wire lane_li_v,output wire lane_li_r,input wire[552:0] lane_li_d,
 input wire c_tx_v,output wire c_tx_r,input wire[511:0] c_tx_d,input wire c_tx_l,
 output wire c_rx_v,input wire c_rx_r,output wire[511:0] c_rx_d,output wire c_rx_l,
 output reg fault
);
 generate if(ENABLE==0)begin:g_legacy
 assign lane_lo_v=core_lo_v;assign core_lo_r=lane_lo_r;assign lane_lo_d=core_lo_d;
 assign core_li_v=lane_li_v;assign lane_li_r=core_li_r;assign core_li_d=lane_li_d;
 assign c_tx_r=0;assign c_rx_v=0;assign c_rx_d=0;assign c_rx_l=0;
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;else if(c_tx_v)fault<=1;
 end else begin:g_control
 wire tv,tr,rv,rr;wire[512:0] td,rd;wire x0,x1,x2,x3;
 wire malformed=lane_li_v&&(lane_li_d[551:512]!=40'd0);
 wire[511:0] payload=(MUT==1)?(c_tx_d^512'd1):c_tx_d;
 wire last=(MUT==2)?1'b0:c_tx_l;
 ot_s81_ctrl_skid2 #(.W(513)) tx(.clk(clk),.rst_n(rst_n),.in_valid(c_tx_v),.in_ready(c_tx_r),.in_data({last,payload}),
 .out_valid(tv),.out_ready(tr),.out_data(td));
 assign lane_lo_v=tv;assign tr=lane_lo_r;assign lane_lo_d={td[512],40'd0,td[511:0]};
 ot_s81_ctrl_skid2 #(.W(513)) rx(.clk(clk),.rst_n(rst_n),.in_valid(lane_li_v&&!malformed),.in_ready(rr),.in_data({lane_li_d[552],lane_li_d[511:0]}),
 .out_valid(rv),.out_ready(c_rx_r),.out_data(rd));
 assign lane_li_r=malformed?1'b1:rr;
 assign c_rx_v=rv;assign c_rx_d=rd[511:0];assign c_rx_l=rd[512];
 assign core_lo_r=0;assign core_li_v=0;assign core_li_d=0;
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;
 else if(core_lo_v||malformed)fault<=1;
 end endgenerate
endmodule

// Two slots with producer-ready, head data and occupancy all registered.
// Unlike combinational full-replacement skids, no ready path crosses this tile.
module ot_s81_ctrl_skid2 #(parameter integer W=513)(
 input wire clk,rst_n,input wire in_valid,output reg in_ready,input wire[W-1:0] in_data,
 output wire out_valid,input wire out_ready,output reg[W-1:0] out_data
);
 reg[W-1:0] tail;reg[1:0] count;
 wire push=in_valid&&in_ready;wire pop=out_valid&&out_ready;
 wire[1:0] next_count=count+(push?2'd1:2'd0)-(pop?2'd1:2'd0);
 assign out_valid=count!=0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin in_ready<=0;count<=0;out_data<=0;tail<=0;end
  else begin
   count<=next_count;in_ready<=next_count<2;
   if(pop)begin
    if(count==2)begin out_data<=tail;if(push)tail<=in_data;end
    else if(push)out_data<=in_data;
   end else if(push)begin if(count==0)out_data<=in_data;else tail<=in_data;end
  end
 end
endmodule
