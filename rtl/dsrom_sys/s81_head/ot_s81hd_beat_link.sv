`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81hd_beat_tx / ot_s81hd_beat_rx (S81-HEAD/ADAPT 2026-10-25, COORD ruling (3) of 2026-10-25 03:45): the registered
// multi-beat fixed-latency link pair of the S81 head die.  Contract: results/arch/s81_head_1025/ADAPTER.md.
//
// It is the N-beat generalisation of the S81/SVCG 2-beat fold lane (dsdv_svc_f2b_tx / _rx, claude/s81-svcg-1024r
// @9be238f21b): same rules, a parameter N instead of the fixed 2, and an explicit valid + beat index field instead of
// the svcg trick of carrying v inside word[0] (the head records have their own valid next to W data bits, so word[0]
// is data).  The svcg modules are fixed at N = 2 and an odd W with v = word[0]; they do not fit, so this is a new pair.
//
// Word = {d[W-1:0]} + v.  P = ceil(W / N) payload bits a beat.  Port (P + 1 + BW wires, BW = max(1, clog2 N)) =
// {bi[BW-1:0], vb, pay[P-1:0]}:
//   beat k (k = 0 .. N-1) leaves in cycle t0 + k: vb = 1, bi = k, pay = word_padded[k*P +: P] (word_padded = {0, d});
//   the pad bits of beat N-1 (N*P - W of them) are 0.
// FIXED PHASE, no handshake, no credit.  Rate: at most one word every N cycles a direction (the compiled schedule's
// guarantee).  A violation is a STICKY fault, never arbitrated:
//   TX: a valid word while beats of the previous one are still owed (the new word is dropped);
//   RX: a beat with bi != 0 outside a word, a beat whose bi is not the expected next index, an idle cycle (vb = 0)
//       inside a word (dropped beat), or a non-zero pad bit in beat N-1.
// Latency: a word presented at the TX input in cycle t leaves at the RX output (v = 1) in cycle t + N + 1 + S, S = the
// number of plain relay registers between the TX pin register and the RX pin register (the plan lane's stations).
// The TX output register IS the TX pin flop; the RX input register IS the RX pin flop (partition pins registered).
// Reset (decision 2 / 13): control only -- owed count, expected index, the vb / bi pin-register bits and the faults.
// Data registers (hold, payload pin bits, assembly) have no reset.
// MUT (bench negative control, TX only): 0 = production; 1 = beats 0 and 1 swapped (each keeps its own bi);
//   2 = beat 1 dropped (vb = 0 in its cycle); 3 = TX rate check removed (a new word pre-empts the owed beats).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_beat_tx #(
    parameter integer W   = 553,
    parameter integer N   = 2,
    parameter integer MUT = 0,
    parameter integer P   = (W + N - 1) / N,
    parameter integer BW  = (N > 1) ? $clog2(N) : 1
) (
    input  wire                 ck,
    input  wire                 rn,          // control-only reset, active low
    input  wire                 v,
    input  wire [W-1:0]         d,
    output wire [P+BW:0]        o,           // {bi, vb, pay}: the TX pin register
    output reg                  fault
);
    localparam integer NP = N * P;
    localparam [BW-1:0] NM1 = BW'(N - 1);
    wire [NP-1:0] wp = {{(NP - W){1'b0}}, d};
    reg  [BW-1:0] owe;                       // beats still owed after the one in the pin register
    reg  [BW-1:0] nxt;                       // index of the next owed beat
    wire start = v && ((MUT == 3) ? 1'b1 : (owe == 0));
    reg  [P-1:0]  oq_p;                      // payload pin bits (data, no reset)
    reg           oq_v;
    reg  [BW-1:0] oq_b;
    generate if (N > 1) begin : g_multi
        reg [NP-P-1:0] hold;                 // beats 1 .. N-1 (data, no reset)
        wire [P-1:0] b0 = wp[P-1:0];
        wire [P-1:0] b1 = wp[2*P-1:P];
        reg  [NP-1:0] swp;                   // MUT 1 only: beats 0 and 1 exchanged
        always @(*) begin swp = wp; swp[P-1:0] = b1; swp[2*P-1:P] = b0; end
        always @(posedge ck) begin
            if (start) hold <= (MUT == 1) ? swp[NP-1:P] : wp[NP-1:P];
            else if (owe != 0) hold <= hold >> P;
            if (start) oq_p <= (MUT == 1) ? b1 : b0;
            else oq_p <= hold[P-1:0];
        end
        always @(posedge ck or negedge rn)
            if (!rn) begin owe <= 0; nxt <= 0; fault <= 1'b0; oq_v <= 1'b0; oq_b <= 0; end
            else begin
                if (v && owe != 0 && MUT != 3) fault <= 1'b1;          // rate violation: word dropped
                if (start) begin
                    owe <= NM1; nxt <= BW'(1);
                    oq_v <= 1'b1; oq_b <= (MUT == 1) ? BW'(1) : {BW{1'b0}};
                end else if (owe != 0) begin
                    owe <= owe - 1'b1; nxt <= nxt + 1'b1;
                    oq_v <= !((MUT == 2) && nxt == BW'(1));
                    oq_b <= (MUT == 1 && nxt == BW'(1)) ? {BW{1'b0}} : nxt;
                end else begin
                    oq_v <= 1'b0; oq_b <= 0;
                end
            end
    end else begin : g_one
        always @(posedge ck) oq_p <= wp[P-1:0];
        always @(posedge ck or negedge rn)
            if (!rn) begin owe <= 0; nxt <= 0; fault <= 1'b0; oq_v <= 1'b0; oq_b <= 0; end
            else begin oq_v <= v; oq_b <= 0; end
    end endgenerate
    assign o = {oq_b, oq_v, oq_p};
endmodule

module ot_s81hd_beat_rx #(
    parameter integer W  = 553,
    parameter integer N  = 2,
    parameter integer P  = (W + N - 1) / N,
    parameter integer BW = (N > 1) ? $clog2(N) : 1
) (
    input  wire                 ck,
    input  wire                 rn,
    input  wire [P+BW:0]        i,           // {bi, vb, pay}
    output wire                 v,           // word valid in the cycle its last beat sits in the RX pin register
    output wire [W-1:0]         d,
    output reg                  fault
);
    localparam integer NP = N * P;
    localparam integer PADN = NP - W;
    localparam [BW-1:0] LASTB = BW'(N - 1);
    reg  [P-1:0]  iq_p;                      // RX pin register payload (data, no reset)
    reg           iq_v;
    reg  [BW-1:0] iq_b;
    always @(posedge ck) iq_p <= i[P-1:0];
    always @(posedge ck or negedge rn)
        if (!rn) begin iq_v <= 1'b0; iq_b <= 0; end
        else begin iq_v <= i[P]; iq_b <= i[P+BW:P+1]; end
    reg           mid;                       // inside a word: the next beat must be index `ex`
    reg  [BW-1:0] ex;
    wire [BW-1:0] want = mid ? ex : {BW{1'b0}};
    wire          ord_ok = iq_v && (iq_b == want);
    wire          last = ord_ok && (iq_b == LASTB);
    wire          pad_bad;
    generate if (PADN > 0) begin : g_pad
        assign pad_bad = |iq_p[P-1:P-PADN];
    end else begin : g_nopad
        assign pad_bad = 1'b0;
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) begin mid <= 1'b0; ex <= 0; fault <= 1'b0; end
        else begin
            if (iq_v && !ord_ok) fault <= 1'b1;                 // beat out of order / bi != 0 outside a word
            if (!iq_v && mid) fault <= 1'b1;                    // dropped beat inside a word
            if (last && pad_bad) fault <= 1'b1;                 // beat N-1 pad bits must be 0
            if (ord_ok && !last) begin mid <= 1'b1; ex <= iq_b + 1'b1; end
            else begin mid <= 1'b0; ex <= 0; end
        end
    generate if (N > 1) begin : g_multi
        reg [NP-P-1:0] asm_q;                // beats 0 .. N-2 (data, no reset)
        integer k;
        always @(posedge ck)
            for (k = 0; k < N - 1; k = k + 1)
                if (ord_ok && iq_b == BW'(k)) asm_q[k*P +: P] <= iq_p;
        wire [NP-1:0] word = {iq_p, asm_q};
        assign d = word[W-1:0];
    end else begin : g_one
        assign d = iq_p[W-1:0];
    end endgenerate
    assign v = last && !pad_bad;
endmodule
`default_nettype wire
