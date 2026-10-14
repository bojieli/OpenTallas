`timescale 1ps/1fs
`default_nettype none
// Four actual native B2 slices. Group0 has an exclusive per-quadrant client.
// Group1 and DMA are exported in the VM domain for independent real endpoint binding.
// Client offsets are local13-bit sectors; mirror aperture remains explicit per beat.
module ot_hbm_b2_su_vm4_mirror #(parameter integer MUT=0, NC=4, HARD_CLOCKS=0)(
 input wire [3:0] cclk,input wire vclk,rst_n,input wire [3:0] permit,mirror,
 input wire [51:0] vm_child_clk,vm_child_rst_n,
 input wire [23:0] relay_clk,relay_rst_n,
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
  wire [16*257-1:0] allrr;wire [15:0] allrc,allwc,alld;wire [7:0] kd;wire vc;wire [2:0] hs;wire [1:0] mb;wire [NC*274-1:0] unused_cr;
  assign mirror_busy[q*2+:2]=mb;
  assign rr=allrr[8*257-1:0];assign rqcr=allrc[7:0];assign wqcr=allwc[7:0];assign wd=alld[7:0];
  assign peer_rr[q*8*257+:8*257]=allrr[8*257+:8*257];assign peer_rq_credit[q*8+:8]=allrc[15:8];assign peer_wq_credit[q*8+:8]=allwc[15:8];assign peer_wq_done[q*8+:8]=alld[15:8];
  ot_hbm_b2_slice_owned #(.NC(NC),.HARD_CLOCKS(HARD_CLOCKS),.RG(2),.WG(2),.RRS(8'h33),.WRS(8'h33)) vm(.clk(vclk),.rst_n(rst_n),.child_clk(vm_child_clk[q*13+:13]),.child_rst_n(vm_child_rst_n[q*13+:13]),.sid(2'(q)),.cq({NC*338{1'b0}}),.cr(unused_cr),
   .rq({peer_rq[q*8*17+:8*17],rq}),.rq_cr(allrc),.rr(allrr),.wq({peer_wq[q*8*281+:8*281],wq}),.wq_cr(allwc),.wq_done(alld),
   .dq(dma_q[q*8*281+:8*281]),.dq_done(dma_done[q*8+:8]),.vcb(2130'b0),.vcb_cr(vc),.kq_done(kd),
   .cw_in(cwi[q]),.cw_in_cr(cwicr[q]),.cw_out(cw[q]),.cw_out_cr(cwcr[q]),.ccw_in(ccwi[q]),.ccw_in_cr(ccwicr[q]),.ccw_out(ccw[q]),.ccw_out_cr(ccwcr[q]),
   .bank_status(bank_status[q*8*18+:8*18]),.hub_status(hs),.mirror_busy(mb));
  wire [2223:0] cf[0:3],nf[0:3];wire [1:0] ccr[0:3],ncr[0:3];
  assign cf[0]=cw[q];assign cwi[(q+1)%4]=cf[3];assign ccr[3]=cwicr[(q+1)%4];assign cwcr[q]=ccr[0];
  assign nf[0]=ccw[q];assign ccwi[(q+3)%4]=nf[3];assign ncr[3]=ccwicr[(q+3)%4];assign ccwcr[q]=ncr[0];
  for(genvar s=0;s<3;s=s+1)begin:relay
   ot_vms_relay #(.W(2224),.C(2)) r_cw(.clk(HARD_CLOCKS?relay_clk[q*6+s*2]:vclk),.rst_n(HARD_CLOCKS?relay_rst_n[q*6+s*2]:rst_n),.f_in(cf[s]),.f_out(cf[s+1]),.cr_in(ccr[s+1]),.cr_out(ccr[s]));
   ot_vms_relay #(.W(2224),.C(2)) r_ccw(.clk(HARD_CLOCKS?relay_clk[q*6+s*2+1]:vclk),.rst_n(HARD_CLOCKS?relay_rst_n[q*6+s*2+1]:rst_n),.f_in(nf[s]),.f_out(nf[s+1]),.cr_in(ncr[s+1]),.cr_out(ncr[s]));
  end
 end
