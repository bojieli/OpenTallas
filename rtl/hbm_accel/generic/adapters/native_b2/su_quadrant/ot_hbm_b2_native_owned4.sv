`timescale 1ps/1fs
`default_nettype none
// Actual four B2 slices. Shared group1 classes: 0 SU, 1 quant, 2 DMA peer.
// Native DMA front writes use separate done-only DQ transport, never WRS credits.
// Source ingress capacity is reserved before posting; permits govern dequeue only.
module ot_hbm_b2_native_owned4 #(parameter integer MUT=0,FASTFIN=0,FRONTFAST=0)(
 input wire [3:0] su_clk,quant_clk,dma_clk,input wire vclk,rst_n,
 input wire [3:0] su_rreq,su_wreq,su_drained,su_mirror,
 input wire [32*16-1:0] su_rq,output wire [31:0] su_rcredit,output wire [32*257-1:0] su_rr,
 input wire [32*280-1:0] su_wq,output wire [31:0] su_wcredit,su_done,
 output wire [3:0] su_rgrant,su_wgrant,su_rack,su_wack,
 input wire [4*683-1:0] quant_rec,input wire [3:0] quant_mirror,
 output wire [11:0] quant_ret,output wire [3:0] quant_drained,
 input wire [3:0] dma_rreq,dma_wreq,dma_peer_drained,
 input wire [32*17-1:0] dma_rq,output wire [31:0] dma_rcredit,output wire [32*257-1:0] dma_rr,
 input wire [32*281-1:0] dma_wq,output wire [31:0] dma_wcredit,dma_wdone,
 output wire [3:0] dma_rgrant,dma_wgrant,dma_rack,dma_wack,
 input wire [32*281-1:0] dma_dq,output wire [31:0] dma_dq_done,
 input wire [3:0] probe_clk,probe_permit,probe_mirror,
 input wire [32*16-1:0] probe_rq,output wire [31:0] probe_rcredit,output wire [32*257-1:0] probe_rr,
 input wire [32*280-1:0] probe_wq,output wire [31:0] probe_wcredit,probe_done,
 output wire [31:0] su_cdrained,su_vdrained,dma_cdrained,dma_vdrained,
 output wire [11:0] vm_rgrant,vm_wgrant,
 output wire [4*8*18-1:0] bank_status,output wire [127:0] fault
);
 wire [32*17-1:0] qrq;wire [32*281-1:0] qwq;wire [32*257-1:0] qrr;
 wire [31:0] qrc,qwc,qd,qcd,qvd,qrrdy,qwrdy,qfault;
 wire [3:0] qrg,qwg,qreqr,qreqw,qbusy,qvgr,qvgw,qrack,qwack;
 ot_hgi_qdq_native_peer4_owned #(.MUT_QDQ(MUT==2?1:0),.FASTFIN(FASTFIN),.FRONTFAST(FRONTFAST)) quant(
  .cclk(quant_clk),.vclk(vclk),.rst_n(rst_n),.permit(qrg|qwg),.mirror(quant_mirror),.rec(quant_rec),.ret(quant_ret),
  .rg_req(qreqr),.wg_req(qreqw),.rg_gnt(qrg),.wg_gnt(qwg),.vm_rg_gnt(qvgr),.vm_wg_gnt(qvgw),
  .peer_rq(qrq),.peer_rq_credit(qrc),.peer_rr(qrr),.peer_wq(qwq),.peer_wq_credit(qwc),.peer_wq_done(qd),
  .adapter_fault(qfault),.cdrained(qcd),.vdrained(qvd),.rready(qrrdy),.wready(qwrdy),.qdrained(quant_drained),.qbusy(qbusy));
 wire [32*17-1:0] brq;wire [32*281-1:0] bwq;wire [32*257-1:0] brr;wire [31:0] brc,bwc,bd;
 for(genvar q=0;q<4;q=q+1)begin:quad
  wire [3*8*17-1:0] srq;wire [3*8*281-1:0] swq;wire [3*8*257-1:0] srr;
  wire [23:0] src,swc,sd,rrdy,wrdy,vd,cd;wire [2:0] rg,wg,rack,wack,vrg,vwg;wire mf;
  assign srq[8*17+:8*17]=qrq[q*8*17+:8*17];assign swq[8*281+:8*281]=qwq[q*8*281+:8*281];
  assign qrr[q*8*257+:8*257]=srr[8*257+:8*257];assign qrc[q*8+:8]=src[8+:8];assign qwc[q*8+:8]=swc[8+:8];assign qd[q*8+:8]=sd[8+:8];
  assign rrdy[8+:8]=qrrdy[q*8+:8];assign wrdy[8+:8]=qwrdy[q*8+:8];assign vd[8+:8]=qvd[q*8+:8];assign cd[8+:8]=qcd[q*8+:8];
  assign qrg[q]=rg[1];assign qwg[q]=wg[1];assign qvgr[q]=vrg[1];assign qvgw[q]=vwg[1];assign qrack[q]=rack[1];assign qwack[q]=wack[1];
  for(genvar b=0;b<8;b=b+1)begin:lane
   wire [15:0] r=su_rq[(q*8+b)*16+:16];wire [279:0] w=su_wq[(q*8+b)*280+:280];
   wire bad=r[15]&&(r[14:13]!=0||(su_mirror[q]&&r[12]))||w[279]&&(w[278:277]!=0||(su_mirror[q]&&w[276]));
   reg af;(* async_reg="true" *)reg af1,af2,an1,an2;
   always @(posedge su_clk[q] or negedge rst_n)if(!rst_n)af<=0;else if(bad)af<=1;
   always @(posedge vclk or negedge rst_n)if(!rst_n)begin af1<=0;af2<=0;an1<=1;an2<=1;end else begin af1<=af;af2<=af1;an1<=~af;an2<=an1;end
   wire allow=!af2&&(af2==~an2);wire lf;
   ot_hbm_b2_lane_cdc_owned slink(.cclk(su_clk[q]),.vclk(vclk),.rst_n(rst_n),.permit(rg[0]|wg[0]),.vrpermit(vrg[0]&&allow),.vwpermit(vwg[0]&&allow),
    .crq({r[15],su_mirror[q],su_mirror[q]?2'b00:2'(q),r[12:0]}),.crq_credit(su_rcredit[q*8+b]),.crr(su_rr[(q*8+b)*257+:257]),
    .cwq({w[279],su_mirror[q],su_mirror[q]?2'b00:2'(q),w[276:264],w[263:0]}),.cwq_credit(su_wcredit[q*8+b]),.cwq_done(su_done[q*8+b]),
    .vrq(srq[b*17+:17]),.vrq_credit(src[b]),.vrr(srr[b*257+:257]),.vwq(swq[b*281+:281]),.vwq_credit(swc[b]),.vwq_done(sd[b]),
    .fault(lf),.cdrained(cd[b]),.vdrained(vd[b]),.rready(rrdy[b]),.wready(wrdy[b]));
   assign fault[q*8+b]=lf|af;assign su_cdrained[q*8+b]=cd[b];assign su_vdrained[q*8+b]=vd[b];
   ot_hbm_b2_lane_cdc_owned dlink(.cclk(dma_clk[q]),.vclk(vclk),.rst_n(rst_n),.permit(rg[2]|wg[2]),.vrpermit(vrg[2]),.vwpermit(vwg[2]),
    .crq(dma_rq[(q*8+b)*17+:17]),.crq_credit(dma_rcredit[q*8+b]),.crr(dma_rr[(q*8+b)*257+:257]),
    .cwq(dma_wq[(q*8+b)*281+:281]),.cwq_credit(dma_wcredit[q*8+b]),.cwq_done(dma_wdone[q*8+b]),
    .vrq(srq[(16+b)*17+:17]),.vrq_credit(src[16+b]),.vrr(srr[(16+b)*257+:257]),.vwq(swq[(16+b)*281+:281]),.vwq_credit(swc[16+b]),.vwq_done(sd[16+b]),
    .fault(fault[32+q*8+b]),.cdrained(cd[16+b]),.vdrained(vd[16+b]),.rready(rrdy[16+b]),.wready(wrdy[16+b]));
   assign dma_cdrained[q*8+b]=cd[16+b];assign dma_vdrained[q*8+b]=vd[16+b];
  end
  ot_hbm_b2_peer_mux_q #(.MUT(MUT==1?1:0)) station(.clk(vclk),.rst_n(rst_n),.src_clk({dma_clk[q],quant_clk[q],su_clk[q]}),
   .rreq({dma_rreq[q],qbusy[q]|quant_rec[q*683],su_rreq[q]}),.wreq({dma_wreq[q],qbusy[q]|quant_rec[q*683],su_wreq[q]}),
   .src_drained({dma_peer_drained[q]&&(&cd[16+:8]),quant_drained[q],su_drained[q]&&(&cd[0+:8])}),
   .lane_rready(rrdy),.lane_wready(wrdy),.lane_vdrained(vd),.src_rq(srq),.src_rcredit(src),.src_rr(srr),.src_wq(swq),.src_wcredit(swc),.src_done(sd),
   .rgrant(rg),.wgrant(wg),.rack(rack),.wack(wack),.vm_rgrant(vrg),.vm_wgrant(vwg),
   .rq(brq[q*8*17+:8*17]),.rcredit(brc[q*8+:8]),.rr(brr[q*8*257+:8*257]),.wq(bwq[q*8*281+:8*281]),.wcredit(bwc[q*8+:8]),.done(bd[q*8+:8]),.fault(mf));
  assign su_rgrant[q]=rg[0];assign su_wgrant[q]=wg[0];assign su_rack[q]=rack[0];assign su_wack[q]=wack[0];
  assign dma_rgrant[q]=rg[2];assign dma_wgrant[q]=wg[2];assign dma_rack[q]=rack[2];assign dma_wack[q]=wack[2];
  assign vm_rgrant[q*3+:3]=vrg;assign vm_wgrant[q*3+:3]=vwg;assign fault[96+q*8+:8]={8{mf}};
 end
 assign fault[64+:32]=qfault;
 ot_hbm_b2_su_vm4 vm(.cclk(probe_clk),.vclk(vclk),.rst_n(rst_n),.permit(probe_permit),.mirror(probe_mirror),
  .crq(probe_rq),.crq_credit(probe_rcredit),.crr(probe_rr),.cwq(probe_wq),.cwq_credit(probe_wcredit),.cwq_done(probe_done),
  .peer_rq(brq),.peer_rq_credit(brc),.peer_rr(brr),.peer_wq(bwq),.peer_wq_credit(bwc),.peer_wq_done(bd),.dma_q(dma_dq),.dma_done(dma_dq_done),.fault(),.bank_status(bank_status));
endmodule
`default_nettype wire
