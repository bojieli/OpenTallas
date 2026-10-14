`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B TP8 two-die split (owner 2026-10-14 06:45 PT: compute/ROM die + KV/system die), die-link endpoint helpers.
// Contract: results/arch/qwen_split_1014/LINK.md (class 0 CTL / class 6 SCTL).
//
// The merged-die sequencer (ot_qkvd_kv_seq_merged) talks to the ROM sequencer over RAW LEVEL faces (sd 56 b in,
// ds 187 b + pw 75 b out) that also carry one-cycle posted pulses (h_start, pw_v, dw_v).  Across the link a level face
// becomes EVENT WORDS: a word is sent when the registered face differs from the last value sent (levels) or when a
// pulse bit has fired since the last word (pulses, kept pending until sent).  The receiver holds the levels of the
// latest word and asserts a pulse bit for exactly the one cycle after its word arrives.  Order is kept by the link
// class (in order per class), so the receiver's level sequence is the sender's, with link latency.
//
// ot_qwen_split_lvl_tx  face (captured at the pin) -> v / d words under C0 credits (cr returns one).  Levels coalesce
//                       while credits are short (only the latest value matters); a pulse bit that fires again while
//                       its previous firing is still pending is a sticky fault (it would be lost): fail closed.
// ot_qwen_split_lvl_rx  v / d words (captured at the pin) -> face; cr = one registered pulse per word taken.
// Every input is captured at a pin flop, every output is launched from a flop (no same-cycle ready anywhere).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_split_lvl_tx #(
    parameter integer         W  = 56,
    parameter [W-1:0]         PM = {W{1'b0}},   // pulse bits
    parameter integer         C0 = 4             // initial credits (= the receiving buffer)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] face,
    output reg          v,
    output reg  [W-1:0] d,
    input  wire         cr,
    output reg          fault
);
    reg [W-1:0] f, last, pend;
    reg         crq, started;
    reg [7:0]   c;
    always @(posedge clk) f <= face;
    wire [W-1:0] lv   = f & ~PM;
    wire [W-1:0] pl   = (pend | (f & PM));
    // the first word after reset is sent unconditionally: the receiver starts from all-zero levels, the sender's
    // face may not be zero at release
    wire         want = !started || (lv != last) || (pl != {W{1'b0}});
    wire         send = want && (c != 8'd0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            v <= 1'b0; d <= {W{1'b0}}; last <= {W{1'b0}}; pend <= {W{1'b0}}; crq <= 1'b0; c <= 8'(C0);
            fault <= 1'b0; started <= 1'b0;
        end else begin
            crq <= cr;
            v <= send;
            if (send) begin d <= lv | pl; last <= lv; pend <= {W{1'b0}}; started <= 1'b1; end
            else pend <= pl;
            if ((pend & f & PM) != {W{1'b0}}) fault <= 1'b1;   // a second firing before the first left: one would merge
            c <= c - (send ? 8'd1 : 8'd0) + (crq ? 8'd1 : 8'd0);
        end
endmodule

module ot_qwen_split_lvl_rx #(
    parameter integer         W  = 56,
    parameter [W-1:0]         PM = {W{1'b0}}
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [W-1:0] d,
    output reg          cr,
    output reg  [W-1:0] face
);
    reg         vq;
    reg [W-1:0] dq;
    always @(posedge clk) dq <= d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vq <= 1'b0; cr <= 1'b0; face <= {W{1'b0}}; end
        else begin
            vq <= v;
            cr <= vq;
            if (vq) face <= dq;                    // levels and pulses of the new word
            else    face <= face & ~PM;            // pulses last one cycle
        end
endmodule