endmodule
`default_nettype wire

// Distinct physical glue clone of the native B2 slice; independent raw
// clock/reset entries do not establish phase or reset-release qualification.
`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM SLICE (el1011-hbm-b2-vm, SPEC v0.4, 2026-10-12): one quadrant's VM = hub + 8 bank tiles + CW and CCW ring
// stops (one netlist, dir strap) + ring client + COLL star receiver.  This module is glue only (wires between hardened
// tiles; the die places the tiles): no logic of its own.  Both ring directions are wide (2,224 b + a 2-b per-VC credit);
// the COLL star edge is 2,130 b + a 1-b credit.  mirror_busy = {CCW stop, CW stop} (the consumer ORs them).
// Lane index of a wide group = g*8 + b (lane b <-> bank b); lane credits 4 + 2 x relay stages (RRS / WRS).  See ot_vms_bank / ot_vms_hub / ot_vms_rstop / ot_vms_rcl.
module ot_hbm_b2_slice_owned #(
    parameter integer HARD_CLOCKS = 0,
    parameter integer NC = 4, parameter integer RG = 2, parameter integer WG = 2,
    // relay stages each way between each wide lane group's farthest client and the slice face (die contract relay count;
    // SPEC v0.8 D-B2-12): every lane of group g gets 4 + 2 x RRS/WRS[g] credits (ot_vms_bank).  Default 3 = the local
    // lane group's far station (slice -> SU -> SFU -> HC); the bank tile is hardened at its defaults, which must match.
    parameter [RG*4-1:0] RRS = {RG{4'd3}}, parameter [WG*4-1:0] WRS = {WG{4'd3}},
    parameter integer BMUT = 0, parameter integer HMUT = 0, parameter integer CMUT = 0
) (
    input wire [12:0] child_clk,child_rst_n,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [1:0]           sid,
    input  wire [NC*338-1:0]    cq,
    output wire [NC*274-1:0]    cr,
    input  wire [RG*8*17-1:0]   rq,
    output wire [RG*8-1:0]      rq_cr,
    output wire [RG*8*257-1:0]  rr,
    input  wire [WG*8*281-1:0]  wq,
    output wire [WG*8-1:0]      wq_cr,
    output wire [WG*8-1:0]      wq_done,
    input  wire [8*281-1:0]     dq,
    output wire [7:0]           dq_done,
    input  wire [2129:0]        vcb,
    output wire                 vcb_cr,
    output wire [7:0]           kq_done,
    input  wire [2223:0]        cw_in,
    output wire [1:0]           cw_in_cr,
    output wire [2223:0]        cw_out,
    input  wire [1:0]           cw_out_cr,
    input  wire [2223:0]        ccw_in,
    output wire [1:0]           ccw_in_cr,
    output wire [2223:0]        ccw_out,
    input  wire [1:0]           ccw_out_cr,
    output wire [8*18-1:0]      bank_status,
    output wire [2:0]           hub_status,
    output wire [1:0]           mirror_busy
);
    wire [(NC+1)*338-1:0] hcq; wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq; wire [273:0] hr;
    assign hcq = {hq, cq}; assign cr = hcr[NC*274-1:0]; assign hr = hcr[NC*274 +: 274];
    wire [8*285-1:0] pq; wire [7:0] pq_cr; wire [8*266-1:0] pr;
    wire [289:0] cwi, cci; wire cwi_cr, cci_cr; wire [263:0] cco0, cco1;
    wire [8*276-1:0] eg, xq0, xq1; wire [7:0] egc0, egc1, xqc0, xqc1, xqd0, xqd1;
    wire [287:0] rce0, rce1; wire rce0_cr, rce1_cr; wire [265:0] ri0, ri1; wire ri0_cr, ri1_cr;
    wire [2:0] wk01, wk10; wire wk01_cr, wk10_cr; wire ack01, ack10;
    wire [8*281-1:0] kq; wire [7:0] kq_cr; wire [3:0] cb_epoch;
    localparam integer HF = 2, EGC = 1;  // one constant for both sides of each credit link
    ot_vms_hub #(.NC(NC), .CWI(HF), .CCI(HF), .MUT(HMUT)) u_hub (.clk(HARD_CLOCKS?child_clk[0]:clk), .rst_n(HARD_CLOCKS?child_rst_n[0]:rst_n), .sid(sid), .cq(hcq), .cr(hcr), .pq(pq), .pq_cr(pq_cr),
        .pr(pr), .cwi(cwi), .cwi_cr(cwi_cr), .cci(cci), .cci_cr(cci_cr), .cco0(cco0), .cco1(cco1), .status(hub_status));
    genvar b, g;
    for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [RG*17-1:0] brq; wire [RG-1:0] brq_cr; wire [RG*257-1:0] brr;
        wire [WG*281-1:0] bwq; wire [WG-1:0] bwq_cr, bwq_done;
        for (g = 0; g < RG; g = g + 1) begin : g_r
            assign brq[g*17 +: 17] = rq[(g*8 + b)*17 +: 17];
            assign rq_cr[g*8 + b] = brq_cr[g]; assign rr[(g*8 + b)*257 +: 257] = brr[g*257 +: 257];
        end
        for (g = 0; g < WG; g = g + 1) begin : g_w
            assign bwq[g*281 +: 281] = wq[(g*8 + b)*281 +: 281];
            assign wq_cr[g*8 + b] = bwq_cr[g]; assign wq_done[g*8 + b] = bwq_done[g];
        end
        ot_vms_bank #(.RG(RG), .WG(WG), .RRS(RRS), .WRS(WRS), .EGC(EGC), .MUT(BMUT)) u_bank (.clk(HARD_CLOCKS?child_clk[b+1]:clk), .rst_n(HARD_CLOCKS?child_rst_n[b+1]:rst_n), .bid(3'(b)), .sid(sid),
            .rq(brq), .rq_cr(brq_cr), .rr(brr), .wq(bwq), .wq_cr(bwq_cr), .wq_done(bwq_done),
            .dq(dq[b*281 +: 281]), .dq_done(dq_done[b]), .kq(kq[b*281 +: 281]), .kq_cr(kq_cr[b]), .kq_done(kq_done[b]),
            .xq(xq0[b*276 +: 276]), .xq_cr(xqc0[b]), .xq_done(xqd0[b]), .xq2(xq1[b*276 +: 276]), .xq2_cr(xqc1[b]), .xq2_done(xqd1[b]),
            .eg(eg[b*276 +: 276]), .eg_cr({egc1[b], egc0[b]}),
            .pq(pq[b*285 +: 285]), .pq_cr(pq_cr[b]), .pr(pr[b*266 +: 266]), .status(bank_status[b*18 +: 18]));
    end
    ot_vms_rstop #(.HF(HF), .EGC(EGC), .MUT(CMUT)) u_cw (.clk(HARD_CLOCKS?child_clk[9]:clk), .rst_n(HARD_CLOCKS?child_rst_n[9]:rst_n), .sid(sid), .dir(1'b0),
        .l_in(cw_in), .l_in_cr(cw_in_cr), .l_out(cw_out), .l_out_cr(cw_out_cr), .pi(cwi), .pi_cr(cwi_cr),
        .eg(eg), .eg_cr(egc0), .xq(xq0), .xq_cr(xqc0), .xq_done(xqd0), .rce(rce0), .rce_cr(rce0_cr), .ri(ri0), .ri_cr(ri0_cr),
        .wko(wk01), .wko_cr(wk01_cr), .wki(wk10), .wki_cr(wk10_cr), .cco(cco0), .ack_o(ack01), .ack_i(ack10), .mirror_busy(mirror_busy[0]));
    ot_vms_rstop #(.HF(HF), .EGC(EGC), .MUT(CMUT)) u_ccw (.clk(HARD_CLOCKS?child_clk[10]:clk), .rst_n(HARD_CLOCKS?child_rst_n[10]:rst_n), .sid(sid), .dir(1'b1),
        .l_in(ccw_in), .l_in_cr(ccw_in_cr), .l_out(ccw_out), .l_out_cr(ccw_out_cr), .pi(cci), .pi_cr(cci_cr),
        .eg(eg), .eg_cr(egc1), .xq(xq1), .xq_cr(xqc1), .xq_done(xqd1), .rce(rce1), .rce_cr(rce1_cr), .ri(ri1), .ri_cr(ri1_cr),
        .wko(wk10), .wko_cr(wk10_cr), .wki(wk01), .wki_cr(wk01_cr), .cco(cco1), .ack_o(ack10), .ack_i(ack01), .mirror_busy(mirror_busy[1]));
    ot_vms_rcl u_rcl (.clk(HARD_CLOCKS?child_clk[11]:clk), .rst_n(HARD_CLOCKS?child_rst_n[11]:rst_n), .sid(sid), .rce0(rce0), .rce0_cr(rce0_cr), .rce1(rce1), .rce1_cr(rce1_cr),
        .hq(hq), .hr(hr), .ri0(ri0), .ri0_cr(ri0_cr), .ri1(ri1), .ri1_cr(ri1_cr));
    ot_vms_star u_star (.clk(HARD_CLOCKS?child_clk[12]:clk), .rst_n(HARD_CLOCKS?child_rst_n[12]:rst_n), .vcb(vcb), .vcb_cr(vcb_cr), .kq(kq), .kq_cr(kq_cr), .epoch(cb_epoch));
endmodule
`default_nettype wire
