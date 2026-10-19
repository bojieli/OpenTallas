`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SFU core k9 (H-SU 2026-10-17, coordinator 0co: square-ish ~1,600 x 1,800 cluster, owner rule "no long-thin blocks").
// Port re-slicing of ot_hgi_sfu_core_split2 (no logic of its own; DRAIN_PIPE below adds split2's drain stage): the sixteen lane-direct buses are
// split into four face groups so each group of four lane leaves (hard child ot_su12_sfu) faces its own block side:
//   _w = lanes 0-3 (W column)   _n = lanes 4-7 (N row)   _e = lanes 8-11 (E column)   _s = lanes 12-15 (S row).
// split2's X_w[k*W +: W] (lane k, k=0..7) -> lanes 0-3 on _w, 4-7 on _n; X_e (lanes 8..15) -> 8-11 on _e, 12-15 on _s.
// Every other port is split2's unchanged (local_* / io_word / compiler_control / clocks / resets / fault).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sfu_core_split3 #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0,
 // DRAIN_PIPE=1 (SFU-K9 10-18, k9 default): split2's VM bridge registers the drain interface once on clk, cutting the
 // 772 ps / 19-level operand-store output -> BF16 round -> write_q stage (textbook REFUSE). Static-schedule effect: every
 // drain sector reaches local_wq 1 edge later and its local_w_done is expected 1 edge later; drained sectors (VM output
 // region) are not read back inside the programme, so the compiler calendar is unchanged.
 parameter integer DRAIN_PIPE=1,
 // HBM-SAFE-K9 (10-19, coordinator 0ks, safe-design checklist items 4 + 7; k9 default 1):
 //  WPIPE=1: the operand store registers every bank-write input once (VM stage meta/data + lane element writes) before
 //   the groups' write select: cuts VM meta -> bank w_mask_in (~702 ps / 19 lv) and lane -> u_output wcoll_q (~717 ps).
 //   Static-schedule effect: every operand-store bank write lands 1 edge later (SFU calendar write-landing +1, priced
 //   in results/rtl/hbm_safe_k9_1019/schedule.md); the canonical lockstep shows no boundary edge moves.
 //  GCLK=1: the five store groups (4 operand + output, 16 SRAMs each, one floorplan column each) run on their own
 //   regional roots clk_st[4:0] (same die clock, neighbour-matched entries like clk_lane / clk_map); clk keeps the
 //   bridge + engine control. Crossings are flop-to-flop and judged per child pair (TT/FF spread <= 80 ps).
 parameter integer WPIPE=1,
 parameter integer GCLK=1
)(
 input wire clk,clk_pw,clk_pe,rst_n,
 input wire [4:0] clk_st,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
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
 wire [7:0] a_vi_re_w,a_vi_re_e,a_ro_v_w,a_ro_v_e,a_kv_we_w,a_kv_we_e;
 wire [191:0] a_vi_addr_w,a_vi_addr_e,a_kv_waddr_w,a_kv_waddr_e;
 wire [255:0] a_ro_x_w,a_ro_x_e,a_kv_wdata_w,a_kv_wdata_e;
 ot_hgi_sfu_core_split2 #(.LWB(LWB),.LG_PATH(LG_PATH),.DRAIN_PIPE(DRAIN_PIPE),.WPIPE(WPIPE),.GCLK(GCLK)) u_core(
  .clk(clk),.clk_pw(clk_pw),.clk_pe(clk_pe),.rst_n(rst_n),.clk_st(clk_st),.clk_lg(clk_lg),.rst_lg_n(rst_lg_n),
  .clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
  .io_word(io_word),.compiler_control(compiler_control),
  .local_rq(local_rq),.local_rr(local_rr),.local_wq(local_wq),.local_w_done(local_w_done),
  .vi_re_w(a_vi_re_w),.vi_re_e(a_vi_re_e),.vi_addr_w(a_vi_addr_w),.vi_addr_e(a_vi_addr_e),
  .vi_q_w({vi_q_n,vi_q_w}),.vi_q_e({vi_q_s,vi_q_e}),
  .ro_v_w(a_ro_v_w),.ro_v_e(a_ro_v_e),.kv_we_w(a_kv_we_w),.kv_we_e(a_kv_we_e),
  .ro_x_w(a_ro_x_w),.ro_x_e(a_ro_x_e),.kv_wdata_w(a_kv_wdata_w),.kv_wdata_e(a_kv_wdata_e),
  .kv_waddr_w(a_kv_waddr_w),.kv_waddr_e(a_kv_waddr_e),.fault(fault));
 assign {vi_re_n,vi_re_w}=a_vi_re_w;          assign {vi_re_s,vi_re_e}=a_vi_re_e;
 assign {vi_addr_n,vi_addr_w}=a_vi_addr_w;    assign {vi_addr_s,vi_addr_e}=a_vi_addr_e;
 assign {ro_v_n,ro_v_w}=a_ro_v_w;             assign {ro_v_s,ro_v_e}=a_ro_v_e;
 assign {kv_we_n,kv_we_w}=a_kv_we_w;          assign {kv_we_s,kv_we_e}=a_kv_we_e;
 assign {ro_x_n,ro_x_w}=a_ro_x_w;             assign {ro_x_s,ro_x_e}=a_ro_x_e;
 assign {kv_wdata_n,kv_wdata_w}=a_kv_wdata_w; assign {kv_wdata_s,kv_wdata_e}=a_kv_wdata_e;
 assign {kv_waddr_n,kv_waddr_w}=a_kv_waddr_w; assign {kv_waddr_s,kv_waddr_e}=a_kv_waddr_e;
endmodule
`default_nettype wire
