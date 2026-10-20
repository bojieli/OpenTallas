`timescale 1ns/1ps
`default_nettype none
// Static HC QUARTER engine (HBM-B-RTL2, plan (b) d4g, 2026-10-17): one per quadrant (hc_eng_<q>, one master, x4),
// beside the quadrant's hc_<q> LG client.  It is the projection datapath of ot_hbm_hc_eng_static cut by the hidden
// dimension: quarter q owns lanes 64q .. 64q+63 of every W = 256 run, i.e. chunks r*256 + 64q + i (i = 0..63,
// r = 0..R-1) of the K = 20,480 vector (K/4 = 5,120 terms per quarter).  The root ot_hbm_hc_root_static keeps the
// programme, the HCP issue/scalar core, the mix store, the table and the tails.
//   BANKS   8 x ot_hbm_hc_bank_static #(W = 64) (term k of every 8-term chunk; 8 hard lane leaves, 8 weight + 4 x
//           macros each), chained 0 -> 7 exactly as in the full engine (csum chunk order ((0+t0)+t1)..+t7 kept).
//           Physically a SQUARE RING of the 8 bank tiles (3 x 3, centre = ingress + tree): bank 0 and bank 7 both sit
//           beside the centre, so the descriptor entry and the chunk-sum exit are short.
//   TREE    the first 6 levels of the csum pairwise chunk tree over the quarter's 64 chunk sums (ot_hdc_fp32_add_lat,
//           TLA stages a level, bit for bit the core's ot_hdc_fp32_add_fast): the result is the aligned 64-chunk
//           subtree sum, one binary32 a task, that the root's core (TPRE = 6) combines with the other 3 quarters'
//           ((q0 + q1) + (q2 + q3)) -- the same pairs as the 256-leaf tree, so every run sum is bit-identical.
//   INGRESS one x_wave port (this quadrant's hc_<q> reader, XW_BEATS = 4 beats of 2,048 b, ot_hbm_hc_xw_rx_static).
//           A quarter wave lw (lw = 0 .. K/1024 - 1 per row / position) carries quarter chunks 32 lw .. 32 lw + 31 =
//           run lw/2, lanes 32 (lw%2) .. +31 (global chunk r*256 + 64q + 32(lw%2) + m).  The 4 quarters land waves
//           in parallel (no cross-quadrant phase stagger any more: each quarter has its own bank write port).
// The ingest event (from the root programme, pin flops here) and the per-task descriptor (from the root core's tap 0,
// pin flops here) are the only inputs from the root; the 32-b subtree sum (+ valid + lane/tree fault) the only output.
// STATIC: no ready, credit or backpressure.  fault (sticky): a wave missing on its due edge, an unsolicited wave, a
// wrong word index, a residual word with nonzero low half, an overlapping ingest event, a bad event field, a beat
// error.  Pin registers: every input lands in a pin flop, every output is a flop.  rst_n: ot_rst_relay (sync release,
// one region per bank tile + centre); each bank tile relays it again at its own boundary (RST_RELAY 1).
// MUT (bench): 1 = bank 3 weight slice rotated, 3 = x landing one run off, 4 = tree level-1 pairs (0,2),(1,3)
// instead of (0,1),(2,3) (reduction order changed).
// RING FORM (2026-10-17, coordinator decision: hc_<q> + centre in the ring hole): this module is now the SOFT
// composition of the die tiles: ot_hbm_hc_qcen_static (centre, inside ot_hbm_hc_qhub_static) + bank tiles
// ot_hbm_hc_bankq0_static (bank 0, W edge, chain-exit relay), ot_hbm_hc_bankq_ft_static (banks 2 N / 6 S, feeding
// corners 1, 3 / 5, 7), ot_hbm_hc_bankq_static (banks 1, 3, 4, 5, 7). The x_wave data beats go to the banks directly
// (256-b slice each); corner banks write one edge later (their feed register). Ports unchanged.
module ot_hbm_hc_qeng_static #(
    parameter integer K    = 20480,
    parameter integer DRLY = 1,                  // relay registers centre <-> bank 0 / bank 7
    parameter integer TLA  = 7,                  // tree adder stages (1.2 GHz pipelined binary32 add)
    parameter integer XW_BEATS = 4,
    // HBM-RTL5 10-18 (coordinator 0fi, d4g HC U-ring): XRLY die relay stages on the bank 7 -> bank 0 chain-exit hop
    // (3x3 U with the hub on the mouth cell: b7 is not edge-adjacent to b0).  Default 0 = unchanged.  The stages come
    // out of the DRLY exit budget (bank 0 keeps DRLY - XRLY >= 1 registers), so the centre / root timing is that of
    // DRLY: the d4g U uses DRLY 2, XRLY 1 (hub DRLY 2, root QDRLY 2, bank 0 tile DRLY 1 unchanged).  One stage = the
    // die relay classes side by side, 1136 + 624 + 304 = 2,064 b (2,049 used: {lane fault, 64 chunk sums}; 15 spare
    // bits tied low), ot_hbm_rly = the hbfd_rly_{1136,624,304}_<flow> masters (reset: rs, released 3 edges later).
    parameter integer XRLY = 0,
    // HH-9 10-19 (47247cc08 bank_distance): CPR 1 = chain pin registers at the bank tile faces: banks 1, 3, 4, 5, 7
    // (ot_hbm_hc_bankq_static) CPI = CPO = 1, bank 0 CPO = 1, edge banks 2 / 6 unchanged -> the chain is CHX = 11
    // edges longer (centre CHX, root QCHX = 11).  Default 0 = unchanged.
    parameter integer CPR  = 0,
    // QHUB-S1 10-19: SAFE 1 = the hub centre's safe form (ot_hbm_hc_qcen_static SAFE: s_i pin register, +1 subtree edge ->
    // root QCHX + 1, programme RAW0 + 1; MUT 6 = that register without the valid delay).  Default 0 = unchanged.
    parameter integer SAFE = 0,
    parameter integer MUT  = 0
)(
    input  wire           clk, rst_n,
    // per-task descriptor from the root core (quarter lane count already clamped by the root)
    input  wire           d_v, d_ss,
    input  wire [6:0]     d_nv,
    input  wire [9:0]     d_wa, d_xa,
    // ingest event from the root programme
    input  wire           i_v, i_kind,
    input  wire [1:0]     i_slot,
    input  wire [4:0]     i_lo,
    input  wire [4:0]     i_w,
    input  wire [11:0]    i_cnt,
    input  wire [9:0]     i_word,
    // this quadrant's x_wave link (hc_<q>)
    input  wire           x_wave_v,
    input  wire [1:0]     x_wave_beat,
    input  wire [9:0]     x_wave_word,
    input  wire [8192/XW_BEATS-1:0] x_wave,
    // subtree sum to the root
    output reg            ps_v,
    output reg  [31:0]    ps,
    output reg            ps_f,
    output reg            fault
);
    localparam integer XB = 8192 / XW_BEATS;
    localparam integer CP = (CPR != 0) ? 1 : 0, CHX = 11 * CP;
    initial if (XW_BEATS != 4) $fatal(1, "ring form: XW_BEATS must be 4 (2,048-b beats, 256-b bank slices)");
    initial if (XRLY < 0 || DRLY - XRLY < 1) $fatal(1, "XRLY: 0 <= XRLY <= DRLY - 1 (bank 0 registers the exit)");
    // ------------------------------------------------------------------ centre
    wire [7:0] rb, wf; wire [12:0] wc_w, wc_n, wc_e, wc_s; wire [2048:0] s_c;
    wire bd_v, bd_ss; wire [6:0] bd_nv; wire [9:0] bd_wa, bd_xa;
    ot_hbm_hc_qcen_static #(.K(K), .DRLY(DRLY), .TLA(TLA), .CHX(CHX), .MUT((MUT == 3 || MUT == 4 || MUT == 6) ? MUT : 0),
        .SAFE(SAFE)) u_cen (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa),
        .i_v(i_v), .i_kind(i_kind), .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word),
        .x_v(x_wave_v), .x_beat(x_wave_beat), .x_word(x_wave_word), .s_i(s_c), .wfault_i(wf), .rst_b(rb),
        .bd_v(bd_v), .bd_ss(bd_ss), .bd_nv(bd_nv), .bd_wa(bd_wa), .bd_xa(bd_xa),
        .wc_w(wc_w), .wc_n(wc_n), .wc_e(wc_e), .wc_s(wc_s), .ps_v(ps_v), .ps(ps), .ps_f(ps_f), .fault(fault));
    // ------------------------------------------------------------------ per-bank beat slices (bank k = term k)
    wire [8*256-1:0] xs;
    for (genvar k = 0; k < 8; k = k + 1) begin : g_xs
        for (genvar i = 0; i < 8; i = i + 1) begin : g_i
            assign xs[k*256 + i*32 +: 32] = x_wave[i*256 + k*32 +: 32];
        end
    end
    // ------------------------------------------------------------------ ring chain 0 -> 7
    wire [8:0] cv, css, cf; wire [9*7-1:0] cnv; wire [9*10-1:0] cwa, cxa; wire [9*2048-1:0] csum;
    // corner feeds: bank 2 feeds 1 (a) and 3 (b); bank 6 feeds 5 (a) and 7 (b)
    wire [3:0] fx_v; wire [7:0] fx_b; wire [4*256-1:0] fx_d; wire [3:0] fwv, fxv, fj; wire [4*10-1:0] fwa;
    wire [3:0] frst, fwf_c;                        // corner reset (through the edge tile) / corner fault (into it)
    // HCRING 10-19 (bench only): link k (bank k-1 outputs -> bank k inputs; link 8 = bank 7 exit -> bank 0 s_i) as ONE
    // face vector in face-position order {f, sum[2047:0], xa, wa, nv, ss, v} (2,078 b).  Default: inputs = outputs.
    // +define+OT_HC_JOINT_MAP + hc_joint_map.svh (tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py) wires the
    // inputs as the PHYSICAL abutment of the two tile faces does (pins paired by position along the joint), so the
    // lockstep checks the bank pin plans + orientations, not only the names.
    localparam integer FV = 2078;
    wire [9*FV-1:0] fo, fi;
    for (genvar k = 0; k < 9; k = k + 1) begin : g_fv
        assign fo[k*FV +: FV] = {cf[k], csum[k*2048 +: 2048], cxa[k*10 +: 10], cwa[k*10 +: 10], cnv[k*7 +: 7], css[k], cv[k]};
    end
