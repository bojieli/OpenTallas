`timescale 1ps/1fs
`default_nettype none
// Real q8 endpoints for group1 of ot_hbm_b2_su_vm4. Each quadrant owns its
// local8 lanes. CDC payload storage is a separate, unclosed physical requirement.
// Engine CK833.333ps -> VM CKV1111.111ps; no pulse crosses these ports directly.
// permit/mirror must remain owned and stable until the actual endpoint and CDC
// queues drain. Exclusive read/write grants are supplied by the parent arbiter.
module ot_hgi_qdq_native_peer4_drain #(parameter integer MUT_QDQ=0, MUT_CDC=0, FASTFIN=0, FRONTFAST=0, FINFLAGS=0, WRSPLIT=0,PAYBYPASS=0) (
 input wire [3:0] cclk,
 input wire vclk, rst_n,
 input wire [3:0] permit, mirror,
 input wire [4*683-1:0] rec,
 output wire [11:0] ret,
 output wire [3:0] rg_req, wg_req,
 input wire [3:0] rg_gnt, wg_gnt,
 output wire [32*17-1:0] peer_rq,
 input wire [31:0] peer_rq_credit,
 input wire [32*257-1:0] peer_rr,
 output wire [32*281-1:0] peer_wq,
 input wire [31:0] peer_wq_credit, peer_wq_done,
 output wire [31:0] adapter_fault,
 output wire [31:0] cdrained, vdrained,
 output wire [3:0] qdrained
);
 for(genvar q=0;q<4;q=q+1)begin:quad
  wire [8*16-1:0] rq;
  wire [8*280-1:0] wq;
  wire [8*257-1:0] rr;
  wire [7:0] rq_credit,wq_credit,wq_done;
  reg [5:0] rec_pending,rec_pending_n;reg ledger_fault;
  wire accepted=rec[q*683]&&ret[q*3];
  wire [6:0] next_pending={1'b0,rec_pending}+accepted-ret[q*3+1];
  always @(posedge cclk[q] or negedge rst_n)
   if(!rst_n)begin rec_pending<=0;rec_pending_n<=6'h3f;ledger_fault<=0;end
   else begin
    if(rec_pending!=~rec_pending_n||next_pending>32)ledger_fault<=1;
    rec_pending<=next_pending[5:0];rec_pending_n<=~next_pending[5:0];
   end
  assign qdrained[q]=!(|adapter_fault[q*8+:8])&&(&cdrained[q*8+:8])&&!ledger_fault&&rec_pending==0&&rec_pending==~rec_pending_n&&!accepted&&!ret[q*3+1]&&!rg_req[q]&&!wg_req[q];
  // qpin4 preserves the actual q8 LQ10 credit counts and LD16 storage.
  // Record format, descriptor/shape validation and fault retirement stay in FR.
  // Physical FR/CORE hard-child defaults are SPANPIPE1. The software qpin4
  // default0 is an unselected alternative and cannot qualify those real views.
  ot_hgi_qdq_q_pin4 #(.SPANPIPE(1),.MUT(MUT_QDQ),.FASTFIN(FASTFIN),.FRONTFAST(FRONTFAST),.FINFLAGS(FINFLAGS),.WRSPLIT(WRSPLIT),.PAYBYPASS(PAYBYPASS)) endpoint(
   .clk(cclk[q]),.rst_n(rst_n),.rec(rec[q*683+:683]),.ret(ret[q*3+:3]),
   .wrq(rq),.wrq_cr(rq_credit),
   .wrr_p0(rr[0+:514]),.wrr_p1(rr[514+:514]),
   .wrr_p2(rr[1028+:514]),.wrr_p3(rr[1542+:514]),
   .wwq(wq),.wwq_cr(wq_credit),.wwq_done(wq_done),
   .rg_req(rg_req[q]),.rg_gnt(rg_gnt[q]&&permit[q]),
   .wg_req(wg_req[q]),.wg_gnt(wg_gnt[q]&&permit[q]));
  for(genvar b=0;b<8;b=b+1)begin:lane
   wire [15:0] r=rq[b*16+:16];
   wire [279:0] w=wq[b*280+:280];
   // Local13-bit sector aperture. Global high bits are rejected, never masked.
   // Mirrored aperture is half-size; sid00 plus mirror is the native convention.
   wire bad=(r[15]&&(r[14:13]!=0||(mirror[q]&&r[12]))) ||
            (w[279]&&(w[278:277]!=0||(mirror[q]&&w[276])));
   reg aperture_fault;
   always @(posedge cclk[q] or negedge rst_n)
    if(!rst_n)aperture_fault<=0;else if(bad)aperture_fault<=1;
   wire cdc_fault;
   ot_hbm_b2_lane_cdc_drain #(.LQ(10),.MUT(MUT_CDC)) link(
    .cclk(cclk[q]),.vclk(vclk),.rst_n(rst_n),
    .permit(permit[q]&&!bad&&!aperture_fault),
    .crq({r[15],mirror[q],mirror[q]?2'b00:2'(q),r[12:0]}),
    .crq_credit(rq_credit[b]),.crr(rr[b*257+:257]),
    .cwq({w[279],mirror[q],mirror[q]?2'b00:2'(q),w[276:264],w[263:0]}),
    .cwq_credit(wq_credit[b]),.cwq_done(wq_done[b]),
    .vrq(peer_rq[(q*8+b)*17+:17]),.vrq_credit(peer_rq_credit[q*8+b]),
    .vrr(peer_rr[(q*8+b)*257+:257]),
    .vwq(peer_wq[(q*8+b)*281+:281]),.vwq_credit(peer_wq_credit[q*8+b]),
    .vwq_done(peer_wq_done[q*8+b]),.fault(cdc_fault),.cdrained(cdrained[q*8+b]),.vdrained(vdrained[q*8+b]));
   assign adapter_fault[q*8+b]=aperture_fault|cdc_fault|ledger_fault;
  end
 end
endmodule
`default_nettype wire
