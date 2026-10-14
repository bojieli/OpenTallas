`timescale 1ns/1ps
// Raw hc182 event station: start38, PW113 and DW181 are the original pulses.
// Sources reserve one of four command credits per nonempty hc edge, including
// simultaneous PW/DW/start as one indivisible raw command. cmd_cr returns a
// credit only after CTRL emits all seven remote copies. Capacity is not commit.
// Captured hc and returned credit precede decode/counters; cmd_v/hc/fault and
// source_cr/available leave registered pins. No same-cycle cross-block ready.
module qkd_host_hc_station #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[2:0]die_id,input wire[181:0]raw_hc,input wire cmd_cr,
 output reg cmd_v,output reg[181:0]cmd_hc,output reg source_cr,
 output reg available,output reg fault
);
 reg[181:0]hq;reg cq;reg[2:0]role;reg role_valid;reg[2:0]credits;
 wire event_v=role_valid&&role==0&&(hq[38]||hq[113]||hq[181]);
 always @(posedge ck)begin hq<=raw_hc;cmd_hc<=hq^((MUT==1&&event_v)?182'd1:182'd0);end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin cq<=0;role<=0;role_valid<=0;credits<=4;cmd_v<=0;source_cr<=0;available<=0;fault<=0;end
  else begin
   role<=die_id;role_valid<=1;if(role_valid&&die_id!=role)fault<=1;
   cq<=cmd_cr;source_cr<=cq&&!fault&&role==0;cmd_v<=event_v&&credits!=0&&!fault;
   available<=role==0&&!fault&&(credits+4'(cq)-4'(event_v)>0);
   if((event_v&&credits==0)||(cq&&credits==4&&!event_v))fault<=1;
   else credits<=credits+3'(cq)-3'(event_v);
  end
 end
endmodule
