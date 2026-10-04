`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Accept-stage port of the DSpark control loop: one simple, never-stalling request
// interface in front of either greedy accept unit (no accept arithmetic here).
//
//   LEAF = 0  rtl/hdc/ot_hdc_accept.sv (the core-agnostic greedy accept unit);
//   LEAF = 1  Codex's protected full-width DS MTP accept leaf
//             rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv
//             (NSLOT 8 / NW 21, SECDED state, lease-keyed caller ABI, ENABLE = 1),
//             reused unmodified: its start / TOKX / AMAX / ACCEPT handshakes, the
//             immediate output ACK and the end-of-step fence are sequenced here.
//
// Requests (pulses, in order, queued QD deep): start (pos, pending token, g), tokx
// (slot >= 1, draft), amax (slot, target), acc, release (the step committed: the
// leaf's fence, which clears its slots; LEAF 0 ignores it).  acc_done pulses when the
// result is ready; acc_a / bonus / ttok hold until the release.
// ---------------------------------------------------------------------------
module ot_dshbm_accept_port #(
    parameter integer LEAF = 0,
    parameter integer TW   = 17,
    parameter integer QD   = 16
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            start_v,
    input  wire [31:0]     start_pos,
    input  wire [TW-1:0]   start_tok,
    input  wire [2:0]      start_g,
    input  wire            tokx_v,
    input  wire [2:0]      tokx_slot,
    input  wire [TW-1:0]   tokx_tok,
    input  wire            amax_v,
    input  wire [2:0]      amax_slot,
    input  wire [TW-1:0]   amax_tok,
    input  wire            acc_v,
    input  wire [2:0]      acc_g,
    input  wire            release_v,
    output wire            acc_done,
    output wire [2:0]      acc_a,
    output wire [TW-1:0]   bonus,
    output wire [8*TW-1:0] ttok,
    output wire            fault
);
    generate if (LEAF == 0) begin : g_hdc
        wire [8*TW-1:0] stok;
        wire acc_any;
        wire [3:0] n_emit;
        ot_hdc_accept #(.NSLOT(8), .NW(TW)) u_acc (
            .clk(clk), .rst_n(rst_n), .start_v(start_v), .start_tok(start_tok),
            .tokx_v(tokx_v), .tokx_slot(tokx_slot), .tokx_tok(tokx_tok),
            .amax_v(amax_v), .amax_slot(amax_slot), .amax_tok(amax_tok),
            .acc_v(acc_v), .acc_g(acc_g), .stok(stok), .ttok(ttok), .acc_done(acc_done), .acc_any(acc_any),
            .acc_a(acc_a), .n_emit(n_emit), .bonus(bonus));
        assign fault = 1'b0;
    end else begin : g_leaf
        localparam [2:0] Q_START = 0, Q_TOKX = 1, Q_AMAX = 2, Q_ACC = 3, Q_REL = 4;
        localparam integer QW = 3 + 3 + 21 + 21;
        reg [QW-1:0] q [0:QD-1];
        reg [4:0] qw, qr;
        wire qe = (qw == qr);
        wire [QW-1:0] h = q[qr[3:0]];
        wire [2:0]  hk = h[QW-1 -: 3];
        wire [2:0]  hs = h[QW-4 -: 3];
        wire [20:0] ha = h[41:21];
        wire [20:0] hb = h[20:0];
        wire start_ready, tokx_ready, amax_ready, accept_ready, fence_ready, out_v, l_done, acc_any, corrected;
        wire [167:0] stok, l_ttok;
        wire [2:0] l_a;
        wire [3:0] n_emit;
        wire [20:0] l_bonus;
        wire [24:0] lease;
        wire go_start = !qe && hk == Q_START;
        wire go_tokx  = !qe && hk == Q_TOKX;
        wire go_amax  = !qe && hk == Q_AMAX;
        wire go_acc   = !qe && hk == Q_ACC;
        wire go_rel   = !qe && hk == Q_REL;
        ot_hdc_mtp_accept_guarded #(.NSLOT(8), .NW(21), .ENABLE(1'b1)) u_leaf (
            .clk(clk), .rst_n(rst_n), .admission_stop(1'b0), .caller_bad(1'b0),
            .start_v(go_start), .start_pos(ha), .start_tok(hb), .start_g(hs), .start_ready(start_ready),
            .tokx_v(go_tokx), .tokx_lease(lease), .tokx_slot(hs), .tokx_tok(hb), .tokx_ready(tokx_ready),
            .amax_v(go_amax), .amax_lease(lease), .amax_slot(hs), .amax_tok(hb), .amax_ready(amax_ready),
            .accept_v(go_acc), .accept_lease(lease), .accept_g(hs), .accept_ready(accept_ready),
            .stok(stok), .ttok(l_ttok), .out_v(out_v), .acc_done(l_done), .acc_any(acc_any), .acc_a(l_a),
            .n_emit(n_emit), .bonus(l_bonus), .lease(lease), .out_ready(out_v), .ack_lease(lease),
            .fence_v(go_rel), .fence_lease(lease), .fence_receipts(6'd63), .fence_rearm(1'b0),
            .fence_ready(fence_ready), .fault(fault), .corrected(corrected));
        wire pop = (go_start && start_ready) || (go_tokx && tokx_ready) || (go_amax && amax_ready) ||
                   (go_acc && accept_ready) || (go_rel && fence_ready);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin qw <= 0; qr <= 0; end
            else begin
                // one request a cycle from the loop (its requests are never simultaneous)
                if (start_v)        begin q[qw[3:0]] <= {Q_START, start_g, start_pos[20:0], {{(21-TW){1'b0}}, start_tok}}; qw <= qw + 1; end
                else if (tokx_v)    begin q[qw[3:0]] <= {Q_TOKX, tokx_slot, 21'd0, {{(21-TW){1'b0}}, tokx_tok}}; qw <= qw + 1; end
                else if (amax_v)    begin q[qw[3:0]] <= {Q_AMAX, amax_slot, 21'd0, {{(21-TW){1'b0}}, amax_tok}}; qw <= qw + 1; end
                else if (acc_v)     begin q[qw[3:0]] <= {Q_ACC, acc_g, 21'd0, 21'd0}; qw <= qw + 1; end
                else if (release_v) begin q[qw[3:0]] <= {Q_REL, 3'd0, 21'd0, 21'd0}; qw <= qw + 1; end
                if (pop) qr <= qr + 1;
            end
        end
        assign acc_done = l_done;
        assign acc_a = l_a;
        assign bonus = l_bonus[TW-1:0];
        genvar gs;
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_t
            assign ttok[gs*TW +: TW] = l_ttok[gs*21 +: TW];
        end
    end endgenerate
endmodule
