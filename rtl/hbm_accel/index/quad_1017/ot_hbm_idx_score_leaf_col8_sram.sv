`timescale 1ns/1ps
`default_nettype none
// IDX-SCORE CLUSTER (H-NETLIST/IDX-SCORE 2026-10-17; H-ELEM approved the registered W->E seam chain, +4 scorer edges,
// ledger IDX.SCORE_CHAIN; H-DIE slot <= 3050 um, 16 head-pair roots per leaf). Same ports and the same arithmetic as
// ot_hbm_idx_score_static; every output 8 edges later (the compiler shifts the selector by 8: hbm_idx_static_calendar.py
// --score-chain 8). Each leaf hop is 2 registers (W pin, E pin: the 450 um reach rule), 4 hops = +8.
//   * 4 x 4 IDENTICAL leaves ot_hbm_idx_score_leaf: row e = engine e (keys of lanes 4e..4e+3), column c = chunk c (heads
//     8c..8c+7, strap hb = 8c). Query, keys and a 30-bit aux word (keep, meta input, W fault cause) enter row e at the W
//     face of leaf (e,0) and are forwarded leaf to leaf through each leaf's W and E pin registers (+2 edges a hop).
//   * sum bus: 4 slots x 138 b {online, v, kv, sum, fault}; leaf c writes slot c from its core and registers the other
//     slots through (W reg, E reg), so every slot reaches the E face of leaf (e,3) at the same age (+8).
//   * W glue (clk_ctl): key line split, valid/keep lanes, meta input, the scorer's W fault checks (combinational into the
//     flop-first leaf (e,0) pins). E glue per row (clk_engine/clk_tail/clk_meta): keep delay, engine settle/online fault,
//     ot_hbm_idx_tail_native, output registers, the d123 meta delay; the scorer fault register (clk_ctl).
// Every leaf pin is registered (flop-first in, register-driven out); seams between leaves are register to register.
module ot_hbm_idx_score_leaf_col8_sram #(parameter integer AUXW = 30)(
    input  wire clk, input wire [15:0] clk_pair, input wire rst_n, input wire [7:0] hb,
    input  wire w_qv, input wire [QW-1:0] w_q, input wire w_kv, input wire [3:0] w_kkv, input wire [KW4-1:0] w_key,
    input  wire [AUXW-1:0] w_aux, input wire [4*SW-1:0] w_bus,
    output wire e_qv, output wire [QW-1:0] e_q, output wire e_kv, output wire [3:0] e_kkv, output wire [KW4-1:0] e_key,
    output wire [AUXW-1:0] e_aux, output reg [4*SW-1:0] e_bus
);
    localparam integer QW = 8 + 512 + 32 + 16, KW4 = 4 * 544, SW = 1 + 1 + 4 + 128 + 4;
    reg f_qv; reg [QW-1:0] f_q; reg f_kv; reg [3:0] f_kkv; reg [KW4-1:0] f_key; reg [AUXW-1:0] f_aux; reg [7:0] hb_p;
    always @(posedge clk) begin
        f_qv <= w_qv; f_q <= w_q; f_kv <= w_kv; f_kkv <= w_kkv; f_key <= w_key; f_aux <= w_aux; hb_p <= hb;
    end
    // E pin registers: a W->E hop is W pin reg -> E pin reg (~half a leaf + the channel each, within the 450 um reach)
    reg g_qv; reg [QW-1:0] g_q; reg g_kv; reg [3:0] g_kkv; reg [KW4-1:0] g_key; reg [AUXW-1:0] g_aux;
    always @(posedge clk) begin g_qv <= f_qv; g_q <= f_q; g_kv <= f_kv; g_kkv <= f_kkv; g_key <= f_key; g_aux <= f_aux; end
    assign e_qv = g_qv; assign e_q = g_q; assign e_kv = g_kv; assign e_kkv = g_kkv; assign e_key = g_key; assign e_aux = g_aux;
    wire c_v_u, on; wire [3:0] c_kv_u, c_f_u; wire [127:0] c_s_u;
    wire n_v; wire [3:0] n_kv, n_f; wire [127:0] n_s;
    ot_hbm_idx_chunk_col8_sram core(.clk(clk), .clk_pair(clk_pair), .rst_n(rst_n), .hb(hb_p),
        .ql_v(f_qv), .ql_head(f_q[QW-1 -: 8]), .ql_codes(f_q[QW-9 -: 512]), .ql_sc(f_q[47:16]), .ql_w(f_q[15:0]),
        .k_v(f_kv), .k_kv(f_kkv), .k_key(f_key),
        .c_v(c_v_u), .c_kv(c_kv_u), .c_sum(c_s_u), .c_fault(c_f_u), .online(on),
        .n_v(n_v), .n_kv(n_kv), .n_sum(n_s), .n_fault(n_f));
    // sum bus: W pin reg (own slot written here from the core) -> E pin reg; every slot ages 2 edges a leaf
    wire [1:0] own = hb_p[4:3];
    reg [4*SW-1:0] b_w;
    integer k;
    always @(posedge clk) begin
        for (k = 0; k < 4; k = k + 1)
            b_w[k*SW +: SW] <= (2'(k) == own) ? {on, n_v, n_kv, n_s, n_f} : w_bus[k*SW +: SW];
        e_bus <= b_w;
    end
endmodule

`default_nettype wire
