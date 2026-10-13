`timescale 1ns/1ps
`default_nettype none
// Actual native SW slot5 binding. All memory read operands are REPL; output
// writes are SW owned. Guard checks full addresses before rebase/truncation.
// Record registered once; owner stays fixed through last native write-done.
// Physical decomposition and source-matched native production gates pending.
module ot_hgi_idx_unit_b2_ixw1 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire [2074:0] rec,output reg [2:0] ret,
 output wire [337:0] vmq,input wire [273:0] vmr,
 output wire [135:0] rq,input wire [7:0] rq_cr,input wire [2055:0] rr,
 output wire rg_req,input wire rg_gnt,
 output wire [2247:0] wq,input wire [7:0] wq_cr,wq_done,
 output wire wg_req,input wire wg_gnt,
 output wire [89:0] sel_fs,output wire [1047:0] sel_qb,input wire sel_qbr,
 output wire [344:0] sel_kin,input wire [611:0] sel_to,output wire sel_toc,
 input wire [71:0] sel_co,output wire sel_coc,input wire [1:0] sel_ev,
 output wire [511:0] iks_e,output wire mapping_fault);
 wire ix,legal;wire [2074:0] rebased;
 ot_hgi_idx_b2_record_guard u_guard(.rec(rec),.index_record(ix),.legal(legal),.rebased(rebased));
 reg [2074:0] core_rec;reg busy,dispatch;wire [2:0] core_ret;
 wire [127:0] old_rq;wire [2239:0] old_wq;wire [31:0] old_rcr;
 wire [8223:0] old_rr;wire [7:0] old_wcr,old_done;
 wire read_fault,write_fault;
 assign mapping_fault=read_fault|write_fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin core_rec<=0;busy<=0;dispatch<=0;ret<=3'b001;end
  else begin
   core_rec[0]<=0;ret[2:1]<=0;
   if(!busy&&rec[0])begin
    if(!legal)ret<=3'b101;
    else begin core_rec<=rebased;busy<=1;dispatch<=1;ret<=0;end
   end else if(dispatch)dispatch<=0;
   else if(busy&&core_ret[1])begin busy<=0;ret<={core_ret[2]|mapping_fault,1'b1,1'b1};end
  end
 end
 ot_hbm_b2_xread_aperture u_read(.clk(clk),.rst_n(rst_n),.permit(busy),.sid(2'd0),.mirror(1'b1),
  .old_q({384'd0,old_rq}),.old_cr(old_rcr),.old_rsp(old_rr),.rq(rq),.rq_cr(rq_cr),.rr(rr),.fault(read_fault));
 ot_hbm_b2_xwrite_aperture u_write(.clk(clk),.rst_n(rst_n),.permit(busy),.sid(2'd0),.mirror(1'b0),
  .old_q(old_wq),.old_cr(old_wcr),.old_done(old_done),.wq(wq),.wq_cr(wq_cr),.wq_done(wq_done),.fault(write_fault));
 ot_hgi_idx_unit #(.MUT(MUT),.PREF(1),.TOPKW(1),.TWIW(8),.NGLOB(1),.IKS(1),.IKS_EVEN(1),.IXW(1),.IXNL(8),.IXLQ(10)) u_core(
  .clk(clk),.rst_n(rst_n),.rec(core_rec),.ret(core_ret),.vmq(vmq),.vmr(vmr),
  .wrq(old_rq),.wrq_cr(old_rcr[7:0]),.wrr(old_rr[2055:0]),.rg_req(rg_req),.rg_gnt(rg_gnt),
  .wwq(old_wq),.wwq_cr(old_wcr),.wwq_done(old_done),.wg_req(wg_req),.wg_gnt(wg_gnt),
  .sel_fs(sel_fs),.sel_qb(sel_qb),.sel_qbr(sel_qbr),.sel_kin(sel_kin),.sel_to(sel_to),.sel_toc(sel_toc),
  .sel_co(sel_co),.sel_coc(sel_coc),.sel_ev(sel_ev),.iks_e(iks_e));
endmodule
`default_nettype wire
