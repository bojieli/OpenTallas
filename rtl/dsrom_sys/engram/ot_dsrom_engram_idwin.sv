`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM Engram n-gram window former, on the S0 (embedding) rank dies, where
// each decode token's id first exists in the array.  It is the ONLY Engram
// state in the array: the home dies' lookup engines are stateless (the window
// travels in the lead flit), so an MTP rollback touches this block only.
//
// It is the hardware form of the official NgramHashState (inference/engram.py)
// for decode: per user slot it keeps the recent compressed ids and their DEAD
// flags (an image-span token is cached as DEAD), and for every token emits the
// window w0..w3 (w0 = this token) with the official blocking rule:
//
//     blocked_k = blocked_(k-1) | (pos < k) | (source_k == DEAD),  blocked_-1 = 0
//     w_k       = blocked_k ? pad : source_k
//
// pos < k is "fewer than k earlier tokens in this sequence" (t_first starts a
// sequence at position 0).
//
// MTP HISTORY RESTORE.  A verify step pushes gamma+1 tokens of a user (the
// committed one and the drafts); when the verifier rejects the last n of them,
// rb_valid / rb_user / rb_n rewinds that user's history by n -- exactly the
// official cache truncated to the accepted prefix.  The history is a ring of
// HD = 8 entries a user (3 look-back + up to 5 rejected drafts), so the ids
// that the rejected drafts pushed out of the 3-deep window are still there.
// The position count saturates at 15: after a rewind of at most 5 it is still
// >= 3 whenever the true position is, so the pos < k test stays exact.  A
// rewind and a token of the same user never share a cycle (the commit
// sequencer orders them); a rewind takes 1 cycle.
//
// The window travels as the Engram LEAD FLIT to the home stages (4 x 17 bits +
// dead); win_dead (this token is DEAD) tells the consumer to close the gate
// (token_mask), as the official forward does.  The compressed-id map (129,280
// tokenizer ids -> 99,092) sits in front of t_cid in the embedding row
// reader's ROM.  One token a cycle, 1-cycle latency, registered outputs.
// ---------------------------------------------------------------------------
module ot_dsrom_engram_idwin #(
    parameter integer NUSER = 64,
    parameter integer ID_W  = 17,
    parameter [ID_W-1:0] PAD = 17'd2,
    parameter integer UW    = (NUSER > 1) ? $clog2(NUSER) : 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 t_valid,
    input  wire [UW-1:0]        t_user,
    input  wire [ID_W-1:0]      t_cid,
    input  wire                 t_first,
    input  wire                 t_dead,
    // MTP rejected-draft rewind
    input  wire                 rb_valid,
    input  wire [UW-1:0]        rb_user,
    input  wire [2:0]           rb_n,
    output reg                  win_valid,
    output reg  [4*ID_W-1:0]    win_ids,     // w0 at [ID_W-1:0] .. w3 at the top
    output reg                  win_dead
);
    localparam integer HD = 8;
    reg [ID_W-1:0] hid [0:NUSER*HD-1];
    reg            hdd [0:NUSER*HD-1];
    reg [3*NUSER-1:0] wp;                    // next write slot per user (reset 0)
    reg [4*NUSER-1:0] np;                    // earlier tokens in the sequence, saturating at 15
    wire [3:0]     n   = t_first ? 4'd0 : np[4*t_user +: 4];
    wire [2:0]     p   = wp[3*t_user +: 3];
    wire [2:0]     rwp = wp[3*rb_user +: 3];
    wire [3:0]     rnp = np[4*rb_user +: 4];
    wire [UW+2:0]  a1  = {t_user, p - 3'd1}, a2 = {t_user, p - 3'd2}, a3 = {t_user, p - 3'd3};
    wire           b0 = t_dead;
    wire           b1 = b0 | (n < 4'd1) | hdd[a1];
    wire           b2 = b1 | (n < 4'd2) | hdd[a2];
    wire           b3 = b2 | (n < 4'd3) | hdd[a3];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin win_valid <= 1'b0; wp <= {3*NUSER{1'b0}}; np <= {4*NUSER{1'b0}}; end
        else begin
            win_valid <= t_valid;
            if (t_valid) begin
                wp[3*t_user +: 3] <= p + 3'd1;
                np[4*t_user +: 4] <= (n == 4'd15) ? 4'd15 : n + 4'd1;
            end
            if (rb_valid) begin
                wp[3*rb_user +: 3] <= rwp - rb_n;
                np[4*rb_user +: 4] <= rnp - {1'b0, rb_n};
            end
        end
    end
    always @(posedge clk) begin
        if (t_valid) begin
            win_ids <= {b3 ? PAD : hid[a3], b2 ? PAD : hid[a2], b1 ? PAD : hid[a1], b0 ? PAD : t_cid};
            win_dead <= t_dead;
            hid[{t_user, p}] <= t_cid;
            hdd[{t_user, p}] <= t_dead;
        end
    end
endmodule
