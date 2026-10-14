`timescale 1ns/1ps
// Literal six-master NO3 production composition; same complete frame ABI.
// fclk_observe has no internal receiver or functional capture. All six masters
// take the literal clk_sm root, preserving original make_sdc.py observation ABI.
module ot_hbm_native_no3_composition_1014 #(parameter integer MUT=0)(
 input wire clk_sm,por_n,release_held,in_v,output wire in_r,
 input wire [2062:0] in_data,input wire [191:0] in_owner,input wire[72:0] in_frame,
 output wire[2:0] out_v,input wire[2:0] out_r,
 output wire[6188:0] out_data,output wire[575:0] out_owner,output wire[218:0] out_frame,
 input wire[2:0] ACK_v,input wire[575:0] ACK_owner,input wire[218:0] ACK_frame,
 output wire release_v,input wire release_r,output wire[191:0] release_owner,output wire[72:0] release_frame,
 output wire fclk_observe,drained,paused,fault
);
 wire[2327:0] pin_data={in_owner,in_frame,in_data};
 wire[6983:0] payload_out;
 wire[191:0] hub_release_owner;
 assign release_owner=hub_release_owner ^ (MUT==1 ? 192'd1 : 192'd0);
 wire sl0_go_check,sl0_go_commit,sl0_go_repair,sl0_go_sel,sl0_gr,sl0_rst_e,sl0_rst_p;
 wire[3:0] sl0_ph4;
 wire sl0_v_same,sl0_v_bad,sl0_v_cbad,sl0_v_ce,sl0_v_ue,sl0_v_clean;
 wire[7:0] sl0_grc_o;
 wire sl1_go_check,sl1_go_commit,sl1_go_repair,sl1_go_sel,sl1_gr,sl1_rst_e,sl1_rst_p;
 wire[3:0] sl1_ph4;
 wire sl1_v_same,sl1_v_bad,sl1_v_cbad,sl1_v_ce,sl1_v_ue,sl1_v_clean;
 wire[7:0] sl1_grc_o;
 wire sl2_go_check,sl2_go_commit,sl2_go_repair,sl2_go_sel,sl2_gr,sl2_rst_e,sl2_rst_p;
 wire[3:0] sl2_ph4;
 wire sl2_v_same,sl2_v_bad,sl2_v_cbad,sl2_v_ce,sl2_v_ue,sl2_v_clean;
 wire[7:0] sl2_grc_o;
 wire sl3_go_check,sl3_go_commit,sl3_go_repair,sl3_go_sel,sl3_gr,sl3_rst_e,sl3_rst_p;
 wire[3:0] sl3_ph4;
 wire sl3_v_same,sl3_v_bad,sl3_v_cbad,sl3_v_ce,sl3_v_ue,sl3_v_clean;
 wire[7:0] sl3_grc_o;
 wire sl4_go_check,sl4_go_commit,sl4_go_repair,sl4_go_sel,sl4_gr,sl4_rst_e,sl4_rst_p;
 wire[3:0] sl4_ph4;
 wire sl4_v_same,sl4_v_bad,sl4_v_cbad,sl4_v_ce,sl4_v_ue,sl4_v_clean;
 wire[4:0] sl4_grc_o;
 wire[319:0] sl4_q;
 ot_hbm_native_no3_hub_observe_1014 u_hub(
  .clk_sm(clk_sm),
  .por_n(por_n),
  .release_held(release_held),
  .in_v(in_v),
  .in_r(in_r),
  .out_v(out_v),
  .out_r(out_r),
  .ACK_v(ACK_v),
  .ACK_owner(ACK_owner),
  .ACK_frame(ACK_frame),
  .release_v(release_v),
  .release_r(release_r),
  .release_frame(release_frame),
  .drained(drained),
  .paused(paused),
  .fault(fault),
  .release_owner(hub_release_owner),
  .fclk_observe(fclk_observe),
  .sl0_go_check(sl0_go_check),
  .sl0_go_commit(sl0_go_commit),
  .sl0_go_repair(sl0_go_repair),
  .sl0_go_sel(sl0_go_sel),
  .sl0_gr(sl0_gr),
  .sl0_rst_e(sl0_rst_e),
  .sl0_rst_p(sl0_rst_p),
  .sl0_ph4(sl0_ph4),
  .sl0_v_same(sl0_v_same),
  .sl0_v_bad(sl0_v_bad),
  .sl0_v_cbad(sl0_v_cbad),
  .sl0_v_ce(sl0_v_ce),
  .sl0_v_ue(sl0_v_ue),
  .sl0_v_clean(sl0_v_clean),
  .sl0_grc_o(sl0_grc_o),
  .sl1_go_check(sl1_go_check),
  .sl1_go_commit(sl1_go_commit),
  .sl1_go_repair(sl1_go_repair),
  .sl1_go_sel(sl1_go_sel),
  .sl1_gr(sl1_gr),
  .sl1_rst_e(sl1_rst_e),
  .sl1_rst_p(sl1_rst_p),
  .sl1_ph4(sl1_ph4),
  .sl1_v_same(sl1_v_same),
  .sl1_v_bad(sl1_v_bad),
  .sl1_v_cbad(sl1_v_cbad),
  .sl1_v_ce(sl1_v_ce),
  .sl1_v_ue(sl1_v_ue),
  .sl1_v_clean(sl1_v_clean),
  .sl1_grc_o(sl1_grc_o),
  .sl2_go_check(sl2_go_check),
  .sl2_go_commit(sl2_go_commit),
  .sl2_go_repair(sl2_go_repair),
  .sl2_go_sel(sl2_go_sel),
  .sl2_gr(sl2_gr),
  .sl2_rst_e(sl2_rst_e),
  .sl2_rst_p(sl2_rst_p),
  .sl2_ph4(sl2_ph4),
  .sl2_v_same(sl2_v_same),
  .sl2_v_bad(sl2_v_bad),
  .sl2_v_cbad(sl2_v_cbad),
  .sl2_v_ce(sl2_v_ce),
  .sl2_v_ue(sl2_v_ue),
  .sl2_v_clean(sl2_v_clean),
  .sl2_grc_o(sl2_grc_o),
  .sl3_go_check(sl3_go_check),
  .sl3_go_commit(sl3_go_commit),
  .sl3_go_repair(sl3_go_repair),
  .sl3_go_sel(sl3_go_sel),
  .sl3_gr(sl3_gr),
  .sl3_rst_e(sl3_rst_e),
  .sl3_rst_p(sl3_rst_p),
  .sl3_ph4(sl3_ph4),
  .sl3_v_same(sl3_v_same),
  .sl3_v_bad(sl3_v_bad),
  .sl3_v_cbad(sl3_v_cbad),
  .sl3_v_ce(sl3_v_ce),
  .sl3_v_ue(sl3_v_ue),
  .sl3_v_clean(sl3_v_clean),
  .sl3_grc_o(sl3_grc_o),
  .sl4_go_check(sl4_go_check),
  .sl4_go_commit(sl4_go_commit),
  .sl4_go_repair(sl4_go_repair),
  .sl4_go_sel(sl4_go_sel),
  .sl4_gr(sl4_gr),
  .sl4_rst_e(sl4_rst_e),
  .sl4_rst_p(sl4_rst_p),
  .sl4_ph4(sl4_ph4),
  .sl4_v_same(sl4_v_same),
  .sl4_v_bad(sl4_v_bad),
  .sl4_v_cbad(sl4_v_cbad),
  .sl4_v_ce(sl4_v_ce),
  .sl4_v_ue(sl4_v_ue),
  .sl4_v_clean(sl4_v_clean),
  .sl4_grc_o(sl4_grc_o),
  .sl4_q(sl4_q)
 );
 wire[1535:0] sl0_dout;
`ifdef OT_NO3_HARD_CHILDREN
 ot_hbm_w2_stn_slice8 u_slice0(
`else
 ot_hbm_w2_stn_slice8 #(.NO(3)) u_slice0(
`endif
  .clk(MUT==2 ? fclk_observe : clk_sm),.rst_p(sl0_rst_p),.rst_e(sl0_rst_e),.gr(sl0_gr),
  .go_check(sl0_go_check),.go_commit(sl0_go_commit),.go_repair(sl0_go_repair),.go_sel(sl0_go_sel),.ph4(sl0_ph4),
  .din(pin_data[0+:512]),.dout(sl0_dout),
  .v_same(sl0_v_same),.v_bad(sl0_v_bad),.v_cbad(sl0_v_cbad),.v_ce(sl0_v_ce),.v_ue(sl0_v_ue),.v_clean(sl0_v_clean),.grc_o(sl0_grc_o));
 assign payload_out[0+:512]=sl0_dout[0+:512];
 assign payload_out[2328+:512]=sl0_dout[512+:512];
 assign payload_out[4656+:512]=sl0_dout[1024+:512];
 wire[1535:0] sl1_dout;
