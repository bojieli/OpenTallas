`timescale 1ps/1fs
`default_nettype none
// Source ready/valid -> actual selector four-credit pulse ABI. Credits are cold
// reset state, never regenerated on frame-start. Owner remains at the stage join.
module ot_hbm_native_index_query_credit #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,retained,
 input wire [72:0] owner_frame,block_frame,
 input wire [6:0] owner_rank,block_rank,
 input wire block_v,output wire block_r,
 input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire qbr,output reg [1047:0] qb,
 output wire drained,output wire fault
);
 reg [2:0] credits,credits_n;
 reg [7:0] order,order_n;
 reg seen_retained,sticky_fault;
 wire coded_ok=(credits_n==~credits)&&(order_n==~order);
 wire allowed=ENABLE&&owner_valid&&!owner_fault&&retained&&!sticky_fault&&coded_ok;
 wire identity_ok=block_frame==owner_frame&&block_rank==owner_rank;
 wire order_ok=order<128&&{block_head,block_number}==order[6:0];
 assign block_r=allowed&&seen_retained&&identity_ok&&order_ok&&(credits!=0);
 wire take=block_v&&block_r;
 assign drained=ENABLE&&coded_ok&&credits==4&&!qb[0];
 assign fault=ENABLE&&(sticky_fault||!coded_ok||owner_fault);
 reg [2:0] next_credit;
 always @* next_credit=credits+{2'b0,qbr}-{2'b0,take};
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin credits<=4;credits_n<=~3'd4;order<=0;order_n<=8'hff;
   seen_retained<=0;sticky_fault<=0;qb<=0;end
  else if(ENABLE)begin
   qb[0]<=take;
   if(take)qb[1047:1]<={head_weight,block_data,block_number,block_head};
   seen_retained<=retained;
   if(!coded_ok||owner_fault||(qbr&&credits==4&&!take)||next_credit>4||
      (block_v&&retained&&(!identity_ok||!order_ok))||
      (!retained&&seen_retained&&(credits!=4||qb[0])))sticky_fault<=1;
   if(coded_ok&&!sticky_fault)begin
    credits<=next_credit;credits_n<=~next_credit;
    if(retained&&!seen_retained)begin order<=0;order_n<=8'hff;end
    else if(take)begin order<=order+1'b1;order_n<=~(order+8'd1);end
   end
  end else qb<=0;
 end
endmodule
`default_nettype wire
