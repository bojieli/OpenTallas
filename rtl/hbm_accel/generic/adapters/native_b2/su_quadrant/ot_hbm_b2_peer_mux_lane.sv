`timescale 1ps/1fs
`default_nettype none
// One real bank's registered owner station. Payload has no reset; only valid,
// credit and commit controls reset. Each hardened station has its own clock root.
module ot_hbm_b2_peer_mux_lane #(parameter integer NSRC=3,MUT=0)(
 input wire clk,rst_n,input wire [NSRC-1:0] rgrant,wgrant,
 input wire [NSRC*17-1:0] src_rq,output reg [NSRC-1:0] src_rcredit,
 output reg [NSRC*257-1:0] src_rr,
 input wire [NSRC*281-1:0] src_wq,output reg [NSRC-1:0] src_wcredit,src_done,
 output reg [16:0] rq,input wire rcredit,input wire [256:0] rr,
 output reg [280:0] wq,input wire wcredit,done,output reg fault
);
 wire [NSRC-1:0] selected_r=(MUT==1)?{rgrant[NSRC-2:0],rgrant[NSRC-1]}:rgrant;
 wire [NSRC-1:0] selected_w=(MUT==1)?{wgrant[NSRC-2:0],wgrant[NSRC-1]}:wgrant;
 reg [15:0] rd;reg [279:0] wd;reg rv,wv;
 // Return diagnostics retain the owner sampled at the return edge. They do
 // not sit on the data/credit handoff path.
 reg dc_rc,dc_rv,dc_wc,dc_done,dc_ro,dc_wo;
 always @*begin
  rd=0;wd=0;rv=0;wv=0;
  for(integer s=0;s<NSRC;s=s+1)begin
   rd=rd|(src_rq[s*17+:16]&{16{selected_r[s]}});rv=rv|(src_rq[s*17+16]&&selected_r[s]);
   wd=wd|(src_wq[s*281+:280]&{280{selected_w[s]}});wv=wv|(src_wq[s*281+280]&&selected_w[s]);
  end
 end
 always @(posedge clk)begin
  rq[15:0]<=rd;wq[279:0]<=wd;
  // Invalid payload is unobservable; unconditional capture removes the
  // 256-bit return-payload enable fanout from each owner grant.
  for(integer s=0;s<NSRC;s=s+1)src_rr[s*257+:256]<=rr[255:0];
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  rq[16]<=0;wq[280]<=0;src_rcredit<=0;src_wcredit<=0;src_done<=0;fault<=0;
  dc_rc<=0;dc_rv<=0;dc_wc<=0;dc_done<=0;dc_ro<=0;dc_wo<=0;
  for(integer s=0;s<NSRC;s=s+1)src_rr[s*257+256]<=0;
 end else begin
  rq[16]<=rv;wq[280]<=wv;
  dc_rc<=rcredit;dc_rv<=rr[256];dc_wc<=wcredit;dc_done<=done;
  dc_ro<=|rgrant;dc_wo<=|wgrant;
  for(integer s=0;s<NSRC;s=s+1)begin
   src_rcredit[s]<=rgrant[s]&&rcredit;src_rr[s*257+256]<=rgrant[s]&&rr[256];
   src_wcredit[s]<=wgrant[s]&&wcredit;src_done[s]<=wgrant[s]&&done;
   if(src_rq[s*17+16]&&!rgrant[s]||src_wq[s*281+280]&&!wgrant[s])fault<=1;
  end
  if((dc_rc||dc_rv)&&!dc_ro||(dc_wc||dc_done)&&!dc_wo)fault<=1;
 end
endmodule
`default_nettype wire
