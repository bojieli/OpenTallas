`timescale 1ps/1fs
`default_nettype none
// Registered group1 owner station for one actual eight-bank quadrant.
// Source classes are assigned by the real parent (SU/quant/DMA), not credits.
// One held R owner and one held W owner share the actual ten bank credits.
// Every source has a reserved ingress FIFO; only VM permits dequeue that FIFO.
module ot_hbm_b2_peer_mux_q #(parameter integer NSRC=3,MUT=0,HARD_CLOCKS=0)(
 input wire clk,rst_n,input wire [7:0] bank_clk,input wire [NSRC-1:0] src_clk,
 input wire [NSRC-1:0] rreq,wreq,src_drained,
 input wire [NSRC*8-1:0] lane_rready,lane_wready,lane_vdrained,
 input wire [NSRC*8*17-1:0] src_rq,
 output wire [NSRC*8-1:0] src_rcredit,
 output wire [NSRC*8*257-1:0] src_rr,
 input wire [NSRC*8*281-1:0] src_wq,
 output wire [NSRC*8-1:0] src_wcredit,src_done,
 output wire [NSRC-1:0] rgrant,wgrant,rack,wack,vm_rgrant,vm_wgrant,
 output wire [8*17-1:0] rq,input wire [7:0] rcredit,input wire [8*257-1:0] rr,
 output wire [8*281-1:0] wq,input wire [7:0] wcredit,done,
 output wire fault
);
 wire [7:0] routed_rvalid,routed_wvalid;
 for(genvar b=0;b<8;b=b+1)begin:routed
  assign routed_rvalid[b]=rq[b*17+16];assign routed_wvalid[b]=wq[b*281+280];
 end
 wire [NSRC-1:0] ra,wa,vd;wire rf,wf;wire [7:0] sf;
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
 for(genvar b=0;b<8;b=b+1)begin:station_bank
  wire [NSRC*17-1:0] lrq;wire [NSRC*281-1:0] lwq;wire [NSRC*257-1:0] lrr;
  wire [NSRC-1:0] lrc,lwc,ld;
  for(genvar z=0;z<NSRC;z=z+1)begin:source
   assign lrq[z*17+:17]=src_rq[(z*8+b)*17+:17];assign lwq[z*281+:281]=src_wq[(z*8+b)*281+:281];
   assign src_rr[(z*8+b)*257+:257]=lrr[z*257+:257];assign src_rcredit[z*8+b]=lrc[z];assign src_wcredit[z*8+b]=lwc[z];assign src_done[z*8+b]=ld[z];
  end
  ot_hbm_b2_peer_mux_lane #(.NSRC(NSRC),.MUT(MUT)) u_station(.clk(HARD_CLOCKS?bank_clk[b]:clk),.rst_n(rst_n),.rgrant(vm_rgrant),.wgrant(vm_wgrant),
   .src_rq(lrq),.src_rcredit(lrc),.src_rr(lrr),.src_wq(lwq),.src_wcredit(lwc),.src_done(ld),
   .rq(rq[b*17+:17]),.rcredit(rcredit[b]),.rr(rr[b*257+:257]),.wq(wq[b*281+:281]),.wcredit(wcredit[b]),.done(done[b]),.fault(sf[b]));
 end
 assign fault=rf|wf|(|sf);
endmodule
`default_nettype wire