`ifdef OT_HC_JOINT_MAP
    `include "hc_joint_map.svh"
`else
    assign fi = fo;
`endif
    wire [8:0] jv, jss, jf; wire [9*7-1:0] jnv; wire [9*10-1:0] jwa, jxa; wire [9*2048-1:0] jsum;
    for (genvar k = 0; k < 9; k = k + 1) begin : g_fi
        assign {jf[k], jsum[k*2048 +: 2048], jxa[k*10 +: 10], jwa[k*10 +: 10], jnv[k*7 +: 7], jss[k], jv[k]} = fi[k*FV +: FV];
    end
    `define OT_HCQ_CHAIN(k) .d_v(jv[k]), .d_ss(jss[k]), .d_nv(jnv[(k)*7 +: 7]), .d_wa(jwa[(k)*10 +: 10]), .d_xa(jxa[(k)*10 +: 10]), \
        .o_v(cv[(k)+1]), .o_ss(css[(k)+1]), .o_nv(cnv[((k)+1)*7 +: 7]), .o_wa(cwa[((k)+1)*10 +: 10]), .o_xa(cxa[((k)+1)*10 +: 10]), \
        .sum_out(csum[((k)+1)*2048 +: 2048]), .f_out(cf[(k)+1])
    assign cv[0] = bd_v; assign css[0] = bd_ss; assign cnv[0 +: 7] = bd_nv; assign cwa[0 +: 10] = bd_wa; assign cxa[0 +: 10] = bd_xa;
    // bank 7 chain exit -> [XRLY die relay stages] -> bank 0 exit relay
    wire [2048:0] s_x [0:XRLY];
    assign s_x[0] = {jf[8], jsum[8*2048 +: 2048]};
    for (genvar r = 0; r < XRLY; r = r + 1) begin : g_xr
        wire [2063:0] ri = {15'd0, s_x[r]}, ro;
        ot_hbm_rly #(.W(1136)) u_r0 (.ck(clk), .rs(rb[0]), .i(ri[0    +: 1136]), .o(ro[0    +: 1136]));
        ot_hbm_rly #(.W(624))  u_r1 (.ck(clk), .rs(rb[0]), .i(ri[1136 +: 624]),  .o(ro[1136 +: 624]));
        ot_hbm_rly #(.W(304))  u_r2 (.ck(clk), .rs(rb[0]), .i(ri[1760 +: 304]),  .o(ro[1760 +: 304]));
        assign s_x[r+1] = ro[2048:0];
    end
    ot_hbm_hc_bankq0_static #(.MUT(0), .DRLY(DRLY - XRLY), .CPO(CP)) u_b0 (.clk(clk), .rst_n(rb[0]), `OT_HCQ_CHAIN(0),
        .xb_v(x_wave_v), .xb_beat(x_wave_beat), .xb_d(xs[0 +: 256]),
        .wv(wc_w[12]), .xv(wc_w[11]), .j(wc_w[10]), .wa(wc_w[9:0]), .wfault(wf[0]),
        .s_i(s_x[XRLY]), .s_o(s_c));
    for (genvar e = 0; e < 2; e = e + 1) begin : g_ft          // e 0: bank 2 (N, wc_n), e 1: bank 6 (S, wc_s)
        localparam integer K0 = 2 + 4 * e;
        wire [12:0] wc = (e == 0) ? wc_n : wc_s;
        ot_hbm_hc_bankq_ft_static #(.MUT(0)) u_b (.clk(clk), .rst_n(rb[K0]), `OT_HCQ_CHAIN(K0),
            .sum_in(jsum[K0*2048 +: 2048]), .f_in(jf[K0]),
            .xb_v(x_wave_v), .xb_beat(x_wave_beat), .xb_d(xs[K0*256 +: 256]),
            .wv(wc[12]), .xv(wc[11]), .j(wc[10]), .wa(wc[9:0]), .wfault(wf[K0]),
            .fa_xb_v(x_wave_v), .fa_xb_beat(x_wave_beat), .fa_xb_d(xs[(K0-1)*256 +: 256]),
            .fa_wv(wc[12]), .fa_xv(wc[11]), .fa_j(wc[10]), .fa_wa(wc[9:0]),
            .fa_xb_v_o(fx_v[2*e]), .fa_xb_beat_o(fx_b[4*e +: 2]), .fa_xb_d_o(fx_d[(2*e)*256 +: 256]),
            .fa_wv_o(fwv[2*e]), .fa_xv_o(fxv[2*e]), .fa_j_o(fj[2*e]), .fa_wa_o(fwa[(2*e)*10 +: 10]),
            .fb_xb_v(x_wave_v), .fb_xb_beat(x_wave_beat), .fb_xb_d(xs[(K0+1)*256 +: 256]),
            .fb_wv(wc[12]), .fb_xv(wc[11]), .fb_j(wc[10]), .fb_wa(wc[9:0]),
            .fb_xb_v_o(fx_v[2*e+1]), .fb_xb_beat_o(fx_b[4*e+2 +: 2]), .fb_xb_d_o(fx_d[(2*e+1)*256 +: 256]),
            .fb_wv_o(fwv[2*e+1]), .fb_xv_o(fxv[2*e+1]), .fb_j_o(fj[2*e+1]), .fb_wa_o(fwa[(2*e+1)*10 +: 10]),
            .fa_rst_n(rb[K0-1]), .fb_rst_n(rb[K0+1]), .fa_rst_n_o(frst[2*e]), .fb_rst_n_o(frst[2*e+1]),
            .fa_wfault(fwf_c[2*e]), .fb_wfault(fwf_c[2*e+1]), .fa_wfault_o(wf[K0-1]), .fb_wfault_o(wf[K0+1]));
    end
    // corners 1, 3, 5, 7 (feed index c = 0..3) and bank 4 (E edge, wc_e)
    for (genvar c = 0; c < 4; c = c + 1) begin : g_cn
        localparam integer KC = 2 * c + 1;
        ot_hbm_hc_bankq_static #(.MUT((MUT == 1 && KC == 3) ? 1 : 0), .CPI(CP), .CPO(CP)) u_b (.clk(clk), .rst_n(frst[c]), `OT_HCQ_CHAIN(KC),
            .sum_in(jsum[KC*2048 +: 2048]), .f_in(jf[KC]),
            .xb_v(fx_v[c]), .xb_beat(fx_b[2*c +: 2]), .xb_d(fx_d[c*256 +: 256]),
            .wv(fwv[c]), .xv(fxv[c]), .j(fj[c]), .wa(fwa[c*10 +: 10]), .wfault(fwf_c[c]));
    end
    ot_hbm_hc_bankq_static #(.MUT(0), .CPI(CP), .CPO(CP)) u_b4 (.clk(clk), .rst_n(rb[4]), `OT_HCQ_CHAIN(4),
        .sum_in(jsum[4*2048 +: 2048]), .f_in(jf[4]),
        .xb_v(x_wave_v), .xb_beat(x_wave_beat), .xb_d(xs[4*256 +: 256]),
        .wv(wc_e[12]), .xv(wc_e[11]), .j(wc_e[10]), .wa(wc_e[9:0]), .wfault(wf[4]));
    `undef OT_HCQ_CHAIN
endmodule
`default_nettype wire
