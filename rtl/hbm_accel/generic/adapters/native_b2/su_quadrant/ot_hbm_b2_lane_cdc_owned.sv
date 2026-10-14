`timescale 1ps/1fs
`default_nettype none
// Source-bank native lane: ten bank dequeue credits, independent response/commit obligations.
// Posted beats enter the reserved FIFO even before permit; no permit AND discards a valid.
// Only a held VM-domain owner grant dequeues each request direction.
// Ingress capacity must be reserved by the real producer before posting.
// Protected pointer rails come from the real HBM CDC primitive. No pulse crosses directly.
// Each payload FIFO is a distinct physical requirement; this RTL is not a closed SRAM view.
module ot_hbm_b2_lane_cdc_owned #(parameter integer LQ=10, MAX_PENDING=80, MUT=0, HARD_RESETS=0)(
 input wire cclk,vclk,rst_n,permit,vrpermit,vwpermit,
 input wire crst_n,vrst_n,
 input wire [16:0] crq,output reg crq_credit,output reg [256:0] crr,
 input wire [280:0] cwq,output reg cwq_credit,cwq_done,
 output reg [16:0] vrq,input wire vrq_credit,input wire [256:0] vrr,
 output reg [280:0] vwq,input wire vwq_credit,vwq_done,
 output wire fault,output wire cdrained,vdrained,rready,wready,cquiescent
);
 wire csrst_n=HARD_RESETS?crst_n:rst_n,vsrst_n=HARD_RESETS?vrst_n:rst_n;
 wire rf,wf,rdempty,wdempty,retempty,crempty,wcempt,wdempt;
 wire [15:0] rqdata;wire [279:0] wqdata;wire [255:0] rrdata;
 wire [11:0] faults; wire [2:0] unused_freed[0:5];wire unused1,unused2,unused3;
 reg [4:0] rcredit,wcredit,rcredit_n,wcredit_n;reg cf,vf;
 wire rpop=!rdempty&&rcredit!=0&&vrpermit&&vrpending<48,wpop=!wdempty&&wcredit!=0&&vwpermit&&vwpending<48;
 ot_hbm_accel_cdc_fifo_p2 #(.W(16),.AW(4)) rqfifo(.wclk(cclk),.wrst_n(csrst_n),.we(crq[16]),.wdata(crq[15:0]),.full(rf),.rd_freed(unused_freed[0]),.w_fault(faults[0]),.rclk(vclk),.rrst_n(vsrst_n),.re(rpop),.rdata(rqdata),.empty(rdempty),.r_fault(faults[1]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(280),.AW(4)) wqfifo(.wclk(cclk),.wrst_n(csrst_n),.we(cwq[280]),.wdata(cwq[279:0]),.full(wf),.rd_freed(unused_freed[1]),.w_fault(faults[2]),.rclk(vclk),.rrst_n(vsrst_n),.re(wpop),.rdata(wqdata),.empty(wdempty),.r_fault(faults[3]));
 wire rrfull,rcfull,wcfull,wdfull;wire rdummy,cdummy,wdummy;
 ot_hbm_accel_cdc_fifo_p2 #(.W(256),.AW(4)) rrfifo(.wclk(vclk),.wrst_n(vsrst_n),.we(vrr[256]),.wdata(MUT==1?vrr[255:0]^256'd1:vrr[255:0]),.full(rrfull),.rd_freed(unused_freed[2]),.w_fault(faults[4]),.rclk(cclk),.rrst_n(csrst_n),.re(!retempty),.rdata(rrdata),.empty(retempty),.r_fault(faults[5]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) rcfifo(.wclk(vclk),.wrst_n(vsrst_n),.we(vrq_credit),.wdata(1'b1),.full(rcfull),.rd_freed(unused_freed[3]),.w_fault(faults[6]),.rclk(cclk),.rrst_n(csrst_n),.re(!crempty),.rdata(rdummy),.empty(crempty),.r_fault(faults[7]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) wcfifo(.wclk(vclk),.wrst_n(vsrst_n),.we(vwq_credit),.wdata(1'b1),.full(wcfull),.rd_freed(unused_freed[4]),.w_fault(faults[8]),.rclk(cclk),.rrst_n(csrst_n),.re(!wcempt),.rdata(cdummy),.empty(wcempt),.r_fault(faults[9]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) wdfifo(.wclk(vclk),.wrst_n(vsrst_n),.we(vwq_done),.wdata(1'b1),.full(wdfull),.rd_freed(unused_freed[5]),.w_fault(faults[10]),.rclk(cclk),.rrst_n(csrst_n),.re(!wdempt),.rdata(wdummy),.empty(wdempt),.r_fault(faults[11]));
 always @(posedge cclk or negedge csrst_n)if(!csrst_n)begin crq_credit<=0;cwq_credit<=0;cwq_done<=0;crr<=0;cf<=0;end else begin
  crq_credit<=!crempty;cwq_credit<=!wcempt;cwq_done<=!wdempt;crr<={!retempty,rrdata};
  if((crq[16]&&rf)||(cwq[280]&&wf))cf<=1;
 end
 always @(posedge vclk or negedge vsrst_n)if(!vsrst_n)begin rcredit<=LQ;rcredit_n<=~(5'(LQ));wcredit<=LQ;wcredit_n<=~(5'(LQ));vrq<=0;vwq<=0;vf<=0;end else begin
  vrq<={rpop,rqdata};vwq<={wpop,wqdata};rcredit<=rcredit-rpop+vrq_credit;wcredit<=wcredit-wpop+vwq_credit;rcredit_n<=~(rcredit-rpop+vrq_credit);wcredit_n<=~(wcredit-wpop+vwq_credit);
  if(rcredit!=~rcredit_n||wcredit!=~wcredit_n||(vrr[256]&&rrfull)||(vrq_credit&&rcfull)||(vwq_credit&&wcfull)||(vwq_done&&wdfull)||rcredit-rpop+vrq_credit>LQ||wcredit-wpop+vwq_credit>LQ)vf<=1;
 end
 // Source obligations count accepted beats until each real returned event is consumed.
 // Credit return and commit/response are independent obligations.
 // Owned-parent bound80 reserves48 admitted VM obligations +16 sourceFIFO
 // +10 unused servercredits +6 registered handoff slots. Dequeue pauses
 // at48 VM obligations, allowing mirror ACK batches to quiesce without overflow.
 // Ten bank credits return on dequeue, before response/commit; they are not this bound.
 localparam integer CB=$clog2(MAX_PENDING+1);
 reg [CB-1:0] rresp,rcred,wcred,wcommit,rresp_n,rcred_n,wcred_n,wcommit_n;
 reg df;reg [6:0] vrpending,vwpending,vrpending_n,vwpending_n;
 wire [7:0] nvrpending={1'b0,vrpending}+vrq[16]-vrr[256];
 wire [7:0] nvwpending={1'b0,vwpending}+vwq[280]-vwq_done;
 reg pf;
 always @(posedge vclk or negedge vsrst_n)if(!vsrst_n)begin
  vrpending<=0;vwpending<=0;vrpending_n<=7'h7f;vwpending_n<=7'h7f;pf<=0;
 end else begin
  if(vrpending!=~vrpending_n||vwpending!=~vwpending_n||nvrpending>64||nvwpending>64)pf<=1;
  vrpending<=nvrpending[6:0];vrpending_n<=~nvrpending[6:0];vwpending<=nvwpending[6:0];vwpending_n<=~nvwpending[6:0];
 end
 wire racc=crq[16],wacc=cwq[280];
 wire [CB:0] nrresp={1'b0,rresp}+racc-crr[256];
 wire [CB:0] nrcred={1'b0,rcred}+racc-crq_credit;
 wire [CB:0] nwcred={1'b0,wcred}+wacc-cwq_credit;
 wire [CB:0] nwcommit={1'b0,wcommit}+wacc-cwq_done;
 always @(posedge cclk or negedge csrst_n)if(!csrst_n)begin
  rresp<=0;rcred<=0;wcred<=0;wcommit<=0;
  rresp_n<='1;rcred_n<='1;wcred_n<='1;wcommit_n<='1;df<=0;
 end else begin
  if(rresp!=~rresp_n||rcred!=~rcred_n||wcred!=~wcred_n||wcommit!=~wcommit_n||
    nrresp>MAX_PENDING||nrcred>MAX_PENDING||nwcred>MAX_PENDING||nwcommit>MAX_PENDING)df<=1;
  rresp<=nrresp[CB-1:0];rresp_n<=~nrresp[CB-1:0];
  rcred<=nrcred[CB-1:0];rcred_n<=~nrcred[CB-1:0];
  wcred<=nwcred[CB-1:0];wcred_n<=~nwcred[CB-1:0];
  wcommit<=nwcommit[CB-1:0];wcommit_n<=~nwcommit[CB-1:0];
 end
 assign cquiescent=!df&&!cf&&!(|faults)&&rresp==~rresp_n&&rcred==~rcred_n&&wcred==~wcred_n&&wcommit==~wcommit_n&&rresp==0&&rcred==0&&wcred==0&&wcommit==0&&
  !crr[256]&&!crq_credit&&!cwq_credit&&!cwq_done;
 assign cdrained=(MUT==2)?1'b1:cquiescent&&!crq[16]&&!cwq[280];
 // This VM-local predicate must be combined with the synchronized source predicate
 // by the held-owner lease. It cannot by itself prove returned queues consumed.
 assign vdrained=rready&&wready&&!pf&&!vf&&!(|faults)&&rcredit==~rcredit_n&&wcredit==~wcredit_n&&rdempty&&wdempty&&rcredit==LQ&&wcredit==LQ&&
  !vrq[16]&&!vwq[280]&&!vrr[256]&&!vrq_credit&&!vwq_credit&&!vwq_done;
 assign rready=!pf&&!vf&&vrpending==0&&vrpending==~vrpending_n&&rcredit==LQ&&rcredit==~rcredit_n&&!vrq[16]&&!vrr[256]&&!vrq_credit;
 assign wready=!pf&&!vf&&vwpending==0&&vwpending==~vwpending_n&&wcredit==LQ&&wcredit==~wcredit_n&&!vwq[280]&&!vwq_done&&!vwq_credit;
 assign fault=pf|df|cf|vf|(|faults);
endmodule
`default_nettype wire
