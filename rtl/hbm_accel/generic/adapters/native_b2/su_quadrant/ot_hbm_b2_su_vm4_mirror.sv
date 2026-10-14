`timescale 1ps/1fs
`default_nettype none
// Four actual native B2 slices. Group0 has an exclusive per-quadrant client.
// Group1 and DMA are exported in the VM domain for independent real endpoint binding.
// Client offsets are local13-bit sectors; mirror aperture remains explicit per beat.
module ot_hbm_b2_su_vm4_mirror #(parameter integer MUT=0)(
 input wire [3:0] cclk,input wire vclk,rst_n,input wire [3:0] permit,mirror,
 input wire [4*8*16-1:0] crq,output wire [31:0] crq_credit,output wire [32*257-1:0] crr,
 input wire [32*280-1:0] cwq,output wire [31:0] cwq_credit,cwq_done,
 input wire [32*17-1:0] peer_rq,output wire [31:0] peer_rq_credit,output wire [32*257-1:0] peer_rr,
 input wire [32*281-1:0] peer_wq,output wire [31:0] peer_wq_credit,peer_wq_done,
 input wire [32*281-1:0] dma_q,output wire [31:0] dma_done,
 output wire [7:0] mirror_busy,
 output wire [31:0] fault,output wire [4*8*18-1:0] bank_status
);
 wire [2223:0] cw[0:3],ccw[0:3],cwi[0:3],ccwi[0:3];wire [1:0] cwcr[0:3],ccwcr[0:3],cwicr[0:3],ccwicr[0:3];
 for(genvar q=0;q<4;q=q+1)begin:quad
  wire [8*17-1:0] rq;wire [7:0] rqcr,wqcr,wd;wire [8*257-1:0] rr;wire [8*281-1:0] wq;
  for(genvar b=0;b<8;b=b+1)begin:lane
   wire [15:0] r=crq[(q*8+b)*16+:16];wire [279:0] w=cwq[(q*8+b)*280+:280];wire lf;
   wire bad=r[15]&&(r[14:13]!=0||(mirror[q]&&r[12]))||w[279]&&(w[278:277]!=0||(mirror[q]&&w[276]));
   reg af;always @(posedge cclk[q] or negedge rst_n)if(!rst_n)af<=0;else if(bad)af<=1;
   ot_hbm_b2_lane_cdc #(.MUT(MUT)) link(.cclk(cclk[q]),.vclk(vclk),.rst_n(rst_n),.permit(permit[q]&&!bad&&!af),
    .crq({r[15],mirror[q],mirror[q]?2'b00:2'(q),r[12:0]}),.crq_credit(crq_credit[q*8+b]),.crr(crr[(q*8+b)*257+:257]),
    .cwq({w[279],mirror[q],mirror[q]?2'b00:2'(q),w[276:264],w[263:0]}),.cwq_credit(cwq_credit[q*8+b]),.cwq_done(cwq_done[q*8+b]),
    .vrq(rq[b*17+:17]),.vrq_credit(rqcr[b]),.vrr(rr[b*257+:257]),.vwq(wq[b*281+:281]),.vwq_credit(wqcr[b]),.vwq_done(wd[b]),.fault(lf));
   assign fault[q*8+b]=lf|af;
  end
  wire [16*257-1:0] allrr;wire [15:0] allrc,allwc,alld;wire [7:0] kd;wire vc;wire [2:0] hs;wire [1:0] mb;wire [273:0] unused_cr;
  assign mirror_busy[q*2+:2]=mb;
  assign rr=allrr[8*257-1:0];assign rqcr=allrc[7:0];assign wqcr=allwc[7:0];assign wd=alld[7:0];
  assign peer_rr[q*8*257+:8*257]=allrr[8*257+:8*257];assign peer_rq_credit[q*8+:8]=allrc[15:8];assign peer_wq_credit[q*8+:8]=allwc[15:8];assign peer_wq_done[q*8+:8]=alld[15:8];
  ot_vms_slice #(.NC(1),.RG(2),.WG(2),.RRS(8'h33),.WRS(8'h33)) vm(.clk(vclk),.rst_n(rst_n),.sid(2'(q)),.cq(338'b0),.cr(unused_cr),
   .rq({peer_rq[q*8*17+:8*17],rq}),.rq_cr(allrc),.rr(allrr),.wq({peer_wq[q*8*281+:8*281],wq}),.wq_cr(allwc),.wq_done(alld),
   .dq(dma_q[q*8*281+:8*281]),.dq_done(dma_done[q*8+:8]),.vcb(2130'b0),.vcb_cr(vc),.kq_done(kd),
   .cw_in(cwi[q]),.cw_in_cr(cwicr[q]),.cw_out(cw[q]),.cw_out_cr(cwcr[q]),.ccw_in(ccwi[q]),.ccw_in_cr(ccwicr[q]),.ccw_out(ccw[q]),.ccw_out_cr(ccwcr[q]),
   .bank_status(bank_status[q*8*18+:8*18]),.hub_status(hs),.mirror_busy(mb));
  wire [2223:0] cf[0:3],nf[0:3];wire [1:0] ccr[0:3],ncr[0:3];
  assign cf[0]=cw[q];assign cwi[(q+1)%4]=cf[3];assign ccr[3]=cwicr[(q+1)%4];assign cwcr[q]=ccr[0];
  assign nf[0]=ccw[q];assign ccwi[(q+3)%4]=nf[3];assign ncr[3]=ccwicr[(q+3)%4];assign ccwcr[q]=ncr[0];
  for(genvar s=0;s<3;s=s+1)begin:relay
   ot_vms_relay #(.W(2224),.C(2)) r_cw(.clk(vclk),.rst_n(rst_n),.f_in(cf[s]),.f_out(cf[s+1]),.cr_in(ccr[s+1]),.cr_out(ccr[s]));
   ot_vms_relay #(.W(2224),.C(2)) r_ccw(.clk(vclk),.rst_n(rst_n),.f_in(nf[s]),.f_out(nf[s+1]),.cr_in(ncr[s+1]),.cr_out(ncr[s]));
  end
 end
endmodule
`default_nettype wire
