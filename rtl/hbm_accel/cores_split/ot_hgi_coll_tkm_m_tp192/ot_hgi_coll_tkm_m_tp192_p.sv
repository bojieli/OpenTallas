// CORE-HBM-SPLIT 2026-10-23: the HBM-P4-SPLIT plan variant of the die master ot_hgi_coll_tkm_m_tp192
// (rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v5.sv: ot_hgi_coll_tkm_m #(TP 192)) with its body the twin
// ot_hgi_coll_tkm_static_p #(PIPE 1) (root <-> tile crossings registered, priced +2 edges by HBM-P4/P5).  Source of
// the tkm root core extraction (rest_extract.sh); same ports and wiring as ot_hgi_coll_tkm_m.
`timescale 1ns/1ps
module ot_hgi_coll_tkm_m_tp192_p(
 input wire clk,rst_n,start,arg_mode,input wire [31:0] tile_clk,input wire buffer_clk,
 input wire [11:0] cfg_n,input wire [12:0] cfg_k,cfg_nout,input wire [7:0] cfg_g,cfg_gbase,input wire [15:0] cfg_pf,
 input wire [39:0] cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire [3:0] del_slot,del_valid,input wire [2179:0] del_flit,
 output wire w_v,output wire [39:0] w_addr,output wire [15:0] w_mask,output wire [511:0] w_data,
 output wire busy,done,fault,output wire [31:0] stat_cycles);
 ot_hgi_coll_tkm_static_p #(.TP(192),.PIPE(1)) u(.clk(clk),.tile_clk(tile_clk),.buffer_clk(buffer_clk),.rst_n(rst_n),.start(start),
  .cfg_n(cfg_n),.cfg_k(cfg_k),.cfg_nout(cfg_nout),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),.cfg_pf(cfg_pf),
  .cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),
  .del_slot(del_slot & {4{!arg_mode}}),.del_valid(del_valid & {4{!arg_mode}}),.del_flit(del_flit),
  .w_v(w_v),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),
  .busy(busy),.done(done),.fault(fault),.stat_cycles(stat_cycles));
endmodule
