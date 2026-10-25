`timescale 1ns/1ps
`default_nettype none
// HC quarter HUB tile (HBM-B-RTL2, plan (b) d4g, 2026-10-17; coordinator decision 10-17 23:45: hc_<q> goes IN the hole
// of the quarter engine's 3x3 bank ring, no empty middle).  One die tile per quadrant (hce_<q>_hub, one master x4) =
//   ot_hbm_hc_q_static     the quadrant's static HC LG client (programme SRAM, residual / gathered / result VM traffic)
//   ot_hbm_hc_qcen_static  the quarter engine centre (control-only x_wave rx, ingest sequencer, descriptor relay,
//                          6-level partial-sum subtree, regional reset to the 8 bank tiles)
// The x_wave link hc_<q> -> engine is now inside the tile: hc_<q>'s 2,048-b beat output register drives the 8 bank
// beat slices (256 b each, + v/beat) and the centre's beat control directly (same edges as the separate tiles:
// hc_<q> output flop -> receiver pin flop).  Bank slices: W face bank 0; N face bank 2 + corners 1, 3 (fed through
// bank 2); E face bank 4; S face bank 6 + corners 5, 7.  Every other port is the two sub-blocks' own (registered) pin.
// W (HBM-HC 2026-10-24, default 64 = unchanged): 128 = the B2 8-SM die HALF hub (hc_NW / hc_NE under the NQ 2 root):
// centre ot_hbm_hc_qcen_static #(W 128) -- d_nv 8 b, i_w 6 b, wc_* 14 b, s_i 4,097 b -- over 8 W 128 bank tiles.  The
// hc_<q> LG client and the x-wave beat slices are unchanged (a wave is still 32 chunks x 8 terms).
module ot_hbm_hc_qhub_static #(
    parameter integer K = 20480,
    parameter integer DRLY = 1,
    parameter integer TLA = 7,
    parameter integer CHX = 0,       // HH-9 10-19: extra bank-chain edges (ot_hbm_hc_qcen_static CHX; 11 with the CPR ring)
    parameter integer RD_CAPTURE = 23,
    parameter integer GATHER_PHASE = 23,
    parameter integer DONE_LAT = 19,
    parameter integer W = 64,        // 64 (quarter hub) or 128 (B2 half hub)
    parameter integer MUT = 0,       // bench: passed to the centre (ot_hbm_hc_qcen_static MUT)
    // derived (do not override)
    parameter integer NVW = (W == 128) ? 8 : 7,
    parameter integer IWW = (W == 128) ? 6 : 5,
    parameter integer JW  = (W == 128) ? 2 : 1
)(
    input  wire           clk, rst_n,
    // ---- hc_<q> (ot_hbm_hc_q_static)
    input  wire [7:0]     tgt,
    input  wire           cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire           desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire           launch_v,
    output wire           configured,
    output wire [135:0]   lg_rq,
    output wire [2247:0]  lg_wq,
    input  wire [2055:0]  lg_rr,
    input  wire [7:0]     lg_w_done,
    output wire           residual_done,
    output wire           gathered_mix_v, output wire [4:0] gathered_mix_row, output wire [2:0] gathered_mix_pos,
    output wire [31:0]    gathered_mix_data,
    output wire           gather_done,
    input  wire           result_v, input wire [2:0] result_position, input wire [767:0] result,
    output wire           program_active, program_done,
    output wire           hcq_fault,
    // ---- quarter engine centre (from / to the root, ot_hbm_hc_root_static)
    input  wire           d_v, d_ss, input wire [NVW-1:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire           i_v, i_kind, input wire [1:0] i_slot, input wire [4:0] i_lo, input wire [IWW-1:0] i_w,
    input  wire [11:0]    i_cnt, input wire [9:0] i_word,
    output wire           ps_v, output wire [31:0] ps, output wire ps_f,
    output wire           eng_fault,
    // ---- to the bank ring
    output wire           rstb_w, rstb_e, output wire [2:0] rstb_n, rstb_s,   // bank 0 | 4 | 1,2,3 | 5,6,7 (corners via 2 / 6)
    output wire           bd_v, bd_ss, output wire [NVW-1:0] bd_nv, output wire [9:0] bd_wa, bd_xa, // bank 0 descriptor
    input  wire [W*32:0]  s_i,                                                                   // bank 0 chain exit
    input  wire           wf_w, wf_e, input wire [2:0] wf_n, wf_s,            // same order
    output wire [11+JW:0] wc_w, wc_n, wc_e, wc_s,
    output wire           xb_v, output wire [1:0] xb_beat,                                     // per face copies below
    output wire           xb_v_n, xb_v_e, xb_v_s, output wire [1:0] xb_beat_n, xb_beat_e, xb_beat_s,
    output wire [255:0]   xb_d0, xb_d1, xb_d2, xb_d3, xb_d4, xb_d5, xb_d6, xb_d7
);
    wire xv; wire [9:0] xw; wire [2047:0] xd; wire [1:0] xbt; wire [7:0] rb;
    assign rstb_w = rb[0]; assign rstb_n = rb[3:1]; assign rstb_e = rb[4]; assign rstb_s = rb[7:5];
    ot_hbm_hc_q_static #(.RD_CAPTURE(RD_CAPTURE), .GATHER_PHASE(GATHER_PHASE), .DONE_LAT(DONE_LAT), .XW_BEATS(4)) u_q (
        .clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .configured(configured), .lg_rq(lg_rq), .lg_wq(lg_wq), .lg_rr(lg_rr), .lg_w_done(lg_w_done),
        .x_wave_v(xv), .x_wave_word(xw), .x_wave(xd), .x_wave_beat(xbt), .residual_done(residual_done),
        .gathered_mix_v(gathered_mix_v), .gathered_mix_row(gathered_mix_row), .gathered_mix_pos(gathered_mix_pos),
        .gathered_mix_data(gathered_mix_data), .gather_done(gather_done), .result_v(result_v),
        .result_position(result_position), .result(result), .program_active(program_active),
        .program_done(program_done), .fault(hcq_fault));
    ot_hbm_hc_qcen_static #(.K(K), .DRLY(DRLY), .TLA(TLA), .CHX(CHX), .MUT(MUT), .W(W)) u_cen (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word),
        .x_v(xv), .x_beat(xbt), .x_word(xw), .s_i(s_i), .wfault_i({wf_s[2:0], wf_e, wf_n[2:0], wf_w}), .rst_b(rb),
        .bd_v(bd_v), .bd_ss(bd_ss), .bd_nv(bd_nv), .bd_wa(bd_wa), .bd_xa(bd_xa),
        .wc_w(wc_w), .wc_n(wc_n), .wc_e(wc_e), .wc_s(wc_s), .ps_v(ps_v), .ps(ps), .ps_f(ps_f), .fault(eng_fault));
    assign xb_v = xv; assign xb_v_n = xv; assign xb_v_e = xv; assign xb_v_s = xv;
    assign xb_beat = xbt; assign xb_beat_n = xbt; assign xb_beat_e = xbt; assign xb_beat_s = xbt;
    wire [8*256-1:0] xs;
    for (genvar k = 0; k < 8; k = k + 1) begin : g_xs
        for (genvar i = 0; i < 8; i = i + 1) begin : g_i
            assign xs[k*256 + i*32 +: 32] = xd[i*256 + k*32 +: 32];
        end
    end
    assign {xb_d7, xb_d6, xb_d5, xb_d4, xb_d3, xb_d2, xb_d1, xb_d0} = xs;
endmodule
`default_nettype wire
