`timescale 1ps/1fs
`default_nettype none
// Registered group1 owner station for one actual eight-bank quadrant.
// Source classes are assigned by the real parent (SU/quant/DMA), not credits.
// One held R owner and one held W owner share the actual ten bank credits.
// Every source has a reserved ingress FIFO; only VM permits dequeue that FIFO.
module ot_hbm_b2_peer_mux_q #(parameter integer NSRC=3,MUT=0)(
 input wire clk,rst_n,input wire [NSRC-1:0] src_clk,
 input wire [NSRC-1:0] rreq,wreq,src_drained,
 input wire [NSRC*8-1:0] lane_rready,lane_wready,lane_vdrained,
 input wire [NSRC*8*17-1:0] src_rq,
 output reg [NSRC*8-1:0] src_rcredit,
 output reg [NSRC*8*257-1:0] src_rr,
 input wire [NSRC*8*281-1:0] src_wq,
 output reg [NSRC*8-1:0] src_wcredit,src_done,
 output wire [NSRC-1:0] rgrant,wgrant,rack,wack,vm_rgrant,vm_wgrant,
 output reg [8*17-1:0] rq,input wire [7:0] rcredit,input wire [8*257-1:0] rr,
 output reg [8*281-1:0] wq,input wire [7:0] wcredit,done,
 output wire fault
);
 wire [7:0] routed_rvalid,routed_wvalid;
 for(genvar b=0;b<8;b=b+1)begin:routed
  assign routed_rvalid[b]=rq[b*17+16];assign routed_wvalid[b]=wq[b*281+280];
 end
 wire [NSRC-1:0] ra,wa,vd;wire rf,wf;reg sf;
 wire [NSRC-1:0] selected_r=(MUT==1)?{vm_rgrant[NSRC-2:0],vm_rgrant[NSRC-1]}:vm_rgrant;
 wire [NSRC-1:0] selected_w=(MUT==1)?{vm_wgrant[NSRC-2:0],vm_wgrant[NSRC-1]}:vm_wgrant;
 for(genvar s=0;s<NSRC;s=s+1)begin:predicates
  wire rrbusy,wbusy;
  wire [7:0] rv,wv;
  for(genvar b=0;b<8;b=b+1)begin:beats
   assign rv[b]=src_rr[(s*8+b)*257+256];
   assign wv[b]=src_wq[(s*8+b)*281+280];
  end
  assign rrbusy=(|rv)||(|src_rcredit[s*8+:8]);
  assign wbusy=(|src_wcredit[s*8+:8])||(|src_done[s*8+:8]);
  assign ra[s]=(&lane_rready[s*8+:8])&&!rrbusy&&!(|routed_rvalid);
  assign wa[s]=(&lane_wready[s*8+:8])&&!wbusy&&!(|routed_wvalid);
  assign vd[s]=(&lane_vdrained[s*8+:8])&&!rrbusy&&!wbusy&&!(vm_rgrant[s]&&(|routed_rvalid))&&!(vm_wgrant[s]&&(|routed_wvalid));
 end
 ot_hbm_b2_peer_lease_owned #(.NSRC(NSRC)) rlease(.cclk(src_clk),.vclk(clk),.rst_n(rst_n),.src_req(rreq),.src_drained(src_drained),.vm_drained(vd),.vm_acquire_ready(ra),.src_grant(rgrant),.src_drain_ack(rack),.vm_grant(vm_rgrant),.fault(rf));
 ot_hbm_b2_peer_lease_owned #(.NSRC(NSRC)) wlease(.cclk(src_clk),.vclk(clk),.rst_n(rst_n),.src_req(wreq),.src_drained(src_drained),.vm_drained(vd),.vm_acquire_ready(wa),.src_grant(wgrant),.src_drain_ack(wack),.vm_grant(vm_wgrant),.fault(wf));
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  rq<=0;wq<=0;src_rcredit<=0;src_wcredit<=0;src_done<=0;src_rr<=0;sf<=0;
 end else begin
  rq<=0;wq<=0;src_rcredit<=0;src_wcredit<=0;src_done<=0;src_rr<=0;
  for(integer s=0;s<NSRC;s=s+1)begin
   for(integer b=0;b<8;b=b+1)begin
    if(selected_r[s])rq[b*17+:17]<=src_rq[(s*8+b)*17+:17];
    if(selected_w[s])wq[b*281+:281]<=src_wq[(s*8+b)*281+:281];
    if(vm_rgrant[s])begin src_rcredit[s*8+b]<=rcredit[b];src_rr[(s*8+b)*257+:257]<=rr[b*257+:257];end
    if(vm_wgrant[s])begin src_wcredit[s*8+b]<=wcredit[b];src_done[s*8+b]<=done[b];end
    if(src_rq[(s*8+b)*17+16]&&!vm_rgrant[s])sf<=1;
    if(src_wq[(s*8+b)*281+280]&&!vm_wgrant[s])sf<=1;
   end
  end
  if((|(rcredit))&&!(|vm_rgrant)||(|(wcredit|done))&&!(|vm_wgrant))sf<=1;
  for(integer b=0;b<8;b=b+1)if(rr[b*257+256]&&!(|vm_rgrant))sf<=1;
 end
 assign fault=rf|wf|sf;
endmodule
`default_nettype wire
