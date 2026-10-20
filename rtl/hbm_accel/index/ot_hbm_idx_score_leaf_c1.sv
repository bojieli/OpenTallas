`default_nettype none
// IDX-SCORE leaf, ONE clock root (L2H-IDXSCORE 2026-10-19): structural successor of ot_hbm_idx_score_leaf (same data ports,
// same cycles). r10 gate: the 16 head-pair roots clk_pair[*] are internal-only roots (no boundary flops), so the clock rule
// judges ALL their sinks, and without placement fences each root's ~11.5k sinks spread over the leaf (clk_pair[0] TT
// pin-flop spread 176.2 ps, insertion 679 ps -> CTS rc 2). Here every leaf flop is on the one centre-fed root clk (the die's
// chunk clock, as the pin/glue regs already were); the head-pair region structure stays in the RTL (region reset relays),
// clocked by the same root. Core = ot_hbm_idx_chunk_rt_l (landed reset relays, ring-buffer delays).
module ot_hbm_idx_score_leaf_c1 #(parameter integer AUXW = 30)(
    input  wire clk, input wire rst_n, input wire [7:0] hb,
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
    ot_hbm_idx_chunk_rt_l core(.clk(clk), .clk_pair({16{clk}}), .rst_n(rst_n), .hb(hb_p),
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
