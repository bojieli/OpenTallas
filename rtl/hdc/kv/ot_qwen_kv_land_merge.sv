`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B O4 ROM die, 4-stack full-bandwidth KV fill (ot_qwen_rt_kv_stream4_service): the
// per-TILE LANDING MERGE, the hardened element of the widened landing path (one per tile,
// 1,536 a die, at the landing side of the FILL_LAT network).  Under the 4-stack stream map a
// tile's K/V slice words are written by at most NSRC = 12 beat halves (pseudo-channel ports);
// the merge turns the requests presented this cycle into ONE registered slice write
// (kvw_ce/addr/data/mask, the tile's write port) and grants the requests it took:
//   * a token (stream-unit) write for this tile has priority: no beat is granted;
//   * else the first valid request in rotating port order (rank = port - rr) claims the write
//     (its slice word, loc, is the write's address);
//   * a request is granted iff it is for that word and its lane quarters (q4) overlap no
//     EARLIER valid request for that word (write combining on disjoint lanes).
// The rule is ot_qwen_rt_kv_stream4_service's per-tile arbitration, bit for bit (the service is
// the behavioural model of the 1,536 merges); the grants are flat (no chain: every term is a
// pairwise rank compare), so the depth does not grow with NSRC beyond the reduction trees.
// Source ports are inputs (strapped constants per tile in the die).
// ---------------------------------------------------------------------------
module ot_qwen_kv_land_merge #(
    parameter integer NSRC = 12,
    parameter integer PW   = 7,      // port number bits (128 pseudo-channel ports)
    parameter integer LW   = 7,      // slice word address bits
    parameter integer DW   = 512
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [PW-1:0]        rr,              // rotating priority origin (global)
    input  wire [NSRC-1:0]      s_v,
    input  wire [NSRC*PW-1:0]   s_port,
    input  wire [NSRC*LW-1:0]   s_loc,
    input  wire [NSRC*4-1:0]    s_q4,            // lane quarters the request writes
    input  wire [NSRC*DW-1:0]   s_data,          // already placed in the slice word
    input  wire [NSRC*DW-1:0]   s_mask,
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
    reg [PW-1:0] rank [0:NSRC-1];
    reg [NSRC-1:0] first, same;
    reg [LW-1:0] loc_f;
    reg [DW-1:0] m_data, m_mask;
    integer i, j;
    always @(*) begin
        for (i = 0; i < NSRC; i = i + 1) rank[i] = s_port[i*PW +: PW] - rr;
        loc_f = 0;
        for (i = 0; i < NSRC; i = i + 1) begin
            first[i] = s_v[i];
            for (j = 0; j < NSRC; j = j + 1)
                if (j != i && s_v[j] && rank[j] < rank[i]) first[i] = 1'b0;
            if (first[i]) loc_f = loc_f | s_loc[i*LW +: LW];
        end
        for (i = 0; i < NSRC; i = i + 1) same[i] = s_v[i] && s_loc[i*LW +: LW] == loc_f;
        m_data = 0; m_mask = 0;
        for (i = 0; i < NSRC; i = i + 1) begin
            s_grant[i] = !tok_v && same[i];
            for (j = 0; j < NSRC; j = j + 1)
                if (j != i && same[j] && rank[j] < rank[i] && (s_q4[j*4 +: 4] & s_q4[i*4 +: 4]) != 4'd0) s_grant[i] = 1'b0;
            if (s_grant[i]) begin
                m_data = m_data | s_data[i*DW +: DW];
                m_mask = m_mask | s_mask[i*DW +: DW];
            end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kvw_ce <= 1'b0;
        else kvw_ce <= tok_v || (|s_v);
    always @(posedge clk) begin
        kvw_addr <= tok_v ? tok_loc : loc_f;
        kvw_data <= tok_v ? tok_data : m_data;
        kvw_mask <= tok_v ? tok_mask : m_mask;
    end
endmodule
