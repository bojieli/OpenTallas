`timescale 1ns/1ps
// Raw hc182 event station: start38, PW113 and DW181 are the original pulses.
// Sources reserve one of four command credits per nonempty hc edge, including
// simultaneous PW/DW/start as one indivisible raw command. cmd_cr returns a
// credit only after CTRL emits all seven remote copies. Capacity is not commit.
// Captured hc and returned credit precede decode/counters; cmd_v/hc/fault and
// source_cr/available leave registered pins. No same-cycle cross-block ready.
// HCW (KV-P2-RTL 10-23): width of the hc slice the station carries. 182 (default) = the
// original full raw hc (START38 + PW113 + DW181 events), unchanged. 39 = START only
// (hc[38:0] = start,gen,token,pos): the admission compositions replay pr143 (PW/DW,
// hc[181:39]) locally on fixed cycles and bypass the station, so the START-only
// station has no PW/DW port bits at all instead of a 143-bit constant-zero tie.
module qkd_host_hc_station #(parameter integer MUT=0,parameter integer HCW=182)(
 input wire ck,rst_n,input wire[2:0]die_id,input wire[HCW-1:0]raw_hc,input wire cmd_cr,
 output reg cmd_v,output reg[HCW-1:0]cmd_hc,output reg source_cr,
 output reg available,output reg fault
);
 initial if(HCW!=182&&HCW!=39)$fatal(1,"qkd_host_hc_station: HCW must be 182 (full hc) or 39 (START only)");
 reg[HCW-1:0]hq;reg cq;reg[2:0]role;reg role_valid;reg[2:0]credits;
 wire ev_raw;
 generate if(HCW==182)begin:g_full assign ev_raw=hq[38]||hq[113]||hq[181];end
 else begin:g_start assign ev_raw=hq[38];end endgenerate
 wire event_v=role_valid&&role==0&&ev_raw;
 always @(posedge ck)begin hq<=raw_hc;cmd_hc<=hq^((MUT==1&&event_v)?HCW'(1):HCW'(0));end
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
