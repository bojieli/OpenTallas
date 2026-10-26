`timescale 1ns/1ps
`default_nettype none
// Native VM producer at the whole-SU LG boundary. The SU station already lives
// in each pgslice: no second ot_hbm_su_static_vm_ports instance belongs here.
// LG selectors are external compiled calendar pins, never request-derived.
// Bank slot pins are external configuration/calendar inputs. Run reserves wide
// owner0; preload uses DMA owner WG+4=5 through dq, with all SU commands idle.
// No behavioral memory or expected-answer source exists in this module.
module ot_hbm_su_native_vm #(
 parameter integer MUT_LG=0,MUT_BANK=0
)(
 input wire [31:0] clk_bank,input wire rst_n,
 input wire [32*17-1:0] lg_rq,input wire [32*281-1:0] lg_wq,
 output wire [32*257-1:0] lg_rr,output wire [31:0] lg_w_done,
 input wire [31:0] cal_rd,cal_wr,
 input wire [31:0] rslot_v,wslot_v,
 input wire [32*2-1:0] rslot,input wire [32*3-1:0] wslot,
 input wire [32*281-1:0] preload_wq,output wire [31:0] preload_done,
 output wire [31:0] lg_fault,output wire [32*18-1:0] bank_status
);
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [8*17-1:0] nrq;
  wire [8*281-1:0] nwq;
  wire [8*257-1:0] nrr;
  wire [7:0] ndone;
  ot_hbm_vm_lg_static_split #(.READ_RETURN(10),.WRITE_RETURN(7),.MUT(MUT_LG)) lg(
   .clk(clk_bank[q*8+:8]),.rst_n(rst_n),
   .local_rq(lg_rq[q*8*17+:8*17]),.far_rq(136'd0),
   .local_wq(lg_wq[q*8*281+:8*281]),.far_wq(2248'd0),
   .local_read(cal_rd[q*8+:8]),.local_write(cal_wr[q*8+:8]),
   .near_rq(nrq),.near_wq(nwq),.near_rr(nrr),.near_w_done(ndone),
   .local_rr(lg_rr[q*8*257+:8*257]),.far_rr(),
   .local_w_done(lg_w_done[q*8+:8]),.far_w_done(),.bank_fault(lg_fault[q*8+:8]));
  for(genvar b=0;b<8;b=b+1)begin:g_b
   localparam integer I=q*8+b;
   wire [3*257-1:0] rr3;
   ot_vms_bank_static #(.RG(3),.WG(1),.MUT(MUT_BANK)) bank(
    .clk(clk_bank[I]),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
    .rslot_v(rslot_v[I]),.rslot(rslot[I*2+:2]),
    .wslot_v(wslot_v[I]),.wslot(wslot[I*3+:3]),
    .rq({34'd0,nrq[b*17+:17]}),.rr(rr3),
    .wq(nwq[b*281+:281]),.wq_done(ndone[b]),
    .dq(preload_wq[I*281+:281]),.dq_done(preload_done[I]),
    .kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
    .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),
    .status(bank_status[I*18+:18]));
   assign nrr[b*257+:257]=rr3[0+:257];
  end
 end
endmodule
`default_nettype wire
