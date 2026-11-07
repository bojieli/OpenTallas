`timescale 1ns/1ps
`default_nettype none
// DIE-HEAD-76 hd_lep0N_vC = Codex REMEDY Variant B, form D2 (11-06): hd_lep0N split into one LEP hub and four
// pair-local regions.  Region k = pair macro u_pair (unchanged signed child ot_s81hd_lep_pair) + the LEP TX landing
// FIFO of lane k (ot_s81hd_lep_txlane: credit sender, 5 SRAM, lo_k face) + (in the plan) the coll_ik / coll_ok
// partition faces.  The hub keeps the shared LEP (frame build, RX pair re-assembly, MU tag), the MU landing and lw_o.
// Cut nets per lane k (no others):
//   hub -> region  tx_psh, tx_pg[18] (push copies), tx_wd[553] {sq, frame half}, k_li_r (RX credit), k_rxv
//                  (+ tx_rt / tx_rst[106] reset leaves only in the LOCAL_RST=0 proof form)
//   region -> hub  tx_ovf (sticky), k_li_v, k_li_d[553], k_flt[3]
// Every hub->region and region->hub net is a credit link, a push without back-pressure, or a sticky flag, so the
// plan may add the same fixed number of face cycles to each bundle (PIN CYCLES, emitted by the plan; see the
// lane report).  This file adds 0 cycles: ot_s81hd_lep0N_split_core (hub + 4 regions, LOCAL_RST=0) is
// cycle-equal to ot_s81hd_lep0N_noidx_core PAIR=1 (tools/s81_head/head_lep_split_equiv.sh).
// LOCAL_RST=1 (physical form): the region builds its own ot_rst_relay_tree3 from its rst_n, the same 3-edge
// synchronous-release contract as the LEP tree leaves it replaces.
module ot_s81hd_lep0N_hub_core (
 input wire ck,rst_n,
 input wire[1103:0]lepk_i0,output wire[1103:0]lepk_o0,
 input wire lepf_i0,input wire[44:0]unit_i0,
 output wire[31:0]ctrl_o0,output wire fault_o0,output reg[10:0]lw_o,
 output wire[3:0]tx_rt,output wire[4*106-1:0]tx_rst,output wire[3:0]tx_psh,output wire[4*18-1:0]tx_pg,
 output wire[4*553-1:0]tx_wd,input wire[3:0]tx_ovf,
 input wire[3:0]k_li_v,output wire[3:0]k_li_r,input wire[4*553-1:0]k_li_d,
 output wire[3:0]k_rxv,input wire[4*3-1:0]k_flt
);
 wire mwv,mrv,mf;wire[1103:0]mwd,mrd;
 always@(posedge ck or negedge rst_n)
  if(!rst_n)lw_o<=0;else lw_o<={mwd[1056:1047],mwv};
 ot_s81hd_lep_idx_nr_txext #(.DT(512),.DR(12),.CRED(12),.SRAM(1),
  .NB(80),.RX_SRAM(1),.IN_PIPE(1),.NATIVE32(1),.IDX_EN(0))u_lep(
  .clk(ck),.rst_n(rst_n),.ro(lepk_i0),.ri(lepk_o0),
  .lo0_v(),.lo0_r(1'b0),.lo0_d(),.lo1_v(),.lo1_r(1'b0),.lo1_d(),
  .lo2_v(),.lo2_r(1'b0),.lo2_d(),.lo3_v(),.lo3_r(1'b0),.lo3_d(),
  .li0_v(k_li_v[0]),.li0_r(k_li_r[0]),.li0_d(k_li_d[0*553+:553]),
  .li1_v(k_li_v[1]),.li1_r(k_li_r[1]),.li1_d(k_li_d[1*553+:553]),
  .li2_v(k_li_v[2]),.li2_r(k_li_r[2]),.li2_d(k_li_d[2*553+:553]),
  .li3_v(k_li_v[3]),.li3_r(k_li_r[3]),.li3_d(k_li_d[3*553+:553]),
  .rxv(k_rxv[1:0]),.rxvb(k_rxv[3:2]),.sl_f(lepf_i0),
  .l0_f(k_flt[0+:3]),.l1_f(k_flt[3+:3]),.l2_f(k_flt[6+:3]),.l3_f(k_flt[9+:3]),
  .mu_c(unit_i0[44:11]),.mu_rt(ctrl_o0),
  .ml_wv(mwv),.ml_wd(mwd),.ml_rv(mrv),.ml_rd(mrd),.ml_f(mf),
  .fault(fault_o0),.tl(276'd0),.ca(),.cb(),
  .tx_rt(tx_rt),.tx_rst(tx_rst),.tx_psh(tx_psh),.tx_pg(tx_pg),.tx_wd(tx_wd),.tx_ovf(tx_ovf));
 dsdv_mu_land_head_nr #(.NB(80),.NS(1),.SRAM(1),.W(1104))u_land(
  .clk(ck),.rst_n(rst_n),.wv(mwv),.wd(mwd),.rc(unit_i0[10:0]),
  .rv(mrv),.rd(mrd),.fault(mf));
endmodule

