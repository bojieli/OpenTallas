`timescale 1ns/1ps
// TOPK w8 cluster HUB TILE (rt_j, Claude group-B4 2026-10-14).
//
// Why: rt_a..rt_i hardened the 16 lane / heap children but left the engine glue (ot_hgi_idx_topk_wreg HUB=1 LANE=1:
// command / score / result boundary, front end, status AND tree, max-root tournament, merge credit FIFOs, merge tree,
// result skid; ~12k flops) as cluster glue.  The placer smeared it over the 1,292 x 1,248 um outline, so every
// hub-internal net became a long wire (rt_i gate re-timed: u_hub.out_valid -> u_bo.i_r -233 ps, rz -> rem -120 ps,
// k -> lt_k -61 ps).  The hub is now its OWN hardened tile, placed in the centre channel between the lane rows, and every
// hub <-> cluster-boundary link is register -> wire -> register:
//   * command: valid / ready with a REGISTERED ready (cmd_ready = !h_v, as in the wreg);
//   * scores: CREDIT link from the W-face FIFO (u_bi): a beat arrives with in_v (no ready), lands in a pin register and
//     an NCI-deep landing FIFO; one registered credit pulse (in_cr) per beat taken by the engine;
//   * results: CREDIT link to the E-face FIFO (u_bo): out_v / out_d are registered; one credit (out_cr) comes back per
//     beat the E-face FIFO delivers; done follows the last delivered beat (all NCO credits home).
// j2 (Claude group-B6 2026-10-14, native pin audit of CLOSED j1: capture 473.5 ps on cmd_valid, cmd_* 267-310,
// lt_mv 446 / lt_md 225, rst_n 402): every input now lands in a pin register first -- command = pin registers + a
// 2-entry landing skid (registered cmd_ready only when the skid is empty and the previous cycle was not ready, so the
// one transfer the pin stage can still hide always has a slot); merge leaf mv / md / me = pin registers (inside the
// engine's LANE block); rst_n drives only ot_rst_relay copies.  Command acceptance +1 edge, merge credit round trip
// 5 -> 6 edges with the lane tile's 6 credits (still full rate, landing FIFO depth 6 still bounds every item).
// The engine (ot_hgi_idx_topk_hw HUB=1 LANE=1) and the lane interface are unchanged; this module is the wreg boundary of
// ot_hgi_idx_topk_heap.sv with the two credit links in place of the out_ready / in_ready handshakes.
module ot_hgi_topk_hub_tile #(
 parameter integer NCI = 6,                  // score credits = landing FIFO depth (link round trip <= 5)
 parameter integer NCO = 7,                  // result credits (<= the E-face FIFO entries, 8)
 parameter integer MUT_BYP = 0
)(
 input wire clk, rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n, cmd_m,
 input wire cmd_values,
 input wire in_v, input wire [259:0] in_d, output reg in_cr,          // in_d = {score[255:0], nw[3:0]}
 output reg out_v, output reg [97:0] out_d, input wire out_cr,         // out_d = {id, score, row, last, values_valid}
 output reg done, output reg [3:0] error,
 // lane links, split by the face that meets them: _a = lanes 0-3 (S face: the lower lane row), _b = lanes 4-7 (N face)
 output wire [11:0] lt_ph_a, lt_ph_b, output wire [47:0] lt_k_a, lt_k_b, output wire [3:0] lt_clr_a, lt_clr_b,
 output wire [3:0] lt_pv_a, lt_pv_b, lt_mcr_a, lt_mcr_b, output wire [215:0] lt_pd_a, lt_pd_b,
 input wire [3:0] lt_q_a, lt_q_b, lt_x_a, lt_x_b, lt_ok_a, lt_ok_b, lt_mv_a, lt_mv_b, lt_me_a, lt_me_b,
 input wire [211:0] lt_root_a, lt_root_b, input wire [215:0] lt_md_a, lt_md_b
);
 wire [23:0] lt_ph; wire [95:0] lt_k; wire [7:0] lt_clr, lt_pv, lt_mcr; wire [431:0] lt_pd;
 assign {lt_ph_b, lt_ph_a} = lt_ph; assign {lt_k_b, lt_k_a} = lt_k; assign {lt_clr_b, lt_clr_a} = lt_clr;
 assign {lt_pv_b, lt_pv_a} = lt_pv; assign {lt_mcr_b, lt_mcr_a} = lt_mcr; assign {lt_pd_b, lt_pd_a} = lt_pd;
 wire [7:0] lt_q = {lt_q_b, lt_q_a}, lt_x = {lt_x_b, lt_x_a}, lt_ok = {lt_ok_b, lt_ok_a}, lt_mv = {lt_mv_b, lt_mv_a},
            lt_me = {lt_me_b, lt_me_a};
 wire [423:0] lt_root = {lt_root_b, lt_root_a}; wire [431:0] lt_md = {lt_md_b, lt_md_a};
 localparam integer IW = 8, W = 8, MAX_K = 2048;
 localparam integer CIW = $clog2(NCI + 1), COW = $clog2(NCO + 1), QA = $clog2(NCI);
 reg active,c_valid,s_valid,q_valid,pending_done,o_rdy;
 // ---------------------------------------------------------------- reset relay + command pin landing
 // j3 (native audit of CLOSED j2: capture 208.6 ps on rst_n = the port fed two relays): the engine's relay is the
 // ONLY port load; the hub registers take its two exported regions (same release edge as the engine and the lanes).
 wire [1:0] hr;
 localparam integer CDW = 4 + 6 + 25 + 32 + 32 + 1;
 reg cv_q, rdy_q, cmd_rdy; reg [CDW-1:0] cd_q;                       // pin registers
 reg [CDW-1:0] cs [0:1]; reg cs_w, cs_r; reg [1:0] cs_n;             // landing skid
 wire acc = cv_q && rdy_q;
 wire h_v = cs_n != 2'd0;
 wire [CDW-1:0] csh = cs[cs_r];
 reg [3:0] c_unit; reg [5:0] c_op; reg [24:0] c_param; reg [31:0] c_n,c_m; reg c_values;
 reg [IW*32-1:0] s_score; reg [3:0] s_nw;
 reg [97:0] q_r; reg [97:0] b_r [0:3]; reg [1:0] bw, br; reg [2:0] bn;
 wire core_cmd_ready,core_in_ready,core_out_valid,core_done; wire [3:0] core_error;
 wire [31:0] core_id,core_score,core_row; wire core_last,core_values;
 // ---------------------------------------------------------------- score landing (credit link)
 reg iv_q; reg [259:0] id_q;                                         // pin registers
 reg [259:0] ilq [0:NCI-1]; reg [QA-1:0] ilw, ilr; reg [CIW-1:0] iln;
 wire il_ne = iln != 0;
 wire in_ready_i = active && (!s_valid || core_in_ready);
 wire take = in_ready_i && il_ne;
 wire [259:0] ilh = ilq[ilr];
 // ---------------------------------------------------------------- result skid + credit link
 reg [COW-1:0] ocr; reg ocr_q;
 wire core_out_ready = o_rdy;
 wire [97:0] c_r = {core_values,core_last,core_row,core_score,core_id};
 wire push = core_out_valid && o_rdy, pop = q_valid && ocr != 0, q_load = !q_valid || pop;
 wire from_b = q_load && bn != 3'd0, direct = q_load && bn == 3'd0 && push, to_b = push && !direct;
 wire [2:0] bn_nx = bn + to_b - from_b;
 wire q_nx = q_load ? (bn != 3'd0 || push) : 1'b1;
 assign cmd_ready = cmd_rdy;
 wire go = h_v && !active && !c_valid && core_cmd_ready && !pending_done && !q_valid && bn == 3'd0;
 reg h_done; reg [3:0] h_err; reg done_p;
 wire drained = !q_valid && !out_v && ocr == COW'(NCO);
 ot_hgi_idx_topk_hw #(.ENABLE(1'b1),.MAX_K(MAX_K),.IW(IW),.W(W),.MUT_BYP(MUT_BYP),.HUB(1'b1),.LANE(1'b1)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),.in_nw(s_nw),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error),
  .t_k(),.t_op_v(),.t_op_ext(),.t_clr_go(),.t_op_x(),.t_op_cr(8'd0),.t_ext_v(8'd0),
  .t_idle_i(8'd0),.t_ext_d(432'd0),.t_root_key(424'd0),
  .lt_ph(lt_ph),.lt_k(lt_k),.lt_clr(lt_clr),.lt_pv(lt_pv),.lt_mcr(lt_mcr),.lt_pd(lt_pd),.lt_q(lt_q),.lt_x(lt_x),.lt_ok(lt_ok),
  .lt_mv(lt_mv),.lt_me(lt_me),.lt_root(lt_root),.lt_md(lt_md),.rr_x(hr));
 always @(posedge clk) begin
  cd_q <= {cmd_unit, cmd_op, cmd_param, cmd_n, cmd_m, cmd_values};
  if (acc) cs[cs_w] <= cd_q;
  if (go) {c_unit, c_op, c_param, c_n, c_m, c_values} <= csh;
  id_q <= in_d;
  if (iv_q) ilq[ilw] <= id_q;
  if (take) {s_score, s_nw} <= ilh;
  if(to_b)b_r[bw]<=c_r;
  if(from_b)q_r<=b_r[br]; else if(direct)q_r<=c_r;
  out_d <= {q_r[31:0], q_r[63:32], q_r[95:64], q_r[96], q_r[97]};
 end
 wire [1:0] cs_n_nx = cs_n + 2'(acc) - 2'(go);
 always @(posedge clk or negedge hr[1])
  if (!hr[1]) begin cv_q <= 1'b0; rdy_q <= 1'b0; cmd_rdy <= 1'b0; cs_w <= 1'b0; cs_r <= 1'b0; cs_n <= 2'd0; end
  else begin
   cv_q <= cmd_valid; rdy_q <= cmd_rdy;
   if (acc) cs_w <= !cs_w;
   if (go) cs_r <= !cs_r;
   cs_n <= cs_n_nx;
   cmd_rdy <= cs_n_nx == 2'd0 && !cmd_rdy;                           // at most one transfer the pin stage hides
  end
 always @(posedge clk or negedge hr[0])begin
  if(!hr[0])begin
   active<=0;c_valid<=0;s_valid<=0;q_valid<=0;pending_done<=0;h_done<=0;h_err<=0;o_rdy<=0;bw<=0;br<=0;bn<=0;
   iv_q<=1'b0; ilw<=0; ilr<=0; iln<=0; in_cr<=1'b0; ocr<=COW'(NCO); ocr_q<=1'b0; out_v<=1'b0;
   done<=1'b0; done_p<=1'b0; error<=4'd0;
  end else begin
   h_done<=0;
   iv_q <= in_v; in_cr <= take; ocr_q <= out_cr; out_v <= pop;
   if (iv_q) ilw <= (ilw == QA'(NCI-1)) ? QA'(0) : ilw + 1'b1;
   if (take) ilr <= (ilr == QA'(NCI-1)) ? QA'(0) : ilr + 1'b1;
   iln <= iln + CIW'(iv_q) - CIW'(take);
   ocr <= ocr - COW'(pop) + COW'(ocr_q);
   if(c_valid&&core_cmd_ready)c_valid<=0;
   if(go)begin active<=1;c_valid<=1;h_err<=0;end
   if(in_ready_i)s_valid<=il_ne;
   q_valid<=q_nx; bn<=bn_nx; if(to_b)bw<=bw+1'b1; if(from_b)br<=br+1'b1;
   o_rdy<=({2'b00,q_valid}+bn+{2'b00,push})<=3'd2;
   if(core_done)begin pending_done<=1;h_err<=core_error;end
   if((pending_done||core_done)&&bn==3'd0&&(!q_valid||pop))begin h_done<=1;active<=0;pending_done<=0;c_valid<=0;s_valid<=0;end
   // done follows the last DELIVERED beat: every result credit home (the E-face FIFO is empty) after the engine's pulse
   error <= h_err;
   done <= done_p && drained;
   if (h_done) done_p <= 1'b1; else if (done_p && drained) done_p <= 1'b0;
  end
 end
 initial if (NCI < 2 || NCO < 1) $fatal(1, "ot_hgi_topk_hub_tile: NCI >= 2, NCO >= 1");
`ifndef SYNTHESIS
 always @(posedge clk) if (hr[0] && iv_q && iln == CIW'(NCI) && !take) $fatal(1, "TOPK hub: score landing FIFO overflow (credit protocol broken)");
 always @(posedge clk) if (hr[1] && acc && cs_n == 2'd2 && !go) $fatal(1, "TOPK hub: command skid overflow");
`endif
endmodule
