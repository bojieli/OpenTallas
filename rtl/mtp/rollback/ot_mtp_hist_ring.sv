`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Engram token-history ring with exact MTP rollback (DS-V4.1 Engram layers L1 / L14; stream
// mtp-rollback 2026-10-08).
//
// The Engram hash of position p reads the NG = engram_max_ngram_size (4) raw token ids of positions
// p, p-1, .., p-NG+1 (golden EngramTables.hashes over state["tokens"][:p+1]; positions below 0 are the
// pad).  In a verify pass the draft tokens d_1 .. d_g are history for positions q+2 .. q+1+g, so after
// a rejection the history must be the committed tokens again.  As built this restore existed only as
// testbench logic ("restored to its snapshot after slot a").
//
// This unit makes it a position-indexed ring: the control loop writes a pass's tokens (y, d_1 .. d_g at
// positions q+1 .. q+1+g) before the pass, a read at p streams NG tokens newest first, and rollback is
// the commit pointer alone (n_set): rejected tokens sit at positions >= n and are overwritten by the next
// pass (which writes its pending token at n first) before any read reaches them.  Exact when
// TR >= NG - 1 + PMAX.  Every read is tag-checked (err, sticky).
//
// MUT_APPEND = 1 (bench mutant only): a history that appends every written token at a running write
// count and never rewinds (an AR history register without the restore).
// Cycles: write 1, read 1 + NG, commit 1, rollback 0.  Storage TR x TW (16 x 17 b) per user.
// ---------------------------------------------------------------------------
module ot_mtp_hist_ring #(
    parameter integer TR   = 16,
    parameter integer NG   = 4,
    parameter integer TW   = 17,
    parameter integer PMAX = 8,
    parameter integer PW   = 32,
    parameter integer MUT_APPEND = 0
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           n_set,
    input  wire [PW-1:0]  n_val,
    input  wire           tw_v,
    input  wire [PW-1:0]  tw_pos,
    input  wire [TW-1:0]  tw_tok,
    input  wire           rd_v,
    output wire           rd_ready,
    input  wire [PW-1:0]  rd_pos,
    output reg            h_v,
    output reg  [TW-1:0]  h_tok,
    output reg            h_pad,
    output reg            h_last,
    output reg            err
);
    localparam integer TB = $clog2(TR);
    initial if ((1 << TB) != TR || TR < NG - 1 + PMAX)
        $fatal(1, "ot_mtp_hist_ring: TR must be a power of two >= NG - 1 + PMAX");

    reg [TW-1:0] mem [0:TR-1];
    reg [PW-1:0] tag [0:TR-1];
    reg          tv  [0:TR-1];
    reg [PW-1:0] n, wcount;
    reg          busy;
    reg [PW-1:0] p_q;
    reg [$clog2(NG+1)-1:0] k;
    integer i;
    assign rd_ready = !busy;

    wire [PW-1:0] wslot_pos = MUT_APPEND ? wcount : tw_pos;
    wire [PW-1:0] rp = p_q - k;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; wcount <= 0; err <= 1'b0; busy <= 1'b0; h_v <= 1'b0; h_last <= 1'b0; h_pad <= 1'b0; h_tok <= 0;
            for (i = 0; i < TR; i = i + 1) tv[i] <= 1'b0;
        end else begin
            h_v <= 1'b0; h_last <= 1'b0; h_pad <= 1'b0;
            if (n_set) n <= n_val;
            if (tw_v) begin
                mem[wslot_pos[TB-1:0]] <= tw_tok;
                tag[wslot_pos[TB-1:0]] <= MUT_APPEND ? tw_pos : wslot_pos;
                tv[wslot_pos[TB-1:0]]  <= 1'b1;
                wcount <= wcount + 1'b1;
                if (!MUT_APPEND && ($signed(tw_pos - n) >= PMAX || $signed(tw_pos - n) < -(TR - PMAX))) err <= 1'b1;
            end
            if (!busy && rd_v) begin
                busy <= 1'b1; p_q <= rd_pos; k <= 0;
            end else if (busy) begin
                h_v <= 1'b1;
                if ($signed(rp) < 0) begin h_pad <= 1'b1; h_tok <= 0; end
                else begin
                    h_tok <= mem[rp[TB-1:0]];
                    if (!MUT_APPEND && (!tv[rp[TB-1:0]] || tag[rp[TB-1:0]] != rp)) err <= 1'b1;
                end
                if (k == NG - 1) begin busy <= 1'b0; h_last <= 1'b1; end
                else k <= k + 1'b1;
            end
        end
    end
endmodule
