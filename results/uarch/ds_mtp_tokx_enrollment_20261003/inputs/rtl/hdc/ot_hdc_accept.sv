`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Speculative-decoding accept unit of the hardwired decode cores (model-
// agnostic: V4.1 MTP in ot_hdc_core_v41x, Qwen3 in ot_hdc_core).
//
// A speculative step runs NSLOT position slots: slot j sits at position
// pos + j and carries token stok[j] -- stok[0] the pending token (the step's
// start token), stok[1 .. g] the g draft tokens.  The verify pass of the main
// model yields a target ttok[j] (the argmax of slot j's logits) per slot.
//
//   start   stok[0] <= start_tok (the other slots keep no meaning until written)
//   TOKX    stok[slot] <= tok    (a draft token, from the drafter's argmax)
//   AMAX    ttok[slot] <= tok    (a verify target, from the head's argmax)
//   ACCEPT  a = the longest prefix i = 0, 1, .. < g with stok[i+1] == ttok[i]
//           (greedy speculative decoding: draft i+1 is accepted when it is the
//           token the main model emits after slot i); the step emits ttok[0 ..
//           a] -- the a accepted drafts (equal to ttok[0 .. a-1]) and the bonus
//           ttok[a] -- so n_emit = a + 1 and the next step's pending token is
//           ttok[a].  Registered: the outputs are valid the cycle after acc_v.
//
// Nothing else in a core is predicated on a: rejected slots' position-indexed
// writes are dead (no read reaches them before the next step rewrites them),
// so a commit is the host's position advance of n_emit, plus whatever
// history the core keeps outside position-indexed memory (V4.1: the Engram
// hash history, restored to its snapshot after slot a).
// ---------------------------------------------------------------------------
module ot_hdc_accept #(
    parameter integer NSLOT = 8,
    parameter integer NW    = 16,
    parameter integer SLW   = (NSLOT > 1) ? $clog2(NSLOT) : 1
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                start_v,
    input  wire [NW-1:0]       start_tok,
    input  wire                tokx_v,
    input  wire [SLW-1:0]      tokx_slot,
    input  wire [NW-1:0]       tokx_tok,
    input  wire                amax_v,
    input  wire [SLW-1:0]      amax_slot,
    input  wire [NW-1:0]       amax_tok,
    input  wire                acc_v,
    input  wire [SLW-1:0]      acc_g,          // drafts verified (g <= NSLOT - 1)
    output wire [NSLOT*NW-1:0] stok,
    output wire [NSLOT*NW-1:0] ttok,
    output reg                 acc_done,       // one cycle after acc_v
    output reg                 acc_any,        // an ACCEPT happened since start
    output reg  [SLW-1:0]      acc_a,          // drafts accepted
    output reg  [SLW:0]        n_emit,         // a + 1
    output reg  [NW-1:0]       bonus           // ttok[a]: the next pending token
);
    reg [NW-1:0] s [0:NSLOT-1];
    reg [NW-1:0] t [0:NSLOT-1];
    genvar gv;
    generate
        for (gv = 0; gv < NSLOT; gv = gv + 1) begin : g_o
            assign stok[gv*NW +: NW] = s[gv];
            assign ttok[gv*NW +: NW] = t[gv];
        end
    endgenerate
    // the longest matching prefix: match[i] = draft i+1 equals target i, i < g
    reg [NSLOT-1:0] match;
    reg [SLW-1:0]   a_c;
    reg             run;
    integer i;
    always @(*) begin
        match = 0;
        for (i = 0; i + 1 < NSLOT; i = i + 1)
            match[i] = (i < acc_g) && (s[i + 1] == t[i]);
        a_c = 0;
        run = 1'b1;
        for (i = 0; i + 1 < NSLOT; i = i + 1) begin
            run = run && match[i];
            /* verilator lint_off WIDTH */
            if (run) a_c = i + 1;
            /* verilator lint_on WIDTH */
        end
    end
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < NSLOT; k = k + 1) begin s[k] <= 0; t[k] <= 0; end
            acc_done <= 1'b0; acc_any <= 1'b0; acc_a <= 0; n_emit <= 0; bonus <= 0;
        end else begin
            acc_done <= acc_v;
            if (start_v) begin
                s[0] <= start_tok;
                acc_any <= 1'b0;
            end
            if (tokx_v) s[tokx_slot] <= tokx_tok;
            if (amax_v) t[amax_slot] <= amax_tok;
            if (acc_v) begin
                acc_any <= 1'b1;
                acc_a <= a_c;
                n_emit <= {1'b0, a_c} + 1'b1;
                bonus <= t[a_c];
            end
        end
    end
endmodule
