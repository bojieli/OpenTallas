`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die, 4-stack full-bandwidth KV fill (ot_qwen_rt_kv_stream4_service): the
// per-TILE LANDING MERGE, the hardened element of the widened landing path (one per tile,
// 1,536 a die, at the landing side of the FILL_LAT network).  Under the 4-stack stream map a
// tile's K/V slice words are written by at most NSRC = 12 beat halves (pseudo-channel ports);
// the merge grants the requests presented this cycle and turns them into ONE slice write
// (kvw_ce/addr/data/mask, the tile's write port):
//   * a token (stream-unit) write for this tile has priority: no beat is granted;
//   * else the first valid request in rotating port order (rank = port - rr) claims the write
//     (its slice word, loc, is the write's address);
//   * a request is granted iff it is for that word and its lane quarters overlap no
//     EARLIER valid request for that word (write combining on disjoint lanes).
// The rule is ot_qwen_rt_kv_stream4_service's per-tile arbitration, bit for bit (the service is
// the behavioural model of the 1,536 merges).  Each source presents the landed beat as the
// landing ring holds it (256 bits; a V half in the low 128) with its placement: K beat (s_isk):
// 256 bits at quarter s_sel (0 or 2), lanes masked by the open tile's tail mask tail_lm when
// s_ktail; V half: 128 bits at quarter s_sel.  Source ports are strapped constants per tile.
//
// Timing structure (r2): the rotating order is REGISTERED (rr_n is the next cycle's origin: the
// order matrix E[j][i] = "j before i" is computed a cycle ahead), slice-word equality is pairwise
// (no first -> loc -> compare chain), so the grant is ~4 flat AND-OR levels from s_v/s_loc; the
// granted beats are registered with their placement and the slice word is formed and written in
// the second stage (kvw_* two edges after the request: one of the FILL_LAT network stages).
// ---------------------------------------------------------------------------
module ot_qwen_kv_land_merge #(
    parameter integer NSRC = 12,
    parameter integer PW   = 7,      // port number bits (128 pseudo-channel ports)
    parameter integer LW   = 7,      // slice word address bits
    parameter integer DW   = 512
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [PW-1:0]        rr_n,            // rotating priority origin of the NEXT cycle
    input  wire [NSRC-1:0]      s_v,
    input  wire [NSRC*PW-1:0]   s_port,
    input  wire [NSRC*LW-1:0]   s_loc,
    input  wire [NSRC-1:0]      s_isk,           // K beat (else a V half)
    input  wire [NSRC-1:0]      s_ktail,         // K beat of the open tile: lanes masked by tail_lm
    input  wire [NSRC*2-1:0]    s_sel,           // quarter the beat is placed at
    input  wire [NSRC*256-1:0]  s_beat,
    input  wire [127:0]         tail_lm,         // lanes < P mod 16 of the open K tile
    output reg  [NSRC-1:0]      s_grant,
    input  wire                 tok_v,
    input  wire [LW-1:0]        tok_loc,
    input  wire [DW-1:0]        tok_data,
    input  wire [DW-1:0]        tok_mask,
    output reg                  kvw_ce,
    output reg  [LW-1:0]        kvw_addr,
    output reg  [DW-1:0]        kvw_data,
    output reg  [DW-1:0]        kvw_mask
);
    integer i, j;
    // ---- order matrix, one cycle ahead ----------------------------------------------------
    reg [NSRC-1:0] E [0:NSRC-1];                 // E[j][i]: source j precedes source i this cycle
    always @(posedge clk) begin
        for (j = 0; j < NSRC; j = j + 1)
            for (i = 0; i < NSRC; i = i + 1)
                E[j][i] <= (j != i) && (PW'(s_port[j*PW +: PW] - rr_n) < PW'(s_port[i*PW +: PW] - rr_n));
    end
    // ---- stage 1: grants ------------------------------------------------------------------
    // the open tile's mask is static for a layer: its non-zero flag is registered once (r3)
    reg tail_nz;
    always @(posedge clk) tail_nz <= |tail_lm;
    reg [3:0] q4 [0:NSRC-1];
    reg [NSRC-1:0] first, same, L [0:NSRC-1];
    reg [LW-1:0] loc_f;
    always @(*) begin
        for (i = 0; i < NSRC; i = i + 1) begin
            // lane quarters: K = two quarters at sel (empty if the tail mask is empty), V = one
            if (s_isk[i]) q4[i] = (s_ktail[i] && !tail_nz) ? 4'd0 : (4'b0011 << s_sel[i*2 +: 2]);
            else q4[i] = 4'b0001 << s_sel[i*2 +: 2];
        end
        for (i = 0; i < NSRC; i = i + 1)
            for (j = 0; j < NSRC; j = j + 1) L[i][j] = s_loc[i*LW +: LW] == s_loc[j*LW +: LW];
        loc_f = 0;
        for (i = 0; i < NSRC; i = i + 1) begin
            first[i] = s_v[i];
            for (j = 0; j < NSRC; j = j + 1) if (s_v[j] && E[j][i]) first[i] = 1'b0;
            if (first[i]) loc_f = loc_f | s_loc[i*LW +: LW];
        end
        for (i = 0; i < NSRC; i = i + 1) same[i] = s_v[i] && (|(first & L[i]));
        for (i = 0; i < NSRC; i = i + 1) begin
            s_grant[i] = !tok_v && same[i];
            for (j = 0; j < NSRC; j = j + 1)
                // same[i] && same[j] <=> same[i] && v_j && loc_j == loc_i: no first -> same chain on this term
                if (s_v[j] && L[i][j] && E[j][i] && (q4[j] & q4[i]) != 4'd0) s_grant[i] = 1'b0;
        end
    end
    // ---- stage 2: the granted beats, registered, become one slice write ----------------------
    reg [NSRC-1:0] g_q, isk_q, kt_q; reg [NSRC*2-1:0] sel_q; reg [NSRC*256-1:0] beat_q; reg [127:0] lm_q;
    reg tok_q, ce_q; reg [LW-1:0] loc_q; reg [DW-1:0] tokd_q, tokm_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ce_q <= 1'b0; kvw_ce <= 1'b0; end
        else begin ce_q <= tok_v || (|s_v); kvw_ce <= ce_q; end
    always @(posedge clk) begin
        g_q <= s_grant; isk_q <= s_isk; kt_q <= s_ktail; sel_q <= s_sel; lm_q <= tail_lm;
        beat_q <= s_beat;                    // unconditional: the grant is not an enable of 3k flops
        tok_q <= tok_v; loc_q <= tok_v ? tok_loc : loc_f;
        if (tok_v) begin tokd_q <= tok_data; tokm_q <= tok_mask; end
    end
    reg [DW-1:0] m_data, m_mask;
    always @(*) begin
        m_data = 0; m_mask = 0;
        for (i = 0; i < NSRC; i = i + 1) if (g_q[i]) begin
            reg [127:0] lm; reg [1:0] sl;
            sl = sel_q[i*2 +: 2];
            lm = kt_q[i] ? lm_q : {128{1'b1}};
            if (isk_q[i]) begin
                m_data = m_data | ({256'd0, beat_q[i*256 +: 256]} << (128 * sl));
                m_mask = m_mask | ({256'd0, lm, lm} << (128 * sl));
            end else begin
                m_data = m_data | ({384'd0, beat_q[i*256 +: 128]} << (128 * sl));
                m_mask = m_mask | ({384'd0, {128{1'b1}}} << (128 * sl));
            end
        end
    end
    always @(posedge clk) begin
        kvw_addr <= loc_q;
        kvw_data <= tok_q ? tokd_q : m_data;
        kvw_mask <= tok_q ? tokm_q : m_mask;
    end
endmodule