module ot_s81hd_lep0N_region_core #(parameter integer K=0, parameter [0:0] CHB=1'b1, parameter integer LOCAL_RST=1)(
 input wire ck,rst_n,
 input wire[513:0]coll_i,output wire[511:0]coll_o,
 input wire tx_rt,input wire[105:0]tx_rst,input wire tx_psh,input wire[17:0]tx_pg,input wire[552:0]tx_wd,
 output wire tx_ovf,
 output wire k_li_v,input wire k_li_r,output wire[552:0]k_li_d,
 input wire k_rxv,output wire[2:0]k_flt
);
 wire lv,lr;wire[552:0]ld;
 wire rt;wire[105:0]rx;
 generate if(LOCAL_RST!=0)begin:g_local_rst
  // the lane's 1 + 106 TX reset leaves, rebuilt locally: same 3-edge release as the LEP u_rstr leaves
  wire[106:0]rl;
  ot_rst_relay_tree3 #(.REGIONS(107))u_rstr(.clk(ck),.rst_n_in(rst_n),.rst_n(rl));
  assign rt=rl[0];assign rx=rl[106:1];
 end else begin:g_hub_rst
  assign rt=tx_rt;assign rx=tx_rst;
 end endgenerate
 ot_s81hd_lep_txlane #(.DT(512),.DR(12),.CRED(12),.SRAM(1),.HOST_EN(0),.MU_EN(1),.RX_SRAM(1),.AB_EN(1),.NB(80),
  .IN_PIPE(1),.NATIVE32(1),.IDX_EN(0),.T(K))u_txl(
  .clk(ck),.rt_i(rt),.rst_i(rx),.psh_i(tx_psh),.pg_i(tx_pg),.wd_i(tx_wd),.lo_r_i(lr),
  .lo_v_o(lv),.lo_d_o(ld),.ovf_o(tx_ovf));
 ot_s81hd_lep_pair #(.CHB(CHB))u_pair(.clk(ck),.rst_n(rst_n),
  .k_lo_v(lv),.k_lo_r(lr),.k_lo_d(ld),
  .k_li_v(k_li_v),.k_li_r(k_li_r),.k_li_d(k_li_d),
  .k_rxv(k_rxv),.k_flt(k_flt),.coll_i(coll_i),.coll_o(coll_o));
endmodule

// Proof vehicle: same ports as ot_s81hd_lep0N_noidx_core (PAIR=1); hub instance 'u' so the hub names equal the
// original core names; regions g_rg[k].u_reg.
module ot_s81hd_lep0N_split_core #(parameter[3:0]CH_B=4'b1111, parameter integer LOCAL_RST=0)(
 input wire ck,rst_n,
 input wire[513:0]coll_i0,coll_i1,coll_i2,coll_i3,
 output wire[511:0]coll_o0,coll_o1,coll_o2,coll_o3,
 input wire[1103:0]lepk_i0,output wire[1103:0]lepk_o0,
 input wire lepf_i0,input wire[44:0]unit_i0,
 output wire[31:0]ctrl_o0,output wire fault_o0,output wire[10:0]lw_o
);
 wire[3:0]tx_rt,tx_psh,tx_ovf,li_v,li_r,rxv;wire[4*106-1:0]tx_rst;wire[4*18-1:0]tx_pg;
 wire[4*553-1:0]tx_wd,li_d;wire[4*3-1:0]flt;
 wire[513:0]ci[0:3];wire[511:0]co[0:3];
 assign ci[0]=coll_i0;assign ci[1]=coll_i1;assign ci[2]=coll_i2;assign ci[3]=coll_i3;
 assign coll_o0=co[0];assign coll_o1=co[1];assign coll_o2=co[2];assign coll_o3=co[3];
 ot_s81hd_lep0N_hub_core u(.ck(ck),.rst_n(rst_n),.lepk_i0(lepk_i0),.lepk_o0(lepk_o0),.lepf_i0(lepf_i0),.unit_i0(unit_i0),
  .ctrl_o0(ctrl_o0),.fault_o0(fault_o0),.lw_o(lw_o),
  .tx_rt(tx_rt),.tx_rst(tx_rst),.tx_psh(tx_psh),.tx_pg(tx_pg),.tx_wd(tx_wd),.tx_ovf(tx_ovf),
  .k_li_v(li_v),.k_li_r(li_r),.k_li_d(li_d),.k_rxv(rxv),.k_flt(flt));
 genvar k;
 generate for(k=0;k<4;k=k+1)begin:g_rg
  ot_s81hd_lep0N_region_core #(.K(k),.CHB(CH_B[k]),.LOCAL_RST(LOCAL_RST))u_reg(.ck(ck),.rst_n(rst_n),
   .coll_i(ci[k]),.coll_o(co[k]),
   .tx_rt(tx_rt[k]),.tx_rst(tx_rst[k*106+:106]),.tx_psh(tx_psh[k]),.tx_pg(tx_pg[k*18+:18]),.tx_wd(tx_wd[k*553+:553]),
   .tx_ovf(tx_ovf[k]),.k_li_v(li_v[k]),.k_li_r(li_r[k]),.k_li_d(li_d[k*553+:553]),.k_rxv(rxv[k]),.k_flt(flt[k*3+:3]));
 end endgenerate
endmodule
`default_nettype wire
