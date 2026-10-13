`timescale 1ns/1ps
`default_nettype none
// el1013-idx-tiles: the native SW slot-5 binding of ot_hgi_idx_unit_b2_ixw1 with the TILED wide adapter
// (ot_hgi_idx_unit IXW = 2 -> ot_hgi_idx_index_wt).  Same ports; nothing else differs.
module ot_hgi_idx_unit_b2_ixw2 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [2074:0] rec,output wire [2:0] ret,
 output wire [337:0] vmq,input wire [273:0] vmr,
 output wire [135:0] rq,input wire [7:0] rq_cr,input wire [2055:0] rr,
 output wire rg_req,input wire rg_gnt,
 output wire [2247:0] wq,input wire [7:0] wq_cr,wq_done,
 output wire wg_req,input wire wg_gnt,
 output wire [89:0] sel_fs,output wire [1047:0] sel_qb,input wire sel_qbr,
 output wire [344:0] sel_kin,input wire [611:0] sel_to,output wire sel_toc,
 input wire [71:0] sel_co,output wire sel_coc,input wire [1:0] sel_ev,
 output wire [511:0] iks_e,output wire mapping_fault);
 ot_hgi_idx_unit_b2_ixw1 #(.MUT(MUT),.IXW(2)) u(.clk(clk),.rst_n(rst_n),.rec(rec),.ret(ret),.vmq(vmq),.vmr(vmr),
  .rq(rq),.rq_cr(rq_cr),.rr(rr),.rg_req(rg_req),.rg_gnt(rg_gnt),.wq(wq),.wq_cr(wq_cr),.wq_done(wq_done),
  .wg_req(wg_req),.wg_gnt(wg_gnt),.sel_fs(sel_fs),.sel_qb(sel_qb),.sel_qbr(sel_qbr),.sel_kin(sel_kin),
  .sel_to(sel_to),.sel_toc(sel_toc),.sel_co(sel_co),.sel_coc(sel_coc),.sel_ev(sel_ev),.iks_e(iks_e),
  .mapping_fault(mapping_fault));
endmodule
`default_nettype wire
