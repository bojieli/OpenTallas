`timescale 1ns/1ps
`default_nettype none
// BINDER4 10-23: HBM d4g leaf-split twin of the as-built die master ot_hgi_coll_tkm_m_tp192 (rtl/hbm_accel/generic/
// collective/p2p/ot_hfd_coll_q_hard_v5.sv, r18h5 source d34578d6f): identical ports and wrapper logic (arg_mode masks
// the delivery slot/valid), with the engine ot_hgi_coll_tkm_static replaced by its plan twin ot_hgi_coll_tkm_static_p
// #(PIPE 1) (over_cap_split/ot_hgi_coll_tkm_m_tp192.split.json: root side registered, TKM finish/done/stat +2 edges,
// OT_HBM_LEAF_SPLIT compiler shift; PIPE 0 == pinned).  Bound by physical/die_plan/hbm/bind/asbuilt.json `alias`.
module ot_hgi_coll_tkm_m_tp192_p #(parameter integer PIPE = 1) (
 input wire clk,rst_n,start,arg_mode,input wire [31:0] tile_clk,input wire buffer_clk,
 input wire [11:0] cfg_n,input wire [12:0] cfg_k,cfg_nout,input wire [7:0] cfg_g,cfg_gbase,input wire [15:0] cfg_pf,
 input wire [39:0] cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire [3:0] del_slot,del_valid,input wire [2179:0] del_flit,
 output wire w_v,output wire [39:0] w_addr,output wire [15:0] w_mask,output wire [511:0] w_data,
 output wire busy,done,fault,output wire [31:0] stat_cycles);
 ot_hgi_coll_tkm_static_p #(.TP(192), .PIPE(PIPE)) u(.clk(clk),.tile_clk(tile_clk),.buffer_clk(buffer_clk),.rst_n(rst_n),
  .start(start),.cfg_n(cfg_n),.cfg_k(cfg_k),.cfg_nout(cfg_nout),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),.cfg_pf(cfg_pf),
  .cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),
  .del_slot(del_slot & {4{!arg_mode}}),.del_valid(del_valid & {4{!arg_mode}}),.del_flit(del_flit),
  .w_v(w_v),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),
  .busy(busy),.done(done),.fault(fault),.stat_cycles(stat_cycles));
endmodule
`default_nettype wire
