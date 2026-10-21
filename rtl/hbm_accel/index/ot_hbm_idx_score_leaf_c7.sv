`default_nettype none
// IDX-SCORE leaf c7 (HBM-IDXSQ8 2026-10-20): structural successor of ot_hbm_idx_score_leaf_c1 (one root over 189,723 flops:
// CTS rc137; actual-Liberty native32 FAIL 13,574 drivers). Same data ports, same pin registers, same sum-bus slot logic and
// same cycles as leaf_c1; the core is ot_hbm_idx_chunk_rt_c (codex c7 source a1791bb1d) = chunk glue + 4 x the
// non-parameterised KEY COLUMN ot_hidx_score_col, each a HARD CHILD (kit hidx_score_col7_*, ~47k flops, own CTS root),
// hardened once and replicated 4x (top-down hierarchy contract). RESET_F32 = 1: the glue's 2 x 16-leaf reset tree (native32
// PASS; +1 registered boot-release edge, active data edges unchanged -- handed to the die schedule).
// One clock region (the die's chunk clock; the leaf is < 1 mm): pin regs / glue are soft cells on the leaf root, the columns
// are entered through hard-child clock references; glue <-> column nets are same-region register -> register.
module ot_hbm_idx_score_leaf_c7(                // non-parameterised (AUXW 30): a hard child of the quarter parent
    input  wire clk, input wire rst_n, input wire [7:0] hb,
    input  wire w_qv, input wire [567:0] w_q, input wire w_kv, input wire [3:0] w_kkv, input wire [2175:0] w_key,
    input  wire [29:0] w_aux, input wire [551:0] w_bus,
    output wire e_qv, output wire [567:0] e_q, output wire e_kv, output wire [3:0] e_kkv, output wire [2175:0] e_key,
    output wire [29:0] e_aux, output reg [551:0] e_bus
);
    localparam integer AUXW = 30;
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
    ot_hbm_idx_chunk_rt_c #(.RESET_F32(1)) core(.clk(clk), .rst_n(rst_n), .hb(hb_p),
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
