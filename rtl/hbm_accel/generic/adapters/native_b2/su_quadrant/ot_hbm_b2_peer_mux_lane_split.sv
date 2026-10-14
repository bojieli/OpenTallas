`timescale 1ps/1fs
`default_nettype none
// Distinct hard leaves for the independent R and W held leases.  Each capture
// and diagnostic has the same edge as the original combined station.
module ot_hbm_b2_peer_mux_read #(parameter integer NSRC=3,MUT=0)(
 input wire clk,rst_n,input wire[NSRC-1:0] grant,
 input wire[NSRC*17-1:0] src_rq,output reg[NSRC-1:0] src_credit,
 output reg[NSRC*257-1:0] src_rr,output reg[16:0] rq,
 input wire credit,input wire[256:0] rr,output reg fault);
 wire[NSRC-1:0] sel=(MUT==1)?{grant[NSRC-2:0],grant[NSRC-1]}:grant;
 reg[15:0] data;reg valid;reg dc_cr,dc_rv,dc_owner;
 always @*begin
  data=0;valid=0;
  for(integer s=0;s<NSRC;s=s+1)begin
   data=data|(src_rq[s*17+:16]&{16{sel[s]}});
   valid=valid|(src_rq[s*17+16]&&sel[s]);
  end
 end
 always @(posedge clk)begin
  rq[15:0]<=data;
  for(integer s=0;s<NSRC;s=s+1)src_rr[s*257+:256]<=rr[255:0];
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  rq[16]<=0;src_credit<=0;fault<=0;dc_cr<=0;dc_rv<=0;dc_owner<=0;
  for(integer s=0;s<NSRC;s=s+1)src_rr[s*257+256]<=0;
 end else begin
  rq[16]<=valid;dc_cr<=credit;dc_rv<=rr[256];dc_owner<=|grant;
  for(integer s=0;s<NSRC;s=s+1)begin
   src_credit[s]<=grant[s]&&credit;src_rr[s*257+256]<=grant[s]&&rr[256];
   if(src_rq[s*17+16]&&!grant[s])fault<=1;
  end
  if((dc_cr||dc_rv)&&!dc_owner)fault<=1;
 end
endmodule
module ot_hbm_b2_peer_mux_write #(parameter integer NSRC=3,MUT=0)(
 input wire clk,rst_n,input wire[NSRC-1:0] grant,
 input wire[NSRC*281-1:0] src_wq,output reg[NSRC-1:0] src_credit,src_done,
 output reg[280:0] wq,input wire credit,done,output reg fault);
 wire[NSRC-1:0] sel=(MUT==1)?{grant[NSRC-2:0],grant[NSRC-1]}:grant;
 (* keep=1 *)reg[NSRC-1:0] sel_p,sel_n;
 reg[279:0] data;reg valid;reg dc_cr,dc_done,dc_owner;
 always @*begin
  data=0;valid=0;
  for(integer s=0;s<NSRC;s=s+1)begin
   data[127:0]=data[127:0]|(src_wq[s*281+:128]&{128{sel_p[s]}});
   data[279:128]=data[279:128]|(src_wq[s*281+128+:152]&{152{!sel_n[s]}});
   valid=valid|(src_wq[s*281+280]&&sel_p[s]);
  end
 end
 always @(posedge clk)wq[279:0]<=data;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  wq[280]<=0;src_credit<=0;src_done<=0;fault<=0;
  dc_cr<=0;dc_done<=0;dc_owner<=0;sel_p<=0;sel_n<='1;
 end else begin
  wq[280]<=valid;dc_cr<=credit;dc_done<=done;dc_owner<=|grant;
  sel_p<=sel;sel_n<=~sel;
  for(integer s=0;s<NSRC;s=s+1)begin
   src_credit[s]<=grant[s]&&credit;src_done[s]<=grant[s]&&done;
   if(src_wq[s*281+280]&&!grant[s])fault<=1;
  end
  if((dc_cr||dc_done)&&!dc_owner)fault<=1;
 end
endmodule
module ot_hbm_b2_peer_mux_lane_split #(parameter integer NSRC=3,MUT=0)(
 input wire rclk,wclk,rrst_n,wrst_n,input wire[NSRC-1:0] rgrant,wgrant,
 input wire[NSRC*17-1:0] src_rq,output wire[NSRC-1:0] src_rcredit,
 output wire[NSRC*257-1:0] src_rr,input wire[NSRC*281-1:0] src_wq,
 output wire[NSRC-1:0] src_wcredit,src_done,
 output wire[16:0] rq,input wire rcredit,input wire[256:0] rr,
 output wire[280:0] wq,input wire wcredit,done,output wire fault);
 wire rf,wf;
 ot_hbm_b2_peer_mux_read #(.NSRC(NSRC),.MUT(MUT)) u_read(
  .clk(rclk),.rst_n(rrst_n),.grant(rgrant),.src_rq(src_rq),.src_credit(src_rcredit),
  .src_rr(src_rr),.rq(rq),.credit(rcredit),.rr(rr),.fault(rf));
 ot_hbm_b2_peer_mux_write #(.NSRC(NSRC),.MUT(MUT)) u_write(
  .clk(wclk),.rst_n(wrst_n),.grant(wgrant),.src_wq(src_wq),.src_credit(src_wcredit),
  .src_done(src_done),.wq(wq),.credit(wcredit),.done(done),.fault(wf));
 assign fault=rf|wf;
endmodule
`default_nettype wire
