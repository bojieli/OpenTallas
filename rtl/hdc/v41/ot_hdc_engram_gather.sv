`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Engram row gather and prefetch of the V4.1 decode core, at shipped scale.
//
// ROLE.  The Engram rows of a token are addressed by its compressed id alone,
// which is known when the decode step starts, so the rows are fetched ahead of
// the Engram layers (1 and 14) that consume them.  This unit takes the hash
// unit's row addresses for one token (ENG_LAYERS x ENG_COLS = 48 of them), issues
// one read to each COLUMN BANK of the table ROM, decodes the returned FP8 rows to
// BF16 and writes them into a double-buffered prefetch buffer that the Engram
// layers read.  tools/hdc_v41_engram_rom_plan.py documents the ROM organisation.
//
// ROM ORGANISATION (why the banks never conflict).  Hash column c of layer l
// indexes only its own region of the table, [offset_c, offset_c + prime_c), so
// the ROM is banked by column: bank b = l*ENG_COLS + c holds prime_c rows and
// is addressed by the residue (row - offset_c, ENG_RES_W bits).  Every token
// reads exactly one row from every bank, so the 48 reads of a token are
// conflict free by construction and are issued in one cycle.
//
// BANK INTERFACE.  Per bank: a request channel (valid/ready, residue address,
// 1-bit slot tag) and a response channel (valid/ready, 264-bit beat, echoed
// tag).  A row returns as 8 beats IN ORDER per bank; banks are independent and
// may answer in any order and with any latency.  Beat k carries codes
// 32k .. 32k+31 (code i of the beat at [8i +: 8]) and a side byte at [263:256]
// that is the row's UE8M0 scale on beat 0 and ignored on beats 1..7 (the 264-byte
// packed row of the release: 256 E4M3 codes, the scale and 7 pad bytes).
//
// DECODE (tools/hdc_golden_v41.Model.engram_layer, bit for bit).  Each code is
// E4M3 (E4M3fn, bias 7, subnormals, 0x7F/0xFF NaN) times 2^(scale - 127):
// rows = to_bf16((E4M3[codes] * np.exp2(sc)).astype(float32)).  The product has
// at most 4 significant bits and its binary32 cast is exact, so the result is
// one round-to-nearest-even into BF16: normal results are exact, results below
// 2^-126 round at 2^-133 (at most 3 bits drop), results at or above 2^128 are
// +-inf, zero keeps its sign, a NaN code gives the golden's 0x7FC0 / 0xFFC0.
// Every scale byte 0..255 is inside the contract (255 is 2^128, as the golden's
// exp2 computes it).
//
// PREFETCH BUFFER (outside the unit, an SRAM).  Per layer one write port of
// 32 BF16 (512 bits) per cycle at address {slot, column, beat}; word k of
// column c holds elements 32k .. 32k+31 of that row.  Two slots: token t lands
// in slot t mod 2, so token t+1's rows are fetched while the layers still read
// token t's.  rdy[s*ENG_LAYERS + l] rises when every row of layer l of the
// token in slot s has been written (the edge after the last write commits);
// the consumer frees a slot with rel_valid/rel_slot when it no longer needs it.
//
// FLOW.  in_valid/in_ready take one token's row addresses; in_ready needs the
// next slot free and every bank's previous request accepted.  One response
// port per layer: a round-robin arbiter over the layer's 24 banks takes one
// beat per cycle (the 192 beats of a layer's rows stream in 192 cycles), a
// register stage, a 32-lane decode stage, the buffer write.  Latency from
// accept to rdy with banks of fixed latency L and no stalls: 3 + L + 192 + 2.
// ---------------------------------------------------------------------------
import ot_hdc_engram_tables_shipped_pkg::*;

module ot_hdc_engram_gather #(
    parameter integer NL    = ENG_LAYERS,
    parameter integer NC    = ENG_COLS,
    parameter integer ROW_W = ENG_ROW_W,
    parameter integer AW    = ENG_RES_W,
    parameter integer BEATS = 8,
    parameter integer LANES = 32,
    parameter [ROW_W*NL*NC-1:0] OFFSETS = ENG_OFFSET,
    parameter integer NB    = NL * NC,
    parameter integer DW    = 8 * LANES + 8,          // beat: side byte + LANES codes
    parameter integer CW    = $clog2(NC),
    parameter integer BTW   = $clog2(BEATS),
    parameter integer BAW   = 1 + CW + BTW            // buffer address {slot, column, beat}
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // one token's row addresses (hash unit order: [ROW_W*(l*NC + c) +: ROW_W])
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire [NB*ROW_W-1:0]   in_row,
    output reg                   in_slot,             // slot the next accepted token lands in
    // column banks
    output wire [NB-1:0]         req_valid,
    input  wire [NB-1:0]         req_ready,
    output wire [NB*AW-1:0]      req_addr,
    output wire [NB-1:0]         req_tag,
    input  wire [NB-1:0]         rsp_valid,
    output wire [NB-1:0]         rsp_ready,
    input  wire [NB*DW-1:0]      rsp_data,
    input  wire [NB-1:0]         rsp_tag,
    // prefetch buffer write ports, one per layer
    output reg  [NL-1:0]         wr_en,
    output reg  [NL*BAW-1:0]     wr_addr,
    output reg  [NL*16*LANES-1:0] wr_data,
    // status and release
    output wire [2*NL-1:0]       rdy,
    input  wire                  rel_valid,
    input  wire                  rel_slot
);
    localparam integer TOT  = NC * BEATS;             // beats per layer per token
    localparam integer TW   = $clog2(TOT + 1);
    localparam [TW-1:0] TOTV = TOT;

    // -- slots ------------------------------------------------------------------------
    reg  [1:0]    busy;
    reg  [NB-1:0] pend;
    reg  [NB*AW-1:0] raddr;
    reg  [NB-1:0] rtag;
    assign in_ready = !busy[in_slot] && (pend == {NB{1'b0}});
    wire acc = in_valid && in_ready;
    assign req_valid = pend;
    assign req_addr  = raddr;
    assign req_tag   = rtag;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 2'b00; pend <= {NB{1'b0}}; in_slot <= 1'b0;
        end else begin
            pend <= (pend & ~req_ready) | (acc ? {NB{1'b1}} : {NB{1'b0}});
            if (acc) in_slot <= ~in_slot;
            if (rel_valid) busy[rel_slot] <= 1'b0;
            if (acc) busy[in_slot] <= 1'b1;
        end
    end
    genvar gb;
    generate
        for (gb = 0; gb < NB; gb = gb + 1) begin : g_bank
            localparam [ROW_W-1:0] OFF = OFFSETS[ROW_W*gb +: ROW_W];
            wire [ROW_W-1:0] local_row = in_row[ROW_W*gb +: ROW_W] - OFF;
            always @(posedge clk) if (acc) begin
                raddr[AW*gb +: AW] <= local_row[AW-1:0];
                rtag[gb] <= in_slot;
            end
        end
    endgenerate

    // -- per layer: arbitrate, register, decode, write -------------------------------
    genvar gl, gc, gq;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_layer
            wire [NC-1:0] v = rsp_valid[NC*gl +: NC];
            reg  [CW-1:0] rr;                          // round-robin pointer: lowest priority last grant
            // grant: first valid bank at or after rr + 1, wrapping
            reg  [CW-1:0] gsel;
            reg           gany;
            integer k, j;
            always @(*) begin
                gsel = {CW{1'b0}}; gany = 1'b0;
                for (k = NC - 1; k >= 0; k = k - 1) begin
                    j = (rr + 1 + k) % NC;
                    if (v[j]) begin gsel = j[CW-1:0]; gany = 1'b1; end
                end
            end
            for (gc = 0; gc < NC; gc = gc + 1) begin : g_rdy
                assign rsp_ready[NC*gl + gc] = gany && (gsel == gc);
            end
            // per-bank beat counter and latched scale
            reg [BTW-1:0] bcnt [0:NC-1];
            reg [7:0]     scl  [0:NC-1];
            wire [DW-1:0] gdata = rsp_data[DW*(NC*gl + gsel) +: DW];
            wire          gtag  = rsp_tag[NC*gl + gsel];
            wire [BTW-1:0] gbeat = bcnt[gsel];
            wire [7:0]    gscale = (gbeat == 0) ? gdata[DW-1 -: 8] : scl[gsel];
            integer c;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    rr <= NC - 1;
                    for (c = 0; c < NC; c = c + 1) bcnt[c] <= {BTW{1'b0}};
                end else if (gany) begin
                    rr <= gsel;
                    bcnt[gsel] <= bcnt[gsel] + 1'b1;
                end
            end
            always @(posedge clk) if (gany && gbeat == 0) scl[gsel] <= gdata[DW-1 -: 8];
            // stage 1
            reg              s1_v;
            reg [BAW-1:0]    s1_a;
            reg [7:0]        s1_s;
            reg [8*LANES-1:0] s1_c;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) s1_v <= 1'b0;
                else s1_v <= gany;
            end
            always @(posedge clk) if (gany) begin
                s1_a <= {gtag, gsel, gbeat};
                s1_s <= gscale;
                s1_c <= gdata[8*LANES-1:0];
            end
            // stage 2: decode, buffer write
            wire [16*LANES-1:0] dec;
            for (gq = 0; gq < LANES; gq = gq + 1) begin : g_dec
                ot_hdc_engram_e4m3_bf16 u_dec (.code(s1_c[8*gq +: 8]), .scale(s1_s), .bf16(dec[16*gq +: 16]));
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) wr_en[gl] <= 1'b0;
                else wr_en[gl] <= s1_v;
            end
            always @(posedge clk) if (s1_v) begin
                wr_addr[BAW*gl +: BAW] <= s1_a;
                wr_data[16*LANES*gl +: 16*LANES] <= dec;
            end
            // completion: counted on the edge the buffer commits the write
            wire wslot = wr_addr[BAW*gl + BAW - 1];
            reg [TW-1:0] cnt0, cnt1;                   // beats written for slot 0 / 1
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    cnt0 <= {TW{1'b0}}; cnt1 <= {TW{1'b0}};
                end else begin
                    if (acc && !in_slot) cnt0 <= {TW{1'b0}};
                    else if (wr_en[gl] && !wslot) cnt0 <= cnt0 + 1'b1;
                    if (acc && in_slot) cnt1 <= {TW{1'b0}};
                    else if (wr_en[gl] && wslot) cnt1 <= cnt1 + 1'b1;
                end
            end
            assign rdy[gl]      = busy[0] && cnt0 == TOTV;
            assign rdy[NL + gl] = busy[1] && cnt1 == TOTV;
        end
    endgenerate
endmodule


// E4M3 code times 2^(scale - 127), rounded to BF16 (see the header of ot_hdc_engram_gather).
module ot_hdc_engram_e4m3_bf16 (
    input  wire [7:0]  code,
    input  wire [7:0]  scale,
    output reg  [15:0] bf16
);
    wire       s = code[7];
    wire [3:0] e = code[6:3];
    wire [2:0] m = code[2:0];
    wire [3:0] sig = (e != 0) ? {1'b1, m} : {1'b0, m};
    // E: exponent of the significand's unit bit; value = sig * 2^E
    wire signed [10:0] E = (e != 0) ? $signed({7'd0, e}) - 11'sd137 + $signed({3'd0, scale})
                                    : -11'sd136 + $signed({3'd0, scale});
    wire [1:0] p = sig[3] ? 2'd3 : sig[2] ? 2'd2 : sig[1] ? 2'd1 : 2'd0;
    wire signed [10:0] X = E + $signed({9'd0, p});
    wire [3:0] nrm = sig << (2'd3 - p);               // 1.fff
    wire [7:0] xb = X[7:0] + 8'd127;
    wire signed [10:0] k = E + 11'sd133;              // >= -3 on every code and scale
    wire [1:0] r = (k < 0) ? (~k[1:0] + 2'd1) : 2'd0; // -k for k in -3..-1
    wire [3:0] q = sig >> r;
    wire [3:0] rem = sig & ((4'd1 << r) - 4'd1);
    wire [3:0] half = (r == 0) ? 4'd0 : (4'd1 << (r - 2'd1));
    wire       up = (r != 0) && ((rem > half) || (rem == half && q[0]));
    wire [7:0] sub = (k >= 0) ? ({4'd0, sig} << k[2:0]) : ({4'd0, q} + {7'd0, up});
    always @(*) begin
        if (e == 4'hF && m == 3'h7)        bf16 = {s, 15'h7FC0};
        else if (sig == 0)                 bf16 = {s, 15'd0};
        else if (X > 11'sd127)             bf16 = {s, 8'hFF, 7'd0};
        else if (X >= -11'sd126)           bf16 = {s, xb, nrm[2:0], 4'd0};
        else                               bf16 = {s, 7'd0, sub};
    end
endmodule
