`timescale 1ns/1ps
`default_nettype none
// HC quarter HUB tile (HBM-B-RTL2, plan (b) d4g, 2026-10-17; coordinator decision 10-17 23:45: hc_<q> goes IN the hole
// of the quarter engine's 3x3 bank ring, no empty middle).  One die tile per quadrant (hce_<q>_hub, one master x4) =
//   ot_hnx_hc_q     the quadrant's static HC LG client (programme SRAM, residual / gathered / result VM traffic)
//   ot_hnx_hc_qcen  the quarter engine centre (control-only x_wave rx, ingest sequencer, descriptor relay,
//                          6-level partial-sum subtree, regional reset to the 8 bank tiles)
// HUBFIX 10-19: the bank beat control (xb_v / xb_beat per face) leaves a per-face copy of hc_q's beat-control register.
// The x_wave link hc_<q> -> engine is now inside the tile: hc_<q>'s 2,048-b beat output register drives the 8 bank
// beat slices (256 b each, + v/beat) and the centre's beat control directly (same edges as the separate tiles:
// hc_<q> output flop -> receiver pin flop).  Bank slices: W face bank 0; N face bank 2 + corners 1, 3 (fed through
// bank 2); E face bank 4; S face bank 6 + corners 5, 7.  Every other port is the two sub-blocks' own (registered) pin.
module ot_hnx_hc_qhub #(
    parameter integer K = 20480,
    parameter integer DRLY = 1,
    parameter integer TLA = 7,
    parameter integer RD_CAPTURE = 23,
    parameter integer GATHER_PHASE = 23,
    parameter integer DONE_LAT = 19
)(
    input  wire           clk, rst_n,
    // ---- hc_<q> (ot_hnx_hc_q)
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
    // ---- quarter engine centre (from / to the root, ot_hnx_hc_root)
    input  wire           d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa,
    input  wire           i_v, i_kind, input wire [1:0] i_slot, input wire [4:0] i_lo, i_w,
    input  wire [11:0]    i_cnt, input wire [9:0] i_word,
    output wire           ps_v, output wire [31:0] ps, output wire ps_f,
    output wire           eng_fault,
    // ---- to the bank ring
    output wire           rstb_w, rstb_e, output wire [2:0] rstb_n, rstb_s,   // bank 0 | 4 | 1,2,3 | 5,6,7 (corners via 2 / 6)
    output wire           bd_v, bd_ss, output wire [6:0] bd_nv, output wire [9:0] bd_wa, bd_xa,   // bank 0 descriptor
    input  wire [2048:0]  s_i,                                                                   // bank 0 chain exit
    input  wire           wf_w, wf_e, input wire [2:0] wf_n, wf_s,            // same order
    output wire [12:0]    wc_w, wc_n, wc_e, wc_s,
    output wire           xb_v, output wire [1:0] xb_beat,                                     // per face copies below
    output wire           xb_v_n, xb_v_e, xb_v_s, output wire [1:0] xb_beat_n, xb_beat_e, xb_beat_s,
    output wire [255:0]   xb_d0, xb_d1, xb_d2, xb_d3, xb_d4, xb_d5, xb_d6, xb_d7
);
    wire xv; wire [9:0] xw; wire [2047:0] xd; wire [1:0] xbt; wire [7:0] rb;
    wire [3:0] xvf; wire [7:0] xbf;   // HUBFIX 10-19: per-face copies of the beat-control register (W, N, E, S)
    assign rstb_w = rb[0]; assign rstb_n = rb[3:1]; assign rstb_e = rb[4]; assign rstb_s = rb[7:5];
    ot_hnx_hc_q #(.RD_CAPTURE(RD_CAPTURE), .GATHER_PHASE(GATHER_PHASE), .DONE_LAT(DONE_LAT), .XW_BEATS(4), .XFC(1)) u_q (
        .clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .configured(configured), .lg_rq(lg_rq), .lg_wq(lg_wq), .lg_rr(lg_rr), .lg_w_done(lg_w_done),
        .x_wave_v(xv), .x_wave_word(xw), .x_wave(xd), .x_wave_beat(xbt), .x_wave_vf(xvf), .x_wave_beatf(xbf),
        .residual_done(residual_done),
        .gathered_mix_v(gathered_mix_v), .gathered_mix_row(gathered_mix_row), .gathered_mix_pos(gathered_mix_pos),
        .gathered_mix_data(gathered_mix_data), .gather_done(gather_done), .result_v(result_v),
        .result_position(result_position), .result(result), .program_active(program_active),
        .program_done(program_done), .fault(hcq_fault));
    ot_hnx_hc_qcen #(.K(K), .DRLY(DRLY), .TLA(TLA)) u_cen (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word),
        .x_v(xv), .x_beat(xbt), .x_word(xw), .s_i(s_i), .wfault_i({wf_s[2:0], wf_e, wf_n[2:0], wf_w}), .rst_b(rb),
        .bd_v(bd_v), .bd_ss(bd_ss), .bd_nv(bd_nv), .bd_wa(bd_wa), .bd_xa(bd_xa),
        .wc_w(wc_w), .wc_n(wc_n), .wc_e(wc_e), .wc_s(wc_s), .ps_v(ps_v), .ps(ps), .ps_f(ps_f), .fault(eng_fault));
    // HUBFIX 10-19 (closure job hnx_hcq_hub_1019-n1-c8a284b41 FLOORPLAN_MARGIN wire_reach): ONE beat-control register
    // fanned to four faces sat 530-608 um from a face pin.  Each face now has its own copy (ot_hnx_hc_xbrep, loaded on the
    // same edge from the same next-state: zero added cycles); the original register feeds the centre only.
    assign xb_v   = xvf[0];      assign xb_v_n   = xvf[1];      assign xb_v_e   = xvf[2];      assign xb_v_s   = xvf[3];
    assign xb_beat = xbf[1:0];   assign xb_beat_n = xbf[3:2];   assign xb_beat_e = xbf[5:4];   assign xb_beat_s = xbf[7:6];
    wire [8*256-1:0] xs;
    for (genvar k = 0; k < 8; k = k + 1) begin : g_xs
        for (genvar i = 0; i < 8; i = i + 1) begin : g_i
            assign xs[k*256 + i*32 +: 32] = xd[i*256 + k*32 +: 32];
        end
    end
    assign {xb_d7, xb_d6, xb_d5, xb_d4, xb_d3, xb_d2, xb_d1, xb_d0} = xs;
endmodule
`default_nettype wire