`ifdef OT_NO3_HARD_CHILDREN
 ot_hbm_w2_stn_slice8 u_slice1(
`else
 ot_hbm_w2_stn_slice8 #(.NO(3)) u_slice1(
`endif
  .clk(clk_sm),.rst_p(sl1_rst_p),.rst_e(sl1_rst_e),.gr(sl1_gr),
  .go_check(sl1_go_check),.go_commit(sl1_go_commit),.go_repair(sl1_go_repair),.go_sel(sl1_go_sel),.ph4(sl1_ph4),
  .din(pin_data[512+:512]),.dout(sl1_dout),
  .v_same(sl1_v_same),.v_bad(sl1_v_bad),.v_cbad(sl1_v_cbad),.v_ce(sl1_v_ce),.v_ue(sl1_v_ue),.v_clean(sl1_v_clean),.grc_o(sl1_grc_o));
 assign payload_out[512+:512]=sl1_dout[0+:512];
 assign payload_out[2840+:512]=sl1_dout[512+:512];
 assign payload_out[5168+:512]=sl1_dout[1024+:512];
 wire[1535:0] sl2_dout;
`ifdef OT_NO3_HARD_CHILDREN
 ot_hbm_w2_stn_slice8 u_slice2(
`else
 ot_hbm_w2_stn_slice8 #(.NO(3)) u_slice2(
`endif
  .clk(clk_sm),.rst_p(sl2_rst_p),.rst_e(sl2_rst_e),.gr(sl2_gr),
  .go_check(sl2_go_check),.go_commit(sl2_go_commit),.go_repair(sl2_go_repair),.go_sel(sl2_go_sel),.ph4(sl2_ph4),
  .din(pin_data[1024+:512]),.dout(sl2_dout),
  .v_same(sl2_v_same),.v_bad(sl2_v_bad),.v_cbad(sl2_v_cbad),.v_ce(sl2_v_ce),.v_ue(sl2_v_ue),.v_clean(sl2_v_clean),.grc_o(sl2_grc_o));
 assign payload_out[1024+:512]=sl2_dout[0+:512];
 assign payload_out[3352+:512]=sl2_dout[512+:512];
 assign payload_out[5680+:512]=sl2_dout[1024+:512];
 wire[1535:0] sl3_dout;
