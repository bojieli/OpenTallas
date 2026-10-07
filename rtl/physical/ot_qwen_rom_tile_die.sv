`timescale 1ns/1ps
// Qwen ROM die TILE master (r21 qfd_tile / qfd_tile_e, 1,536 copies): the W12 ROM tile (ot_qwen_rom_tile_w12, 10 ROM
// macros + 8 KiB KV slice) plus its per-tile landing-fabric hop (r19 "KV reconciliation": KVL_BITS = 768 a row, one
// hop a tile) and the per-tile landing merge (ot_qwen_kv_land_merge, the hardened element the stream4 service models).
// Row landing word (768 b, emitted by the stack's qfd_kvc landing crossbar; the row bus is slot-scheduled there):
//   slot k (k < LSLOTS = 2) at [k*SLW +: SLW], SLW = 281:
//     {col[5:0], v, port[6:0], loc[6:0], isk, ktail, sel[1:0], beat[255:0]}   (MSB .. LSB)
//   rr_n[6:0]     at [LSLOTS*SLW +: 7]       rotating merge origin of the next cycle (row-global)
//   tail_lm[127:0] at [LSLOTS*SLW + 7 +: 128]  lanes < P mod 16 of the open K tile (row-global)
//   the remaining 71 bits pass the hop unused.
// A slot is this tile's when v and col == tile_id[5:0] (static strap).  Margin rule: register-to-register boundary.
//   li -> li_q (W pin register) -> lo_q (E pin register, kept copy) -> lo: TWO cycles a tile hop (the 267 um tile
//   width does not fit one SS cycle with a 150 ps inter-region pin budget); priced in the Qwen record.
//   li_q slots -> ot_qwen_kv_land_merge (NSRC = LSLOTS) -> registered kvw_* -> the tile's KV write port.
//   A slot presented but not granted (a crossbar schedule violation) is never dropped silently: it raises a
//   registered land_fault, OR-ed with the tile fault into the registered fault pin (+1 cycle fault latency).
module ot_qwen_rom_tile_die #(
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer SMIN = 6,
    parameter integer CODE_BANKS = 10,
    parameter integer KV_VB = 262144,
    parameter integer KV_NH = 4,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer KVL = 768,
    parameter integer LSLOTS = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [3*NW+13*24+13-1:0] ib,
    input  wire [4*32-1:0]   xl,
    output wire [16*32-1:0]  t_out,
    output wire              t_vout,
    input  wire [16*32-1:0]  n_a,
    input  wire [16*32-1:0]  n_b,
    input  wire              n_va,
    output wire [16*32-1:0]  n_y,
    output wire              n_vy,
    output wire              fault,
    input  wire [KVL-1:0]    li,
    output wire [KVL-1:0]    lo
);
    localparam integer SLW = 281;
    // ---- landing hop: W pin register, E pin register ---------------------------------------------------------------
    (* keep *) reg [KVL-1:0] li_q;
    (* keep *) reg [KVL-1:0] lo_q;
    always @(posedge clk) begin li_q <= li; lo_q <= li_q; end
    assign lo = lo_q;
    // ---- slot decode -----------------------------------------------------------------------------------------------
    wire [LSLOTS-1:0]     s_v;
    wire [LSLOTS*7-1:0]   s_port, s_loc;
    wire [LSLOTS-1:0]     s_isk, s_ktail;
    wire [LSLOTS*2-1:0]   s_sel;
    wire [LSLOTS*256-1:0] s_beat;
    genvar k;
    generate for (k = 0; k < LSLOTS; k = k + 1) begin : g_slot
        wire [SLW-1:0] w = li_q[k*SLW +: SLW];
        assign s_beat[k*256 +: 256] = w[255:0];
        assign s_sel[k*2 +: 2]      = w[257:256];
        assign s_ktail[k]           = w[258];
        assign s_isk[k]             = w[259];
        assign s_loc[k*7 +: 7]      = w[266:260];
        assign s_port[k*7 +: 7]     = w[273:267];
        assign s_v[k]               = w[274] && (w[280:275] == tile_id[5:0]);
    end endgenerate
    wire [6:0]   rr_n    = li_q[LSLOTS*SLW +: 7];
    wire [127:0] tail_lm = li_q[LSLOTS*SLW + 7 +: 128];
    wire [LSLOTS-1:0] s_grant;
    wire         kvw_ce;
    wire [6:0]   kvw_addr;
    wire [511:0] kvw_data, kvw_mask;
    ot_qwen_kv_land_merge #(.NSRC(LSLOTS), .PW(7), .LW(7), .DW(512)) u_merge (
        .clk(clk), .rst_n(rst_n), .rr_n(rr_n), .s_v(s_v), .s_port(s_port), .s_loc(s_loc), .s_isk(s_isk),
        .s_ktail(s_ktail), .s_sel(s_sel), .s_beat(s_beat), .tail_lm(tail_lm), .s_grant(s_grant),
        .tok_v(1'b0), .tok_loc(7'd0), .tok_data(512'd0), .tok_mask(512'd0),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
    reg land_fault;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) land_fault <= 1'b0;
        else land_fault <= land_fault | (|(s_v & ~s_grant));
    // ---- the W12 tile ----------------------------------------------------------------------------------------------
    wire tile_fault;
    ot_qwen_rom_tile_w12 #(.NW(NW), .GT(GT), .SMIN(SMIN), .CODE_BANKS(CODE_BANKS), .KV_VB(KV_VB), .KV_NH(KV_NH),
        .MEM_EXTRA(MEM_EXTRA), .ACC_LAT(ACC_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .TREE_LAT(TREE_LAT)) u_tile (
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl), .t_out(t_out), .t_vout(t_vout),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .fault(tile_fault),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask));
    (* keep *) reg fault_q;    // flop-launched output pin (fault collection is multi-cycle on the die)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0; else fault_q <= tile_fault | land_fault;
    assign fault = fault_q;
endmodule
