`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Reduced die for the full-chip hierarchical implementation: 2 x 2 HDC tiles
// (rtl/chip/ot_chip_hdc_tile.sv) with the die's PHY and link placeholders
// (docs/FULL_CHIP_IMPLEMENTATION.md).  The full die repeats the tile; this is
// the size OpenROAD routes in hours, and the scaling argument to the full die
// is measured on it.
//
// Placement (tools/chip_assembly/floorplans.py): tiles are mirrored in the
// second column (MY) and the second row (MX), the usual tile-flipping, so
//   * horizontal neighbours face each other with their E ports (column 0 E,
//     column 1 mirrored E) and vertical neighbours with their N ports;
//   * every tile's HBM pins (its W edge) face a die edge: column 0 the west
//     HBM PHY, column 1 the east one;
//   * the outward W ports go to board SerDes on the west and east edges, the
//     outward S ports to UCIe die-to-die modules on the south and north edges.
// Mesh port index: [0] N, [1] E, [2] S, [3] W.
//
// Every mesh pin is a register inside its tile (ot_chip_mesh_link), so the
// die-level mesh channel is flop-to-flop across a 20 um gap.
// ---------------------------------------------------------------------------
module ot_chip_die2x2 (
    input  wire         clk,
    input  wire         rst_n,
    // host configuration, shared by every tile
    input  wire         rcfg_we,
    input  wire [7:0]   rcfg_dest,
    input  wire [4:0]   rcfg_mask,
    input  wire [3:0]   rcfg_tile,          // one-hot tile select for routing-table writes
    input  wire [7:0]   cfg_users,
    input  wire [15:0]  cfg_prompt_len,
    input  wire [15:0]  cfg_gen_len,
    input  wire [15:0]  cfg_lead,
    // prompt tokens (host interface) of tile 0, the source tile
    output wire         pr_re,
    output wire [7:0]   pr_user,
    output wire [15:0]  pr_pos,
    input  wire [15:0]  pr_q,
    // status of tile 0
    output wire         tok_valid,
    output wire [7:0]   tok_user,
    output wire [15:0]  tok_pos,
    output wire [15:0]  tok_id,
    output wire [3:0]   fault
);
    localparam integer F = 512;
    // tile t = x + 2*y: (0,0) R0, (1,0) MY, (0,1) MX, (1,1) R180
    wire [3:0]     o_v [0:3], o_l [0:3], o_cr [0:3], i_v [0:3], i_l [0:3], i_cr [0:3];
    wire [4*F-1:0] o_d [0:3], i_d [0:3];
    wire           hq_v [0:3], hq_rdy [0:3], hq_we [0:3];
    wire [23:0]    hq_addr [0:3];
    wire [4:0]     hq_len [0:3];
    wire [13:0]    hq_tag [0:3];
    wire [255:0]   hq_wdata [0:3];
    wire [3:0]     hr_v [0:3], hr_rdy [0:3];
    wire [55:0]    hr_tag [0:3];
    wire [15:0]    hr_beat [0:3];
    wire [1023:0]  hr_data [0:3];
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
            ot_chip_hdc_tile u_tile (
                .clk(clk), .rst_n(rst_n),
                .m_out_valid(o_v[t]), .m_out_data(o_d[t]), .m_out_last(o_l[t]), .m_out_cr(o_cr[t]),
                .m_in_valid(i_v[t]), .m_in_data(i_d[t]), .m_in_last(i_l[t]), .m_in_cr(i_cr[t]),
                .rcfg_we(rcfg_we & rcfg_tile[t]), .rcfg_dest(rcfg_dest), .rcfg_mask(rcfg_mask),
                .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
                .cfg_lead(cfg_lead),
                .pr_re(t_pr_re[t]), .pr_user(t_pr_user[t]), .pr_pos(t_pr_pos[t]),
                .pr_q(t == 0 ? pr_q : 16'd0),
                .hq_v(hq_v[t]), .hq_rdy(hq_rdy[t]), .hq_we(hq_we[t]), .hq_addr(hq_addr[t]),
                .hq_len(hq_len[t]), .hq_tag(hq_tag[t]), .hq_wdata(hq_wdata[t]),
                .hr_v(hr_v[t]), .hr_rdy(hr_rdy[t]), .hr_tag(hr_tag[t]), .hr_beat(hr_beat[t]),
                .hr_data(hr_data[t]),
                .tok_valid(t_tok_valid[t]), .tok_user(t_tok_user[t]), .tok_pos(t_tok_pos[t]),
                .tok_id(t_tok_id[t]), .users_done(t_users_done[t]), .core_busy(t_busy[t]),
                .fault(t_fault[t]));
        end
    endgenerate
    assign pr_re = t_pr_re[0]; assign pr_user = t_pr_user[0]; assign pr_pos = t_pr_pos[0];
    assign tok_valid = t_tok_valid[0]; assign tok_user = t_tok_user[0];
    assign tok_pos = t_tok_pos[0]; assign tok_id = t_tok_id[0];
    assign fault = {t_fault[3], t_fault[2], t_fault[1], t_fault[0]};

    // -- mesh: port pa of tile a faces port pb of tile b ------------------------------
    `define OT_LINK(a, pa, b, pb) \
        assign i_v[b][pb] = o_v[a][pa]; assign i_l[b][pb] = o_l[a][pa]; \
        assign i_d[b][(pb)*F +: F] = o_d[a][(pa)*F +: F]; assign o_cr[a][pa] = i_cr[b][pb]; \
        assign i_v[a][pa] = o_v[b][pb]; assign i_l[a][pa] = o_l[b][pb]; \
        assign i_d[a][(pa)*F +: F] = o_d[b][(pb)*F +: F]; assign o_cr[b][pb] = i_cr[a][pa];
    `OT_LINK(0, 1, 1, 1)    // (0,0).E - (1,0).E (mirrored)
    `OT_LINK(2, 1, 3, 1)    // (0,1).E - (1,1).E
    `OT_LINK(0, 0, 2, 0)    // (0,0).N - (0,1).N (mirrored)
    `OT_LINK(1, 0, 3, 0)    // (1,0).N - (1,1).N
    `undef OT_LINK

    // -- outward ports: W to board SerDes, S to UCIe -------------------------------------
    genvar k;
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_edge
            ot_phy_serdes u_serdes (
                .clk(clk),
                .tx_valid(o_v[k][3]), .tx_data(o_d[k][3*F +: F]), .tx_last(o_l[k][3]), .tx_cr(o_cr[k][3]),
                .rx_valid(i_v[k][3]), .rx_data(i_d[k][3*F +: F]), .rx_last(i_l[k][3]), .rx_cr(i_cr[k][3]));
            ot_phy_ucie u_ucie (
                .clk(clk),
                .tx_valid(o_v[k][2]), .tx_data(o_d[k][2*F +: F]), .tx_last(o_l[k][2]), .tx_cr(o_cr[k][2]),
                .rx_valid(i_v[k][2]), .rx_data(i_d[k][2*F +: F]), .rx_last(i_l[k][2]), .rx_cr(i_cr[k][2]));
        end
    endgenerate

    // -- HBM: column 0 tiles (0, 2) to the west PHY, column 1 tiles (1, 3) to the east --
    generate
        for (k = 0; k < 2; k = k + 1) begin : g_hbm
            localparam integer A = k, B = k + 2;   // the column's two tiles (rows 0, 1)
            ot_phy_hbm u_hbm (
                .clk(clk),
                .hq_v({hq_v[B], hq_v[A]}), .hq_rdy({hq_rdy[B], hq_rdy[A]}), .hq_we({hq_we[B], hq_we[A]}),
                .hq_addr({hq_addr[B], hq_addr[A]}), .hq_len({hq_len[B], hq_len[A]}),
                .hq_tag({hq_tag[B], hq_tag[A]}), .hq_wdata({hq_wdata[B], hq_wdata[A]}),
                .hr_v({hr_v[B], hr_v[A]}), .hr_rdy({hr_rdy[B], hr_rdy[A]}),
                .hr_tag({hr_tag[B], hr_tag[A]}), .hr_beat({hr_beat[B], hr_beat[A]}),
                .hr_data({hr_data[B], hr_data[A]}));
        end
    endgenerate
endmodule
