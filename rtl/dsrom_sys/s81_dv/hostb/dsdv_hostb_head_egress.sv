`timescale 1ns/1ps
`default_nettype none
// New type10 events use two booked transport edges. Actual legacy lane payload
// and valid bypass without added registers. Default-off is direct identity.
module dsdv_hostb_head_egress #(parameter integer ENABLE=0)(
 input wire ck,rst_n,input wire[1:0] legacy_v,input wire[1105:0] legacy_d,
 input wire event_v,input wire[552:0] event_d,input wire event_slot,
 output wire[1:0] host_v,output wire[1105:0] host_d,output wire[2:0] fault);
 generate if(ENABLE==0)begin:g_original
  assign host_v=legacy_v;assign host_d=legacy_d;assign fault=0;
 end else begin:g_hbe
  wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
  reg[2:0] f;assign fault=f;
  wire take=event_v&&event_slot&&f==0;
  reg[552:0] d0,d1;reg[1:0] v;
  wire collision=v[1]&&legacy_v[0];wire[2:0] roots;
  always @(posedge ck)begin d0<=event_d;d1<=d0;end
  always @(posedge ck or negedge rn)begin
   if(!rn)begin v<=0;f<=0;end
   else begin
    v<={v[0],take};
    if(event_slot&&!event_v)f[0]<=1;
    if(event_v&&!event_slot)f[1]<=1;
    if(collision)f[2]<=1;
   end
  end
  genvar k;
  for(k=0;k<3;k=k+1)begin:g_root
   (* keep_hierarchy="yes" *) dsdv_hostb_event_root #(.ID(k)) u_root(.ck(ck),.rn(rn),.d(take),.q(roots[k]));
  end
  for(k=0;k<37;k=k+1)begin:g_bank
   localparam integer LO=15*k,W=(553-LO<15)?553-LO:15;
   wire sel;
   (* keep_hierarchy="yes" *) dsdv_hostb_event_select #(.ID(k)) u_bank(.ck(ck),.d(roots[k/13]),.q(sel));
   assign host_d[LO+:W]=({W{~sel}}&legacy_d[LO+:W])|({W{sel}}&d1[LO+:W]);
  end
  assign host_d[1105:553]=legacy_d[1105:553];
  assign host_v={legacy_v[1],(legacy_v[0]||v[1])&&!collision};
 end endgenerate
endmodule
module dsdv_hostb_event_root #(parameter integer ID=0)(input wire ck,rn,d,output reg q);
 always @(posedge ck or negedge rn)if(!rn)q<=0;else q<=d;
endmodule
module dsdv_hostb_event_select #(parameter integer ID=0)(input wire ck,d,output reg q);
 always @(posedge ck)q<=d;
endmodule
`default_nettype wire
