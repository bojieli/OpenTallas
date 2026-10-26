`timescale 1ns/1ps
`default_nettype none
// Real compiler-reserved eight-row VM reader. This is the HC H_EXPORT/H_STORE
// consumer, not a bench preload. Eight distinct banks/ports per beat, 80 beats.
// Fixed RL includes the actual native VM return pipeline and physical hops.
// Late/missing returns fault; stage data and command stay on compiled cycles.
// XLAT: extra fixed stage edges between the VM return and the leaves (HLAYOUT=1 transpose: 4); the leaf command
// follows the last staged word by the same 3 settle edges.
module ot_s81_hcx_prefetch #(parameter integer RL=4,XLAT=0)(
 input wire clk,rst_n,start,
 input wire [13:0] h_base_row,
 output wire [7:0] rq_v,
 output wire [111:0] rq_row,
 input wire [7:0] rs_v,
 output wire stage_begin,
 output wire stage_v,
 output wire [6:0] stage_word,
 output reg cmd_v,
 output reg fault
);
 reg active;reg[6:0]word;reg[13:0]base;
 reg[RL-1:0]dv;reg[6:0]dw[0:RL-1];
 reg[3:0]settle;
 assign rq_v={8{active}};
 generate for(genvar p=0;p<8;p=p+1)begin:g_row
  assign rq_row[14*p+:14]=base+14'(8*word+p);
 end endgenerate
 assign stage_begin=start;
 assign stage_v=dv[RL-1];
 assign stage_word=dw[RL-1];
 initial if(RL<1)$error("HCX prefetch requires actual native VM read latency");
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;word<=0;dv<=0;settle<=0;cmd_v<=0;fault<=0;end
  else begin
   cmd_v<=0;
   if(start)begin
    if(active|| |dv || settle!=0 || h_base_row[2:0]!=0 || h_base_row>14'd15744)fault<=1;
    active<=1;word<=0;base<=h_base_row;
   end else if(active)begin word<=word+1'b1;if(word==79)active<=0;end
   dv[0]<=active;dw[0]<=word;
   for(integer i=1;i<RL;i=i+1)begin dv[i]<=dv[i-1];dw[i]<=dw[i-1];end
   if(rs_v!={8{dv[RL-1]}})fault<=1;
   if(dv[RL-1] && dw[RL-1]==79)settle<=4'(3+XLAT);
   else if(settle!=0)begin settle<=settle-1'b1;if(settle==1)cmd_v<=1;end
  end
 end
endmodule
`default_nettype wire
