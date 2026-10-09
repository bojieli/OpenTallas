`timescale 1ns/1ps
// Per-pseudo-channel embedding port (emb-hbm 2026-10-08), in the controller band beside qfd_ctrl_emb_<pc>, HBM
// controller clock, between the controller / PHY and the PC's core-clock crossing (qfd_cdc).  It owns the ECC of the
// stored copy: every embedding sector is 256 data + 32 check bits = four SECDED(72,64) words in the HBM3E ECC side-band
// (ot_qfd_emb_pkg enc256: the KV path's / near-HBM row client's SECDED72 bit layout).
//   * class: the PHY returns a PC's read data in RD issue order, so every RD the controller issues (col_v && !col_we,
//     registered outputs of ot_qwen_ctrl_pc_emb) pushes its class (col_sr: static = embedding, else the KV stream)
//     into an RQD-entry in-order FIFO and every returned beat (r_v, 288 b) pops it;
//   * KV beats leave unchanged on the KV landing path (kv_v / kv_d, from flops);
//   * embedding beats are decoded in two registered stages (SECDED72 syndromes, then correction) and leave toward the
//     strip engine as {ue, ce, data 256} (em_v / em_d): ce = a single-bit error corrected, ue = uncorrectable;
//   * static WRITE data (the boot load, 256 b) arrives from the strip engine with its command (w_v / w_d), is encoded
//     (enc256) into a WQD-entry FIFO whose head is the PHY write data of the next static WR (col_v && col_we && col_sr).
// Faults (sticky): a beat with no RD outstanding, class FIFO overflow, a static WR with no data, write FIFO overflow.
// MUT = 3 (bench mutant, must FAIL): the correction is skipped (the raw data bits pass, nothing flagged).
// KVW = 1 (sys-takeover 2026-10-09, opt-in; registry qfd_hbm_ecc_provider): the ECC provider for the MUTABLE KV payload.
//   KV write data (kw_v / kw_d, 256 b, with its KV WR command, same credit discipline as w_v) is encoded here into the
//   HBM3E ECC side-band (enc256: 32 check bits per 256, the layout ot_qfd_kv_landing_ecc decodes) into a KWQD FIFO whose
//   head is the PHY write data of the next KV WR (col_v && col_we && !col_sr); wd = col_sr ? static head : KV head.
//   KV reads already leave as the full 288-b codeword (kv_d) and are corrected by ot_qfd_kv_landing_ecc.  No in-band
//   cost: 0 cycles, +KWQD x 288 flops.  Faults: KV WR with no data, KV write FIFO overflow.
// MUT = 4 / 5 (bench mutants): KV write check column 0 wrong / KV write side-band dropped (check bits 0).
module ot_qfd_emb_pcport #(
    parameter integer RQD = 32,
    parameter integer WQD = 4,
    parameter integer MUT = 0,
    parameter integer KVW = 0,
    parameter integer KWQD = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         col_v,
    input  wire         col_we,
    input  wire         col_sr,
    input  wire         w_v,
    input  wire [255:0] w_d,
    output wire [287:0] wd,               // the PHY write data of the next static WR (FIFO head); KVW: of the next WR
    input  wire         kw_v,             // KVW: KV write data (256 b), one per KV WR command
    input  wire [255:0] kw_d,
    input  wire         r_v,
    input  wire [287:0] r_d,
    output reg          kv_v,
    output reg  [287:0] kv_d,
    output reg          em_v,
    output reg  [257:0] em_d,             // {ue, ce, data}
    output reg          fault
);
    import ot_qfd_emb_pkg::*;
    localparam integer RA = $clog2(RQD);
    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;
    reg [RQD-1:0] kq;
    reg [RA:0] kw, kr;
    reg [287:0] wq [0:WQD-1];
    reg [WA:0] ww, wr;
    wire rd_issue = col_v && !col_we;
    wire wr_static = col_v && col_we && col_sr;
    wire k_empty = kw == kr;
    wire k_full = (kw[RA-1:0] == kr[RA-1:0]) && (kw[RA] != kr[RA]);
    wire w_empty = ww == wr;
    wire w_full = (ww[WA-1:0] == wr[WA-1:0]) && (ww[WA] != wr[WA]);
    wire cls = kq[kr[RA-1:0]];
    localparam integer KA = (KWQD > 1) ? $clog2(KWQD) : 1;
    reg [287:0] kq_w [0:KWQD-1];
    reg [KA:0] kww, kwr;
    wire wr_kv = col_v && col_we && !col_sr;
    wire kw_empty = kww == kwr;
    wire kw_full = (kww[KA-1:0] == kwr[KA-1:0]) && (kww[KA] != kwr[KA]);
    assign wd = (KVW != 0 && !col_sr) ? kq_w[kwr[KA-1:0]] : wq[wr[WA-1:0]];
    function automatic [287:0] kenc(input [255:0] x);
        reg [287:0] c;
        begin
            c = enc256(x);
            if (MUT == 4) c[0] = ~c[0];          // check column 0 of word 0 wrong
            if (MUT == 5) begin c[0] = 1'b0; c[1] = 1'b0; c[3] = 1'b0; c[7] = 1'b0; c[15] = 1'b0; c[31] = 1'b0; c[63] = 1'b0; c[71] = 1'b0; end
            kenc = c;
        end
    endfunction
    always @(posedge clk) if (KVW != 0 && kw_v) kq_w[kww[KA-1:0]] <= kenc(kw_d);
    // decode pipe: stage 1 raw + syndromes, stage 2 corrected
    reg v1; reg [287:0] c1; reg [31:0] y1;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            kw <= 0; kr <= 0; ww <= 0; wr <= 0; kww <= 0; kwr <= 0; kv_v <= 1'b0; em_v <= 1'b0; v1 <= 1'b0; fault <= 1'b0;
        end else begin
            if (rd_issue) begin kw <= kw + 1'b1; if (k_full) fault <= 1'b1; end
            if (r_v) begin kr <= kr + 1'b1; if (k_empty) fault <= 1'b1; end
            kv_v <= r_v && !cls;
            v1 <= r_v && cls;
            em_v <= v1;
            if (w_v) begin ww <= ww + 1'b1; if (w_full) fault <= 1'b1; end
            if (wr_static) begin wr <= wr + 1'b1; if (w_empty) fault <= 1'b1; end
            if (KVW != 0 && kw_v) begin kww <= kww + 1'b1; if (kw_full) fault <= 1'b1; end
            if (KVW != 0 && wr_kv) begin kwr <= kwr + 1'b1; if (kw_empty) fault <= 1'b1; end
        end
    always @(posedge clk) begin : dp
        reg [65:0] dc; reg ue, ce; reg [255:0] d;
        if (rd_issue) kq[kw[RA-1:0]] <= col_sr;
        if (w_v) wq[ww[WA-1:0]] <= enc256(w_d);
        if (r_v) begin
            kv_d <= r_d; c1 <= r_d;
            for (i = 0; i < 4; i = i + 1) y1[i*8 +: 8] <= syn64(r_d[i*72 +: 72]);
        end
        ue = 1'b0; ce = 1'b0;
        for (i = 0; i < 4; i = i + 1) begin
            dc = cor64(c1[i*72 +: 72], (MUT == 3) ? 8'd0 : y1[i*8 +: 8]);
            d[i*64 +: 64] = dc[63:0]; ue = ue | dc[65]; ce = ce | dc[64];
        end
        if (v1) em_d <= {ue, ce, d};
    end
endmodule
