`timescale 1ns/1ps
// Exact TP4/Russell Homes.tile boundary for the complete source element.
// Assembly only: no reset-release generator, no synthetic memory responses,
// no omitted matvec/ROM/KV instances. Controls remain opt-in. Before mapping
// bind Ampere's committed full-load/reset/launch contract to these ports.
module ot_qwen_rom_fulltile_tp4_context_top #(
    parameter integer CONTROL_CONTEXT_CANDIDATE = 0
) (
    input wire clk_stream,
    input wire reset_stream_n,
    input wire [15:0] tile_id,
    input wire ib_go,
    input wire [378:0] ib,
    input wire [127:0] xl,
    output wire [511:0] t_out,
    output wire t_vout,
    input wire [511:0] n_a,n_b,
    input wire n_va,
    output wire [511:0] n_y,
    output wire n_vy,fault,
    input wire kvw_ce,
    input wire [6:0] kvw_addr,
    input wire [511:0] kvw_data,kvw_mask
);
    // 3*NW+13*AW+13 = 3*18+13*24+13 =379 instruction bits.
    // 2 KV heads: K22 + V32 =54 active rows in128 physical rows.
    ot_qwen_rom_tile_context_candidate_r2 #(
        .NW(18),.GT(6144),.SMIN(6),.CODE_BANKS(5),
        .KV_NH(2),.KV_VB(131072),.MEM_EXTRA(1),
        .ACC_LAT(7),.TREE_LAT(7),.MUL_LAT(6),.FAST_ISSUE(1),.KV_PREP(3),
        .ROM_HOLD_DIRECT_CAPTURE(CONTROL_CONTEXT_CANDIDATE),
        .ROM_BANK5_CONTROL(CONTROL_CONTEXT_CANDIDATE),
        .ROM_CONTROL_DISTRIBUTION(CONTROL_CONTEXT_CANDIDATE)
    ) u_tile (
        .clk(clk_stream),.rst_n(reset_stream_n),.tile_id(tile_id),
        .ib_go(ib_go),.ib(ib),.xl(xl),.t_out(t_out),.t_vout(t_vout),
        .n_a(n_a),.n_b(n_b),.n_va(n_va),.n_y(n_y),.n_vy(n_vy),.fault(fault),
        .kvw_ce(kvw_ce),.kvw_addr(kvw_addr),.kvw_data(kvw_data),.kvw_mask(kvw_mask)
    );
endmodule
