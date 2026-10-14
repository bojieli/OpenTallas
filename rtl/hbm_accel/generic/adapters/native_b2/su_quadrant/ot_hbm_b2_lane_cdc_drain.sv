`timescale 1ps/1fs
`default_nettype none
// One exclusive native bank/group lane. Client owns ten end-to-end credits.
// Protected pointer rails come from the real HBM CDC primitive. No pulse crosses directly.
// Each payload FIFO is a distinct physical requirement; this RTL is not a closed SRAM view.
module ot_hbm_b2_lane_cdc_drain #(parameter integer LQ=10, MUT=0)(
 input wire cclk,vclk,rst_n,permit,
 input wire [16:0] crq,output reg crq_credit,output reg [256:0] crr,
 input wire [280:0] cwq,output reg cwq_credit,cwq_done,
 output reg [16:0] vrq,input wire vrq_credit,input wire [256:0] vrr,
 output reg [280:0] vwq,input wire vwq_credit,vwq_done,
 output wire fault,output wire cdrained,vdrained
);
 wire rf,wf,rdempty,wdempty,retempty,crempty,wcempt,wdempt;
 wire [15:0] rqdata;wire [279:0] wqdata;wire [255:0] rrdata;
 wire [11:0] faults; wire [2:0] unused_freed[0:5];wire unused1,unused2,unused3;
 reg [4:0] rcredit,wcredit;reg cf,vf;
 wire rpop=!rdempty&&rcredit!=0,wpop=!wdempty&&wcredit!=0;
 ot_hbm_accel_cdc_fifo_p2 #(.W(16),.AW(4)) rqfifo(.wclk(cclk),.wrst_n(rst_n),.we(crq[16]&&permit),.wdata(crq[15:0]),.full(rf),.rd_freed(unused_freed[0]),.w_fault(faults[0]),.rclk(vclk),.rrst_n(rst_n),.re(rpop),.rdata(rqdata),.empty(rdempty),.r_fault(faults[1]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(280),.AW(4)) wqfifo(.wclk(cclk),.wrst_n(rst_n),.we(cwq[280]&&permit),.wdata(cwq[279:0]),.full(wf),.rd_freed(unused_freed[1]),.w_fault(faults[2]),.rclk(vclk),.rrst_n(rst_n),.re(wpop),.rdata(wqdata),.empty(wdempty),.r_fault(faults[3]));
 wire rrfull,rcfull,wcfull,wdfull;wire rdummy,cdummy,wdummy;
 ot_hbm_accel_cdc_fifo_p2 #(.W(256),.AW(4)) rrfifo(.wclk(vclk),.wrst_n(rst_n),.we(vrr[256]),.wdata(MUT==1?vrr[255:0]^256'd1:vrr[255:0]),.full(rrfull),.rd_freed(unused_freed[2]),.w_fault(faults[4]),.rclk(cclk),.rrst_n(rst_n),.re(!retempty),.rdata(rrdata),.empty(retempty),.r_fault(faults[5]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) rcfifo(.wclk(vclk),.wrst_n(rst_n),.we(vrq_credit),.wdata(1'b1),.full(rcfull),.rd_freed(unused_freed[3]),.w_fault(faults[6]),.rclk(cclk),.rrst_n(rst_n),.re(!crempty),.rdata(rdummy),.empty(crempty),.r_fault(faults[7]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) wcfifo(.wclk(vclk),.wrst_n(rst_n),.we(vwq_credit),.wdata(1'b1),.full(wcfull),.rd_freed(unused_freed[4]),.w_fault(faults[8]),.rclk(cclk),.rrst_n(rst_n),.re(!wcempt),.rdata(cdummy),.empty(wcempt),.r_fault(faults[9]));
 ot_hbm_accel_cdc_fifo_p2 #(.W(1),.AW(4)) wdfifo(.wclk(vclk),.wrst_n(rst_n),.we(vwq_done),.wdata(1'b1),.full(wdfull),.rd_freed(unused_freed[5]),.w_fault(faults[10]),.rclk(cclk),.rrst_n(rst_n),.re(!wdempt),.rdata(wdummy),.empty(wdempt),.r_fault(faults[11]));
 always @(posedge cclk or negedge rst_n)if(!rst_n)begin crq_credit<=0;cwq_credit<=0;cwq_done<=0;crr<=0;cf<=0;end else begin
  crq_credit<=!crempty;cwq_credit<=!wcempt;cwq_done<=!wdempt;crr<={!retempty,rrdata};
  if((crq[16]&&(!permit||rf))||(cwq[280]&&(!permit||wf)))cf<=1;
 end
 always @(posedge vclk or negedge rst_n)if(!rst_n)begin rcredit<=LQ;wcredit<=LQ;vrq<=0;vwq<=0;vf<=0;end else begin
  vrq<={rpop,rqdata};vwq<={wpop,wqdata};rcredit<=rcredit-rpop+vrq_credit;wcredit<=wcredit-wpop+vwq_credit;
  if((vrr[256]&&rrfull)||(vrq_credit&&rcfull)||(vwq_credit&&wcfull)||(vwq_done&&wdfull)||rcredit-rpop+vrq_credit>LQ||wcredit-wpop+vwq_credit>LQ)vf<=1;
 end
 // Source obligations count accepted beats until each real returned event is consumed.
 // Credit return and commit/response are independent obligations.
 localparam integer CB=$clog2(LQ+1);
 reg [CB-1:0] rresp,rcred,wcred,wcommit,rresp_n,rcred_n,wcred_n,wcommit_n;
 reg df;
 wire racc=crq[16]&&permit,wacc=cwq[280]&&permit;
 wire [CB:0] nrresp={1'b0,rresp}+racc-crr[256];
 wire [CB:0] nrcred={1'b0,rcred}+racc-crq_credit;
 wire [CB:0] nwcred={1'b0,wcred}+wacc-cwq_credit;
 wire [CB:0] nwcommit={1'b0,wcommit}+wacc-cwq_done;
 always @(posedge cclk or negedge rst_n)if(!rst_n)begin
  rresp<=0;rcred<=0;wcred<=0;wcommit<=0;
  rresp_n<='1;rcred_n<='1;wcred_n<='1;wcommit_n<='1;df<=0;
 end else begin
  if(rresp!=~rresp_n||rcred!=~rcred_n||wcred!=~wcred_n||wcommit!=~wcommit_n||
    nrresp>LQ||nrcred>LQ||nwcred>LQ||nwcommit>LQ)df<=1;
  rresp<=nrresp[CB-1:0];rresp_n<=~nrresp[CB-1:0];
  rcred<=nrcred[CB-1:0];rcred_n<=~nrcred[CB-1:0];
  wcred<=nwcred[CB-1:0];wcred_n<=~nwcred[CB-1:0];
  wcommit<=nwcommit[CB-1:0];wcommit_n<=~nwcommit[CB-1:0];
 end
 assign cdrained=(MUT==2)?1'b1:!df&&!cf&&!(|faults)&&rresp==0&&rcred==0&&wcred==0&&wcommit==0&&
  !crq[16]&&!cwq[280]&&!crr[256]&&!crq_credit&&!cwq_credit&&!cwq_done;
 // This VM-local predicate must be combined with the synchronized source predicate
 // by the held-owner lease. It cannot by itself prove returned queues consumed.
 assign vdrained=!vf&&!(|faults)&&rdempty&&wdempty&&rcredit==LQ&&wcredit==LQ&&
  !vrq[16]&&!vwq[280]&&!vrr[256]&&!vrq_credit&&!vwq_credit&&!vwq_done;
 assign fault=df|cf|vf|(|faults);
endmodule
`default_nettype wire
