`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MTP commit / rollback sequencer (DS-V4.1; stream mtp-rollback 2026-10-08).
//
// After a verify pass at anchor q (last committed position) with g drafts and a accepted drafts
// (ot_hdc_accept acc_a), the golden keeps positions 0 .. q+1+a (Model.truncate(state, q+2+a)).
// Every speculative state of V4.1 is position-indexed in a ring sized for exact rollback
// (ot_mtp_pos_ring: window rows and DSpark window rows; ot_mtp_cmp_slot_ring: the ratio-2
// compressor open group; ot_mtp_hist_ring: the Engram token history; compressed rows and index keys
// are linear by group), so the whole rollback is this unit's one broadcast:
//
//   n_set / n_val   = q + 2 + a       the committed position count, to every ring (1 cycle)
//   q_next          = q + 1 + a       the next anchor; the next pending token is ttok[a]
//   squash_v        positions q+2+a .. q+1+g are dead (squash_from .. squash_to): the wavefront /
//                   in-flight kill range for the sequencer (dsfd_mtp_seq), empty when a == g
//   epoch           increments every commit (tags in-flight results of the old pass)
//
// err (sticky): a > g, or an accept outside a pass.  MUT_OFF = 1 (bench mutant): n_val = q + 1 + a and
// q_next = q + a (the next pass re-runs the last committed position over its own state).
// Latency: commit outputs registered 1 cycle after acc_done.
// ---------------------------------------------------------------------------
module ot_mtp_commit #(
    parameter integer PW  = 32,
    parameter integer GW  = 4,
    parameter integer EW  = 8,
    parameter integer MUT_OFF = 0
) (
    input  wire           clk,
    input  wire           rst_n,
    // pass start: anchor q and draft count g (the control loop)
    input  wire           pass_v,
    input  wire [PW-1:0]  pass_q,
    input  wire [GW-1:0]  pass_g,
    // accept result
    input  wire           acc_done,
    input  wire [GW-1:0]  acc_a,
    // prefill / bring-up: set n directly
    input  wire           pre_v,
    input  wire [PW-1:0]  pre_n,
    output reg            n_set,
    output reg  [PW-1:0]  n_val,
    output reg  [PW-1:0]  q_next,
    output reg            squash_v,
    output reg  [PW-1:0]  squash_from,
    output reg  [PW-1:0]  squash_to,
    output reg  [EW-1:0]  epoch,
    output reg            err
);
    reg          in_pass;
    reg [PW-1:0] q;
    reg [GW-1:0] g;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_pass <= 1'b0; q <= 0; g <= 0; n_set <= 1'b0; n_val <= 0; q_next <= 0; squash_v <= 1'b0;
            squash_from <= 0; squash_to <= 0; epoch <= 0; err <= 1'b0;
        end else begin
            n_set <= 1'b0; squash_v <= 1'b0;
            if (pre_v) begin
                n_set <= 1'b1; n_val <= pre_n; q_next <= pre_n - 1'b1;
            end
            if (pass_v) begin
                in_pass <= 1'b1; q <= pass_q; g <= pass_g;
            end else if (acc_done) begin
                if (!in_pass || acc_a > g) err <= 1'b1;
                in_pass <= 1'b0;
                n_set <= 1'b1;
                n_val <= q + 2 + acc_a - (MUT_OFF ? 1 : 0);
                q_next <= q + 1 + acc_a - (MUT_OFF ? 1 : 0);
                squash_v <= (acc_a != g);
                squash_from <= q + 2 + acc_a;
                squash_to <= q + 1 + g;
                epoch <= epoch + 1'b1;
            end
        end
    end
endmodule
