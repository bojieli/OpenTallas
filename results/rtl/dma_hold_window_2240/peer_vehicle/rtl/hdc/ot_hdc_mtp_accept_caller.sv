`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Caller of the protected full-width DeepSeek MTP accept leaf
// (rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv, NSLOT 8 / NW 21) for the
// decode core's sequencer -- the core-side ABI of ot_hdc_accept (start / TOKX / AMAX / ACCEPT pulses in,
// stok / ttok / acc_* out), so ot_hdc_core_v41x selects it with ACC_GUARD = 1 (default 0: ot_hdc_accept).
//
// Per speculative step (an ITER run, iter = 1 at start):
//   start  -> leaf start (start_pos = pos, start_tok = token, start_g = gamma); the leaf returns the lease
//             {generation, pos}, which every later query of the cohort carries;
//   TOKX / AMAX -> one held request each (the leaf takes one of a kind per cycle and refuses a rewrite);
//             the core's control steps are >= 5 cycles apart, so one holding register per kind suffices,
//             and a second pulse while one is held raises fault (fail-closed, never dropped);
//   ACCEPT -> leaf accept query once the held TOKX / AMAX requests are absorbed; acc_done is the leaf's
//             guarded output (OUTPUT phase).  The caller latches the result (n_emit, a, bonus, ttok) as the
//             consumer, ACKs the leaf with the lease and fences the cohort (fence_receipts = all six: the
//             core keeps no other copy; rejected slots' KV / compressor / index rows are DEAD by the
//             program's invariant and need no erase), returning the leaf to IDLE for the next step.
// A STEP run (prefill / one-position decode, iter = 0) starts no cohort: stok[0] is the start token from a
// local register and acc_any is 0, as ot_hdc_accept gives a run without ACCEPT.
// hold = 1 while a TOKX / AMAX / ACCEPT request is held: the core's S_DYN waits on it (a DYN control step
// must see every draft token in the leaf's slots).
//
// ovr_en / ovr_tok: SIMULATION-ONLY acceptance-coverage device (never written by RTL, constant 0 in a
// build): when set by a bench, a TOKX of slot k forwards ovr_tok[k] instead of the drafter's token -- the
// forced drafter of tools/rtl_hdc_v41_mtp_campaign.py (stok is read only at DYN and ACCEPT, so replacing a
// draft at TOKX equals the ISA model's replacement at DYN).
// ---------------------------------------------------------------------------
module ot_hdc_mtp_accept_caller #(
    parameter integer NSLOT = 8,
    parameter integer NW    = 16,
    parameter integer SLW   = 3
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                start_v,
    input  wire                iter,
    input  wire [NW-1:0]       start_pos,
    input  wire [NW-1:0]       start_tok,
    input  wire [2:0]          gamma,
    input  wire                tokx_v,
    input  wire [SLW-1:0]      tokx_slot,
    input  wire [NW-1:0]       tokx_tok,
    input  wire                amax_v,
    input  wire [SLW-1:0]      amax_slot,
    input  wire [NW-1:0]       amax_tok,
    input  wire                acc_v,
    input  wire [SLW-1:0]      acc_g,
    output wire [NSLOT*NW-1:0] stok,
    output wire [NSLOT*NW-1:0] ttok,
    output wire                acc_done,
    output reg                 acc_any,
    output reg  [SLW-1:0]      acc_a,
    output reg  [SLW:0]        n_emit,
    output reg  [NW-1:0]       bonus,
    output wire                hold,
    output reg                 fault
);
    localparam integer LW = 21;
    // leaf
    wire        l_start_ready, l_tokx_ready, l_amax_ready, l_accept_ready, l_fence_ready;
    wire [167:0] l_stok, l_ttok;
    wire        l_out_v, l_acc_done, l_acc_any, l_fault, l_corrected;
    wire [2:0]  l_acc_a;
    wire [3:0]  l_n_emit;
    wire [20:0] l_bonus;
    wire [24:0] l_lease;
    // caller state
    reg         coh;                         // a cohort (ITER step) is live in the leaf
    reg         hx_v, hm_v, ha_v, ack_v, fen_v;
    reg  [2:0]  hx_s, hm_s, ha_g;
    reg  [20:0] hx_t, hm_t;
    reg  [NW-1:0] tok0;
    reg  [NW-1:0] ttok_r [0:NSLOT-1];
    reg         res_v;                       // the latched result is the consumer's copy
    reg  [NW-1:0] ovr_tok [0:NSLOT-1];       // simulation-only coverage device (see header)
    reg         ovr_en;
    integer k;
    initial begin ovr_en = 1'b0; for (k = 0; k < NSLOT; k = k + 1) ovr_tok[k] = 0; end

    wire do_start = start_v && iter;
    ot_hdc_mtp_accept_guarded #(.NSLOT(8), .NW(21), .ENABLE(1)) u_leaf (
        .clk(clk), .rst_n(rst_n), .admission_stop(1'b0), .caller_bad(1'b0),
        .start_v(do_start), .start_pos({{(LW-NW){1'b0}}, start_pos}), .start_tok({{(LW-NW){1'b0}}, start_tok}),
        .start_g(gamma), .start_ready(l_start_ready),
        .tokx_v(hx_v), .tokx_lease(l_lease), .tokx_slot(hx_s), .tokx_tok(hx_t), .tokx_ready(l_tokx_ready),
        .amax_v(hm_v), .amax_lease(l_lease), .amax_slot(hm_s), .amax_tok(hm_t), .amax_ready(l_amax_ready),
        .accept_v(ha_v && !hx_v && !hm_v), .accept_lease(l_lease), .accept_g(ha_g), .accept_ready(l_accept_ready),
        .stok(l_stok), .ttok(l_ttok), .out_v(l_out_v), .acc_done(l_acc_done), .acc_any(l_acc_any),
        .acc_a(l_acc_a), .n_emit(l_n_emit), .bonus(l_bonus), .lease(l_lease),
        .out_ready(ack_v), .ack_lease(l_lease),
        .fence_v(fen_v), .fence_lease(l_lease), .fence_receipts(6'd63), .fence_rearm(1'b0),
        .fence_ready(l_fence_ready), .fault(l_fault), .corrected(l_corrected));

    genvar gv;
    generate
        for (gv = 0; gv < NSLOT; gv = gv + 1) begin : g_o
            // slot 0 of a STEP run is the local start token; otherwise the leaf's slots
            if (gv == 0) assign stok[0 +: NW] = coh ? l_stok[0 +: NW] : tok0;
            else assign stok[gv*NW +: NW] = coh ? l_stok[gv*21 +: NW] : {NW{1'b0}};
            assign ttok[gv*NW +: NW] = ttok_r[gv];
        end
    endgenerate
    assign acc_done = l_acc_done;
    assign hold = hx_v || hm_v || ha_v;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            coh <= 1'b0; hx_v <= 1'b0; hm_v <= 1'b0; ha_v <= 1'b0; ack_v <= 1'b0; fen_v <= 1'b0;
            hx_s <= 0; hm_s <= 0; ha_g <= 0; hx_t <= 0; hm_t <= 0; tok0 <= 0; res_v <= 1'b0;
            acc_any <= 1'b0; acc_a <= 0; n_emit <= 0; bonus <= 0; fault <= 1'b0;
            for (k = 0; k < NSLOT; k = k + 1) ttok_r[k] <= 0;
        end else begin
            if (l_fault) fault <= 1'b1;
            if (start_v) begin
                tok0 <= start_tok; acc_any <= 1'b0; res_v <= 1'b0;
                if (iter) begin
                    coh <= 1'b1;
                    if (!l_start_ready) fault <= 1'b1;            // previous cohort not fenced: fail closed
                end
            end
            // held TOKX / AMAX / ACCEPT requests: released when the leaf takes them
            if (tokx_v) begin
                if (hx_v || !coh) fault <= 1'b1;
                hx_v <= 1'b1; hx_s <= tokx_slot;
                hx_t <= ovr_en ? {{(LW-NW){1'b0}}, ovr_tok[tokx_slot]} : {{(LW-NW){1'b0}}, tokx_tok};
            end else if (hx_v && l_tokx_ready) hx_v <= 1'b0;
            if (amax_v) begin
                if (hm_v || !coh) fault <= 1'b1;
                hm_v <= 1'b1; hm_s <= amax_slot; hm_t <= {{(LW-NW){1'b0}}, amax_tok};
            end else if (hm_v && l_amax_ready) hm_v <= 1'b0;
            if (acc_v) begin
                if (ha_v || !coh || acc_g != gamma) fault <= 1'b1;
                ha_v <= 1'b1; ha_g <= acc_g;
            end else if (ha_v && !hx_v && !hm_v && l_accept_ready) ha_v <= 1'b0;
            // the guarded result: latch it (the consumer's copy), ACK, then fence the cohort
            if (l_acc_done) begin
                acc_any <= l_acc_any; acc_a <= l_acc_a[SLW-1:0]; n_emit <= l_n_emit[SLW:0];
                bonus <= l_bonus[NW-1:0]; res_v <= 1'b1;
                for (k = 0; k < NSLOT; k = k + 1) ttok_r[k] <= l_ttok[k*21 +: NW];
                ack_v <= 1'b1;
            end else if (ack_v) begin
                ack_v <= 1'b0; fen_v <= 1'b1;
            end else if (fen_v && l_fence_ready) begin
                fen_v <= 1'b0;
            end
            if (fen_v && l_fence_ready) coh <= 1'b0;
        end
    end
    // the cohort's slot tokens are read by DYN only while it is live; after the fence stok[1..] read 0
endmodule
