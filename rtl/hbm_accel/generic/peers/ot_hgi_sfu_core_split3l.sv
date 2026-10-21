`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SFU core k9z (HBM-COLLECT10/SFUC 2026-10-21): per-lane scalar clock / reset entries for ot_hgi_sfu_core_split3.
// Pure port wrapper, no logic: split3's 16-bit lane entry buses clk_lane / clk_map / rst_lane_n / rst_map_n become 64
// scalar ports <bus>_<lane>, so the kit can put each lane's entries on the die face point nearest that lane's hard child
// (ot_su12_sfu) clk pin. Cause (k9y route hbm_sfucore_k9y-y1-d285e0902, PREROUTE -18.5 ns): the bus ports were spread in
// index order over the W face while the 16 lane children ring all four faces, so clk_lane[i] was an unbuffered direct
// clock-entry wire from the W face to lane i's clk pin (ot_ce_require_wire: hard-child entries are not CTS roots) up to
// ~3.1 mm long: clk_lane[15] 558 fF, 54.7 ns slew, 17.26 ns arrival at g_lane[15].u_sfu/clk. Every worst path launched
// from a late lane child; it was not a logic cone. Same edges, same widths; only the port spelling of the lane entries.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sfu_core_split3l #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0,
 parameter integer TAP_RR=14,
 parameter integer TAP_WR=11,
 parameter integer DRAIN_PIPE=1,
 parameter integer WPIPE=1,
 parameter integer GCLK=1,
 parameter integer WROT=1, NATIVE32=0,
 parameter integer PASS_OHREP=16,
 parameter integer RST_TREE=1,
 parameter integer BTREE=0,
 parameter integer BRING=0
)(
 input wire clk,clk_pw,clk_pe,rst_n,
 input wire [4:0] clk_st,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire clk_lane_0,clk_lane_1,clk_lane_2,clk_lane_3,clk_lane_4,clk_lane_5,clk_lane_6,clk_lane_7,clk_lane_8,clk_lane_9,clk_lane_10,clk_lane_11,clk_lane_12,clk_lane_13,clk_lane_14,clk_lane_15,
 input wire clk_map_0,clk_map_1,clk_map_2,clk_map_3,clk_map_4,clk_map_5,clk_map_6,clk_map_7,clk_map_8,clk_map_9,clk_map_10,clk_map_11,clk_map_12,clk_map_13,clk_map_14,clk_map_15,
 input wire rst_lane_n_0,rst_lane_n_1,rst_lane_n_2,rst_lane_n_3,rst_lane_n_4,rst_lane_n_5,rst_lane_n_6,rst_lane_n_7,rst_lane_n_8,rst_lane_n_9,rst_lane_n_10,rst_lane_n_11,rst_lane_n_12,rst_lane_n_13,rst_lane_n_14,rst_lane_n_15,
 input wire rst_map_n_0,rst_map_n_1,rst_map_n_2,rst_map_n_3,rst_map_n_4,rst_map_n_5,rst_map_n_6,rst_map_n_7,rst_map_n_8,rst_map_n_9,rst_map_n_10,rst_map_n_11,rst_map_n_12,rst_map_n_13,rst_map_n_14,rst_map_n_15,
 input wire [470:0] io_word,
 input wire [1741:0] compiler_control,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [3:0] vi_re_w,vi_re_n,vi_re_e,vi_re_s,
 output wire [95:0] vi_addr_w,vi_addr_n,vi_addr_e,vi_addr_s,
 input wire [127:0] vi_q_w,vi_q_n,vi_q_e,vi_q_s,
 output wire [3:0] ro_v_w,ro_v_n,ro_v_e,ro_v_s,
 output wire [3:0] kv_we_w,kv_we_n,kv_we_e,kv_we_s,
 output wire [127:0] ro_x_w,ro_x_n,ro_x_e,ro_x_s,
 output wire [127:0] kv_wdata_w,kv_wdata_n,kv_wdata_e,kv_wdata_s,
 output wire [95:0] kv_waddr_w,kv_waddr_n,kv_waddr_e,kv_waddr_s,
 output wire fault
);
 ot_hgi_sfu_core_split3 #(.LWB(LWB),.LG_PATH(LG_PATH),.TAP_RR(TAP_RR),.TAP_WR(TAP_WR),.DRAIN_PIPE(DRAIN_PIPE),.WPIPE(WPIPE),.GCLK(GCLK),.WROT(WROT),.NATIVE32(NATIVE32),.PASS_OHREP(PASS_OHREP),.RST_TREE(RST_TREE),.BTREE(BTREE),.BRING(BRING)) u_s3(
  .clk(clk),.clk_pw(clk_pw),.clk_pe(clk_pe),.rst_n(rst_n),.clk_st(clk_st),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),
  .clk_lane({clk_lane_15,clk_lane_14,clk_lane_13,clk_lane_12,clk_lane_11,clk_lane_10,clk_lane_9,clk_lane_8,clk_lane_7,clk_lane_6,clk_lane_5,clk_lane_4,clk_lane_3,clk_lane_2,clk_lane_1,clk_lane_0}),
  .clk_map({clk_map_15,clk_map_14,clk_map_13,clk_map_12,clk_map_11,clk_map_10,clk_map_9,clk_map_8,clk_map_7,clk_map_6,clk_map_5,clk_map_4,clk_map_3,clk_map_2,clk_map_1,clk_map_0}),
  .rst_lane_n({rst_lane_n_15,rst_lane_n_14,rst_lane_n_13,rst_lane_n_12,rst_lane_n_11,rst_lane_n_10,rst_lane_n_9,rst_lane_n_8,rst_lane_n_7,rst_lane_n_6,rst_lane_n_5,rst_lane_n_4,rst_lane_n_3,rst_lane_n_2,rst_lane_n_1,rst_lane_n_0}),
  .rst_map_n({rst_map_n_15,rst_map_n_14,rst_map_n_13,rst_map_n_12,rst_map_n_11,rst_map_n_10,rst_map_n_9,rst_map_n_8,rst_map_n_7,rst_map_n_6,rst_map_n_5,rst_map_n_4,rst_map_n_3,rst_map_n_2,rst_map_n_1,rst_map_n_0}),
  .io_word(io_word),.compiler_control(compiler_control),
  .local_rq(local_rq),.local_rr(local_rr),.local_wq(local_wq),.local_w_done(local_w_done),
  .vi_re_w(vi_re_w),.vi_re_n(vi_re_n),.vi_re_e(vi_re_e),.vi_re_s(vi_re_s),
  .vi_addr_w(vi_addr_w),.vi_addr_n(vi_addr_n),.vi_addr_e(vi_addr_e),.vi_addr_s(vi_addr_s),
  .vi_q_w(vi_q_w),.vi_q_n(vi_q_n),.vi_q_e(vi_q_e),.vi_q_s(vi_q_s),
  .ro_v_w(ro_v_w),.ro_v_n(ro_v_n),.ro_v_e(ro_v_e),.ro_v_s(ro_v_s),
  .kv_we_w(kv_we_w),.kv_we_n(kv_we_n),.kv_we_e(kv_we_e),.kv_we_s(kv_we_s),
  .ro_x_w(ro_x_w),.ro_x_n(ro_x_n),.ro_x_e(ro_x_e),.ro_x_s(ro_x_s),
  .kv_wdata_w(kv_wdata_w),.kv_wdata_n(kv_wdata_n),.kv_wdata_e(kv_wdata_e),.kv_wdata_s(kv_wdata_s),
  .kv_waddr_w(kv_waddr_w),.kv_waddr_n(kv_waddr_n),.kv_waddr_e(kv_waddr_e),.kv_waddr_s(kv_waddr_s),.fault(fault));
endmodule
`default_nettype wire