`ifdef OT_NO3_HARD_CHILDREN
 ot_hbm_w2_stn_slice8 u_slice3(
`else
 ot_hbm_w2_stn_slice8 #(.NO(3)) u_slice3(
`endif
  .clk(clk_sm),.rst_p(sl3_rst_p),.rst_e(sl3_rst_e),.gr(sl3_gr),
  .go_check(sl3_go_check),.go_commit(sl3_go_commit),.go_repair(sl3_go_repair),.go_sel(sl3_go_sel),.ph4(sl3_ph4),
  .din(pin_data[1536+:512]),.dout(sl3_dout),
  .v_same(sl3_v_same),.v_bad(sl3_v_bad),.v_cbad(sl3_v_cbad),.v_ce(sl3_v_ce),.v_ue(sl3_v_ue),.v_clean(sl3_v_clean),.grc_o(sl3_grc_o));
 assign payload_out[1536+:512]=sl3_dout[0+:512];
 assign payload_out[3864+:512]=sl3_dout[512+:512];
 assign payload_out[6192+:512]=sl3_dout[1024+:512];
 wire[839:0] sl4_dout;
`ifdef OT_NO3_HARD_CHILDREN
 ot_hbm_w2_stn_slice5 u_slice4(
`else
 ot_hbm_w2_stn_slice5 #(.NO(3)) u_slice4(
`endif
  .clk(clk_sm),.rst_p(sl4_rst_p),.rst_e(sl4_rst_e),.gr(sl4_gr),
  .go_check(sl4_go_check),.go_commit(sl4_go_commit),.go_repair(sl4_go_repair),.go_sel(sl4_go_sel),.ph4(sl4_ph4),
  .din(pin_data[2048+:280]),.dout(sl4_dout),
  .v_same(sl4_v_same),.v_bad(sl4_v_bad),.v_cbad(sl4_v_cbad),.v_ce(sl4_v_ce),.v_ue(sl4_v_ue),.v_clean(sl4_v_clean),.grc_o(sl4_grc_o),.q(sl4_q));
 assign payload_out[2048+:280]=sl4_dout[0+:280];
 assign payload_out[4376+:280]=sl4_dout[280+:280];
 assign payload_out[6704+:280]=sl4_dout[560+:280];
 assign out_data[0+:2063]=payload_out[0+:2063];
 assign out_frame[0+:73]=payload_out[2063+:73];
 assign out_owner[0+:192]=payload_out[2136+:192];
 assign out_data[2063+:2063]=payload_out[2328+:2063];
 assign out_frame[73+:73]=payload_out[4391+:73];
 assign out_owner[192+:192]=payload_out[4464+:192];
 assign out_data[4126+:2063]=payload_out[4656+:2063];
 assign out_frame[146+:73]=payload_out[6719+:73];
 assign out_owner[384+:192]=payload_out[6792+:192];
endmodule
