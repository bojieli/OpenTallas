`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Reduced DeepSeek-V4.1 universal die: 2 x 2 V4.1 tiles
// (rtl/chip/ot_chip_v41_tile.sv), the two collectives nodes
// (rtl/chip/ot_chip_v41_coll.sv) at the package edges with their UCIe
// modules, board SerDes on the west and east edges, and HBM PHY slices
// (docs/FULL_CHIP_IMPLEMENTATION.md).
//
// Tiles are mirrored as on the HDC die (column 1 MY, row 1 MX); each tile's
// outward S mesh port sits at its inner corner, so the two tiles of a row
// meet their collectives node at the middle of the package edge.
//
// The HBM slices are area and shoreline only: the V4.1 decode core has no
// KV streaming interface in RTL yet (its KV port is served by the tile's KV
// SRAM), so their request ports are tied off.  Every die of the package has
// this layout; its ROM contents are its via mask.
// ---------------------------------------------------------------------------
module ot_chip_v41_die2x2 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         rcfg_we,
    input  wire [7:0]   rcfg_dest,
    input  wire [4:0]   rcfg_mask,
    input  wire [3:0]   rcfg_tile,
    input  wire [7:0]   cfg_users,
    input  wire [15:0]  cfg_prompt_len,
    input  wire [15:0]  cfg_gen_len,
    output wire         pr_re,
    output wire [7:0]   pr_user,
    output wire [15:0]  pr_pos,
    input  wire [15:0]  pr_q,
    output wire         tok_valid,
    output wire [7:0]   tok_user,
    output wire [15:0]  tok_pos,
    output wire [15:0]  tok_id,
    output wire [3:0]   fault,
    output wire [5:0]   coll_fault
);
    localparam integer F = 512;
    wire [3:0]     o_v [0:3], o_l [0:3], o_cr [0:3], i_v [0:3], i_l [0:3], i_cr [0:3];
    wire [4*F-1:0] o_d [0:3], i_d [0:3];
    wire           t_pr_re [0:3];
    wire [7:0]     t_pr_user [0:3];
    wire [15:0]    t_pr_pos [0:3];
    wire           t_tok_valid [0:3];
    wire [7:0]     t_tok_user [0:3], t_users_done [0:3];
    wire [15:0]    t_tok_pos [0:3], t_tok_id [0:3];
    wire           t_busy [0:3], t_fault [0:3];

    genvar t;
    generate
        for (t = 0; t < 4; t = t + 1) begin : g_tile
            ot_chip_v41_tile u_tile (
                .clk(clk), .rst_n(rst_n),
                .m_out_valid(o_v[t]), .m_out_data(o_d[t]), .m_out_last(o_l[t]), .m_out_cr(o_cr[t]),
                .m_in_valid(i_v[t]), .m_in_data(i_d[t]), .m_in_last(i_l[t]), .m_in_cr(i_cr[t]),
                .rcfg_we(rcfg_we & rcfg_tile[t]), .rcfg_dest(rcfg_dest), .rcfg_mask(rcfg_mask),
                .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
                .pr_re(t_pr_re[t]), .pr_user(t_pr_user[t]), .pr_pos(t_pr_pos[t]),
                .pr_q(t == 0 ? pr_q : 16'd0),
                .tok_valid(t_tok_valid[t]), .tok_user(t_tok_user[t]), .tok_pos(t_tok_pos[t]),
                .tok_id(t_tok_id[t]), .users_done(t_users_done[t]), .core_busy(t_busy[t]),
                .fault(t_fault[t]));
        end
    endgenerate
    assign pr_re = t_pr_re[0]; assign pr_user = t_pr_user[0]; assign pr_pos = t_pr_pos[0];
    assign tok_valid = t_tok_valid[0]; assign tok_user = t_tok_user[0];
    assign tok_pos = t_tok_pos[0]; assign tok_id = t_tok_id[0];
    assign fault = {t_fault[3], t_fault[2], t_fault[1], t_fault[0]};

    `define OT_LINK(a, pa, b, pb) \
        assign i_v[b][pb] = o_v[a][pa]; assign i_l[b][pb] = o_l[a][pa]; \
        assign i_d[b][(pb)*F +: F] = o_d[a][(pa)*F +: F]; assign o_cr[a][pa] = i_cr[b][pb]; \
        assign i_v[a][pa] = o_v[b][pb]; assign i_l[a][pa] = o_l[b][pb]; \
        assign i_d[a][(pa)*F +: F] = o_d[b][(pb)*F +: F]; assign o_cr[b][pb] = i_cr[a][pa];
    `OT_LINK(0, 1, 1, 1)
    `OT_LINK(2, 1, 3, 1)
    `OT_LINK(0, 0, 2, 0)
    `OT_LINK(1, 0, 3, 0)
    `undef OT_LINK

    // W ports: board SerDes
    genvar k;
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_edge
            ot_phy_serdes u_serdes (
                .clk(clk),
                .tx_valid(o_v[k][3]), .tx_data(o_d[k][3*F +: F]), .tx_last(o_l[k][3]), .tx_cr(o_cr[k][3]),
                .rx_valid(i_v[k][3]), .rx_data(i_d[k][3*F +: F]), .rx_last(i_l[k][3]), .rx_cr(i_cr[k][3]));
        end
    endgenerate

    // S ports: the collectives nodes (row 0: MoE, row 1: argmax / multicast), then UCIe
    wire [1:0]     u_tv [0:1], u_tl [0:1], u_tc [0:1], u_rv [0:1], u_rl [0:1], u_rc [0:1];
    wire [2*F-1:0] u_td [0:1], u_rd [0:1];
    wire [2:0]     cf [0:1];
    ot_chip_v41_coll_moe u_coll_moe (
        .clk(clk), .rst_n(rst_n),
        .t_in_valid({o_v[1][2], o_v[0][2]}), .t_in_data({o_d[1][2*F +: F], o_d[0][2*F +: F]}),
        .t_in_last({o_l[1][2], o_l[0][2]}), .t_in_cr({o_cr[1][2], o_cr[0][2]}),
        .t_out_valid({i_v[1][2], i_v[0][2]}), .t_out_data({i_d[1][2*F +: F], i_d[0][2*F +: F]}),
        .t_out_last({i_l[1][2], i_l[0][2]}), .t_out_cr({i_cr[1][2], i_cr[0][2]}),
        .u_tx_valid(u_tv[0]), .u_tx_data(u_td[0]), .u_tx_last(u_tl[0]), .u_tx_cr(u_tc[0]),
        .u_rx_valid(u_rv[0]), .u_rx_data(u_rd[0]), .u_rx_last(u_rl[0]), .u_rx_cr(u_rc[0]),
        .fault(cf[0]));
    ot_chip_v41_coll_ar u_coll_ar (
        .clk(clk), .rst_n(rst_n),
        .t_in_valid({o_v[3][2], o_v[2][2]}), .t_in_data({o_d[3][2*F +: F], o_d[2][2*F +: F]}),
        .t_in_last({o_l[3][2], o_l[2][2]}), .t_in_cr({o_cr[3][2], o_cr[2][2]}),
        .t_out_valid({i_v[3][2], i_v[2][2]}), .t_out_data({i_d[3][2*F +: F], i_d[2][2*F +: F]}),
        .t_out_last({i_l[3][2], i_l[2][2]}), .t_out_cr({i_cr[3][2], i_cr[2][2]}),
        .u_tx_valid(u_tv[1]), .u_tx_data(u_td[1]), .u_tx_last(u_tl[1]), .u_tx_cr(u_tc[1]),
        .u_rx_valid(u_rv[1]), .u_rx_data(u_rd[1]), .u_rx_last(u_rl[1]), .u_rx_cr(u_rc[1]),
        .fault(cf[1]));
    assign coll_fault = {cf[1], cf[0]};
    // UCIe module u = 2*node + side (side 0 west of the node, 1 east)
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_ucie
            localparam integer N = k / 2, S = k % 2;
            ot_phy_ucie u_ucie (
                .clk(clk),
                .tx_valid(u_tv[N][S]), .tx_data(u_td[N][S*F +: F]), .tx_last(u_tl[N][S]), .tx_cr(u_tc[N][S]),
                .rx_valid(u_rv[N][S]), .rx_data(u_rd[N][S*F +: F]), .rx_last(u_rl[N][S]), .rx_cr(u_rc[N][S]));
        end
    endgenerate

    // HBM slices: shoreline and area; no V4.1 KV streaming interface yet
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_hbm
            wire          q_rdy;
            wire [3:0]    r_v;
            wire [55:0]   r_tag;
            wire [15:0]   r_beat;
            wire [1023:0] r_data;
            ot_phy_hbm u_hbm (
                .clk(clk), .hq_v(1'b0), .hq_rdy(q_rdy), .hq_we(1'b0), .hq_addr(24'd0), .hq_len(5'd0),
                .hq_tag(14'd0), .hq_wdata(256'd0), .hr_v(r_v), .hr_rdy(4'd0), .hr_tag(r_tag),
                .hr_beat(r_beat), .hr_data(r_data));
        end
    endgenerate
endmodule
