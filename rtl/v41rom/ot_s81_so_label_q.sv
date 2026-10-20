`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_so_label_q (S81-RTAG 2026-10-20, rate plan F4 "router segment-tag widening"): go-aligned output-label tables
// for the BF front (ot_v41_bf_front_core_roots SOQ != 0).
//
// Problem (TOKSIM-S81C/FSEQ 10-19, S81-WQBP 10-20): the column labels every partial it emits ({row, segment index,
// segment count} = so_row / so_idx / so_n [tree segment]) from tables that follow the configuration WRITES (QK edges
// late).  The next phase's configuration is broadcast before its go, so a BF phase whose partials still drain when the
// next phase's configuration lands gets the next phase's label (values right, label wrong).  Static BF phase sequences
// therefore needed P >= 231 (router 5 phases, wo_a 12 phases).  Measured (S81-RTAG trace): every BF partial of these
// ops reads its label at go_e + 172; the next phase's segment-0 write lands about 47-62 edges before its go.
//
// Fix (static, no handshake): the label tables switch at a FIXED edge after each go, not at the configuration write.
// One edge after go the live segment tables (final before go; the next configuration write comes >= ~60 edges after
// this go at any legal period) are snapshotted into an in-order NQ-entry queue; each entry is copied to so_* exactly
// SWD edges after its go_e.  So, for every edge t, so_* = the tables of the latest phase k with go_k + SWD <= t.
// Compiler checks (static calendar, never runtime):  every partial of phase k leaves the column in
// [go_k + SWD, go_{k+1} + SWD);  no configuration write in (go_k, go_k + 1];  P >= SWD / NQ  (a go into a full queue is
// a sticky fault, ORed into the front fault: observation only, never absorbed).
// Safe design: every 16-bit chunk of the table has its own KEPT write-enable / pop / read-pointer copy (16 bits x 2
// gates = 32 loads; ot_keep_regs keeps the copies); storage NQ x TW = 2 x 336 b flops (< 2 kb); no reset on the
// table payload (as the configuration registers), counters / valids / copies reset.  +0 data-path cycles (the label
// switch edge is a schedule constant).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_so_label_q #(
    parameter integer NSEG = 8,
    parameter integer NB = 2,
    parameter integer SWD = 160,      // go_e -> label switch edges (<= shortest go_e -> partial label read, 172 measured)
    parameter integer NQ = 2          // fixed: two pending phases (P >= SWD / 2); the payload below is written for 2
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     go,          // go_e: one phase start per rising edge
    input  wire [1:0]               go_c,        // S81-BF6: two same-edge copies of go (each drives half the chunks)
    input  wire [16*NB*NSEG-1:0]    s_row,       // live tables (flattened)
    input  wire [5*NSEG-1:0]        s_idx,
    input  wire [5*NSEG-1:0]        s_n,
    output wire [16*NB*NSEG-1:0]    so_row,
    output wire [5*NSEG-1:0]        so_idx,
    output wire [5*NSEG-1:0]        so_n,
    output reg                      fault
);
    localparam integer TW = 16 * NB * NSEG + 10 * NSEG;
    localparam integer CK = 16;                  // chunk: an enable / select drives 2 gates a bit -> 32 loads
    localparam integer NC = (TW + CK - 1) / CK;
    localparam integer CW = $clog2(SWD + 201);   // + the MUT_LATE range (no cost in function)
    localparam integer PW = 1;
`ifdef OT_S81_SOQ_MUT_LATE
    localparam [CW-1:0] SW1 = CW'(SWD + 198);      // negative control: label switches 200 edges late (stale label)
`else
    localparam [CW-1:0] SW1 = CW'(SWD - 2);        // + 1 edge enable copy + 1 edge payload copy = SWD
`endif
    wire [TW-1:0] live = {s_n, s_idx, s_row};
    wire [TW-1:0] so;
    assign {so_n, so_idx, so_row} = so;
    // ---- control: in-order queue of NQ pending phases, one countdown each ----
    reg  [CW-1:0]  q_c [0:NQ-1];
    reg  [NQ-1:0]  q_v;
    reg  [PW-1:0]  wp, rp;
    reg            go_q;
    wire           start = go && !go_q;
    // S81-BF6: per half of the chunks, kept copies of go_q / wp (loaded exactly as go_q / wp) and the start event from
    // the half's own go copy, so the chunk enable copies (2 per chunk) load from <= 32-load nets
    (* keep *) reg [1:0] go_qk;
    (* keep *) reg [1:0] wpk;
    wire [1:0] start_k = go_c & ~go_qk;
    wire           pop = q_v[rp] && q_c[rp] == '0;
    integer k;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            go_q <= 1'b0; q_v <= '0; wp <= '0; rp <= '0; fault <= 1'b0; go_qk <= '0; wpk <= '0;
            for (k = 0; k < NQ; k = k + 1) q_c[k] <= '0;
        end else begin
            go_q <= go;
            go_qk <= go_c;
            for (k = 0; k < NQ; k = k + 1) if (q_v[k] && q_c[k] != '0) q_c[k] <= q_c[k] - 1'b1;
            if (pop) begin
                q_v[rp] <= 1'b0;
                rp <= (rp == PW'(NQ - 1)) ? '0 : rp + 1'b1;
            end
            if (start) begin
                if (q_v[wp] && !(pop && rp == wp)) fault <= 1'b1;   // NQ gos inside one SWD window
                q_v[wp] <= 1'b1; q_c[wp] <= SW1;
                wp <= (wp == PW'(NQ - 1)) ? '0 : wp + 1'b1;
            end
            for (k = 0; k < 2; k = k + 1) if (start_k[k]) wpk[k] <= (wpk[k] == PW'(NQ - 1)) ? '0 : wpk[k] + 1'b1;
        end
    // ---- payload: per 16-bit chunk, kept enable / pop / pointer copies (fanout <= 32 each) ----
    genvar c;
    for (c = 0; c < NC; c = c + 1) begin : g_ch
        localparam integer LO = CK * c;
        localparam integer W = (TW - LO) < CK ? (TW - LO) : CK;
        (* keep *) reg [1:0]    we;      // entry write enable copy (start && wp == entry), one edge after go_e
        (* keep *) reg          pp;      // pop copy
        (* keep *) reg          rs;      // read pointer copy at pop
        // no reset on the copies (reset fan-out stays on the ~24 control flops): they are registered functions of the
        // reset control, so one clocked edge in reset clears them (start = pop = 0 while reset holds)
        always @(posedge clk) begin we <= {start_k[c % 2] && wpk[c % 2] == 1'b1, start_k[c % 2] && wpk[c % 2] == 1'b0}; pp <= pop; rs <= rp; end
        reg [W-1:0] qd0, qd1, od;          // two explicit entries (NQ = 2), no runtime-indexed array
        always @(posedge clk) begin
            if (we[0]) qd0 <= live[LO +: W];
            if (we[1]) qd1 <= live[LO +: W];
            if (pp) od <= rs ? qd1 : qd0;
        end
        assign so[LO +: W] = od;
    end
endmodule
`default_nettype wire
