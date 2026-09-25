`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Collectives nodes of the DeepSeek-V4.1 universal die
// (docs/FULL_CHIP_IMPLEMENTATION.md): the five collective engines of
// rtl/rom/collectives at the die's package edges, between the tiles' outward
// (S) mesh ports and the UCIe die-to-die modules.
//
//   ot_chip_v41_coll_moe (south edge, tiles 0 and 1)
//     tile 0: out -> MoE dispatch -> UCIe 0 tx;   UCIe 1 rx -> MoE combine -> in
//     tile 1: out -> expert port results;  expert port work -> in
//             UCIe 0 rx -> expert port records;  expert port returns -> UCIe 1 tx
//   ot_chip_v41_coll_ar (north edge, tiles 2 and 3)
//     tile 2: out -> argmax reduce logits;  UCIe 0 rx/tx <-> argmax up/down
//     tile 3: out -> multicast inject;  multicast local -> in;
//             UCIe 1 rx/tx <-> multicast up/down
//
// PHYSICAL COMPOSITION, NOT A VERIFIED DATAPATH.  Each engine is verified
// against the golden in its own bench (tb_rom_moe_collectives,
// tb_rom_kv_argmax); how the engines attach to the V4.1 decode core (expert
// work and results, the logit stream) is not in RTL yet.  These nodes give
// them the placement, wires and timing they will have: the tile side through
// the same pipelined credit links as the mesh (every pin a register), the
// UCIe side through the PHY placeholders' flit interfaces.
// ---------------------------------------------------------------------------

// A credit-link port pair turned into valid/ready streams.
module ot_chip_link_adapter #(
    parameter integer F = 512,
    parameter integer STAGES = 3,
    parameter integer DEPTH = 12
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         l_in_valid,  input wire [F-1:0] l_in_data, input wire l_in_last,
    output wire         l_in_cr,
    output wire         l_out_valid, output wire [F-1:0] l_out_data, output wire l_out_last,
    input  wire         l_out_cr,
    output wire         s_in_valid,  input wire s_in_ready, output wire [F-1:0] s_in_data,
    output wire         s_in_last,
    input  wire         s_out_valid, output wire s_out_ready, input wire [F-1:0] s_out_data,
    input  wire         s_out_last,
    output wire         overflow
);
    ot_chip_mesh_link_rx #(.W(F), .IN_STAGES(STAGES), .RET_STAGES(STAGES), .DEPTH(DEPTH)) u_rx (
        .clk(clk), .rst_n(rst_n), .ch_valid(l_in_valid), .ch_data(l_in_data), .ch_last(l_in_last),
        .out_valid(s_in_valid), .out_ready(s_in_ready), .out_data(s_in_data), .out_last(s_in_last),
        .cr_ret(l_in_cr), .overflow(overflow));
    ot_chip_mesh_link_tx #(.W(F), .STAGES(STAGES), .CREDITS(DEPTH)) u_tx (
        .clk(clk), .rst_n(rst_n), .in_valid(s_out_valid), .in_ready(s_out_ready), .in_data(s_out_data),
        .in_last(s_out_last), .ch_valid(l_out_valid), .ch_data(l_out_data), .ch_last(l_out_last),
        .cr_ret(l_out_cr));
endmodule

// Shared port list of both nodes: two tile credit links, two UCIe flit links.
`define OT_COLL_PORTS \
    input  wire          clk, \
    input  wire          rst_n, \
    input  wire [1:0]    t_in_valid, input wire [2*512-1:0] t_in_data, input wire [1:0] t_in_last, \
    output wire [1:0]    t_in_cr, \
    output wire [1:0]    t_out_valid, output wire [2*512-1:0] t_out_data, output wire [1:0] t_out_last, \
    input  wire [1:0]    t_out_cr, \
    output wire [1:0]    u_tx_valid, output wire [2*512-1:0] u_tx_data, output wire [1:0] u_tx_last, \
    input  wire [1:0]    u_tx_cr, \
    input  wire [1:0]    u_rx_valid, input wire [2*512-1:0] u_rx_data, input wire [1:0] u_rx_last, \
    output wire [1:0]    u_rx_cr, \
    output wire [2:0]    fault

`define OT_COLL_ADAPTERS \
    wire [1:0] ti_v, ti_r, ti_l, to_v, to_r, to_l, ui_v, ui_r, ui_l, uo_v, uo_r, uo_l, ovf_t, ovf_u; \
    wire [2*F-1:0] ti_d, to_d, ui_d, uo_d; \
    genvar p; \
    generate for (p = 0; p < 2; p = p + 1) begin : g_ad \
        ot_chip_link_adapter #(.F(F), .STAGES(3), .DEPTH(12)) u_t ( \
            .clk(clk), .rst_n(rst_n), \
            .l_in_valid(t_in_valid[p]), .l_in_data(t_in_data[p*F +: F]), .l_in_last(t_in_last[p]), \
            .l_in_cr(t_in_cr[p]), .l_out_valid(t_out_valid[p]), .l_out_data(t_out_data[p*F +: F]), \
            .l_out_last(t_out_last[p]), .l_out_cr(t_out_cr[p]), \
            .s_in_valid(ti_v[p]), .s_in_ready(ti_r[p]), .s_in_data(ti_d[p*F +: F]), .s_in_last(ti_l[p]), \
            .s_out_valid(to_v[p]), .s_out_ready(to_r[p]), .s_out_data(to_d[p*F +: F]), \
            .s_out_last(to_l[p]), .overflow(ovf_t[p])); \
        ot_chip_link_adapter #(.F(F), .STAGES(2), .DEPTH(12)) u_u ( \
            .clk(clk), .rst_n(rst_n), \
            .l_in_valid(u_rx_valid[p]), .l_in_data(u_rx_data[p*F +: F]), .l_in_last(u_rx_last[p]), \
            .l_in_cr(u_rx_cr[p]), .l_out_valid(u_tx_valid[p]), .l_out_data(u_tx_data[p*F +: F]), \
            .l_out_last(u_tx_last[p]), .l_out_cr(u_tx_cr[p]), \
            .s_in_valid(ui_v[p]), .s_in_ready(ui_r[p]), .s_in_data(ui_d[p*F +: F]), .s_in_last(ui_l[p]), \
            .s_out_valid(uo_v[p]), .s_out_ready(uo_r[p]), .s_out_data(uo_d[p*F +: F]), \
            .s_out_last(uo_l[p]), .overflow(ovf_u[p])); \
    end endgenerate

module ot_chip_v41_coll_moe (`OT_COLL_PORTS);
    localparam integer F = 512;
    `OT_COLL_ADAPTERS
    wire f_disp, f_port, f_comb;
    wire [31:0] d_tok, d_rec, d_flit, e_in, e_drop, e_out, c_res, c_iss, c_wait;
    // dispatch: tile 0 -> UCIe 0
    ot_rom_moe_dispatch #(.FLIT_W(F)) u_dispatch (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ti_v[0]), .in_ready(ti_r[0]), .in_data(ti_d[0 +: F]), .in_last(ti_l[0]),
        .out_valid(uo_v[0]), .out_ready(uo_r[0]), .out_data(uo_d[0 +: F]), .out_last(uo_l[0]),
        .tokens_in(d_tok), .records_out(d_rec), .flits_out(d_flit), .fault(f_disp));
    // expert port: UCIe 0 records -> work to tile 1; tile 1 results -> returns to UCIe 1
    ot_rom_moe_expert_port #(.FLIT_W(F)) u_port (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ui_v[0]), .in_ready(ui_r[0]), .in_data(ui_d[0 +: F]), .in_last(ui_l[0]),
        .work_valid(to_v[1]), .work_ready(to_r[1]), .work_data(to_d[F +: F]), .work_last(to_l[1]),
        .res_valid(ti_v[1]), .res_ready(ti_r[1]), .res_data(ti_d[F +: F]), .res_last(ti_l[1]),
        .res_tag(ti_d[F + 8 +: 8]), .res_rank(ti_d[F + 16 +: 3]), .res_home(ti_d[F + 20 +: 4]),
        .out_valid(uo_v[1]), .out_ready(uo_r[1]), .out_data(uo_d[F +: F]), .out_last(uo_l[1]),
        .records_in(e_in), .records_dropped(e_drop), .results_out(e_out), .fault(f_port));
    // combine: UCIe 1 returns -> tile 0 (the engine never stalls)
    wire          c_v, c_l, c_tfv;
    wire [7:0]    c_tag, c_chunk, c_tf;
    wire [F-1:0]  c_d;
    ot_rom_moe_combine #(.FLIT_W(F), .TAGS(2)) u_combine (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ui_v[1]), .in_ready(ui_r[1]), .in_data(ui_d[F +: F]), .in_last(ui_l[1]),
        .out_valid(c_v), .out_tag(c_tag), .out_chunk(c_chunk), .out_data(c_d), .out_last(c_l),
        .tag_free_valid(c_tfv), .tag_free(c_tf), .results_in(c_res), .chunks_issued(c_iss),
        .walker_waits(c_wait), .fault(f_comb));
    assign to_v[0] = c_v;
    assign to_d[0 +: F] = c_d;
    assign to_l[0] = c_l;
    reg [2:0] fault_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_r <= 3'd0;
        else fault_r <= {(|ovf_t) | (|ovf_u) | (c_v & ~to_r[0]), f_comb, f_disp | f_port};
    assign fault = fault_r;
endmodule

module ot_chip_v41_coll_ar (`OT_COLL_PORTS);
    localparam integer F = 512;
    `OT_COLL_ADAPTERS
    wire f_amax;
    wire [31:0] a_tok, m_del, m_fwd, m_inj;
    // argmax reduce: tile 2's logits, UCIe 0 up / down
    ot_rom_argmax_reduce #(.FLIT_W(F)) u_argmax (
        .clk(clk), .rst_n(rst_n),
        .lg_valid(ti_v[0]), .lg_ready(ti_r[0]), .lg_data(ti_d[0 +: F]), .lg_mask(16'hFFFF),
        .lg_base(32'd0), .lg_tag(8'd0), .lg_last(ti_l[0]),
        .up_valid(ui_v[0]), .up_ready(ui_r[0]), .up_data(ui_d[0 +: F]), .up_last(ui_l[0]),
        .dn_valid(uo_v[0]), .dn_ready(uo_r[0]), .dn_data(uo_d[0 +: F]), .dn_last(uo_l[0]),
        .tokens_out(a_tok), .fault(f_amax));
    assign to_v[0] = 1'b0; assign to_d[0 +: F] = {F{1'b0}}; assign to_l[0] = 1'b0;
    // multicast node: tile 3 injects and takes deliveries, UCIe 1 up / down
    ot_rom_mcast_node #(.FLIT_W(F)) u_mcast (
        .clk(clk), .rst_n(rst_n),
        .up_valid(ui_v[1]), .up_ready(ui_r[1]), .up_data(ui_d[F +: F]), .up_last(ui_l[1]),
        .inj_valid(ti_v[1]), .inj_ready(ti_r[1]), .inj_data(ti_d[F +: F]), .inj_last(ti_l[1]),
        .dn_valid(uo_v[1]), .dn_ready(uo_r[1]), .dn_data(uo_d[F +: F]), .dn_last(uo_l[1]),
        .loc_valid(to_v[1]), .loc_ready(to_r[1]), .loc_data(to_d[F +: F]), .loc_last(to_l[1]),
        .delivered(m_del), .forwarded(m_fwd), .injected(m_inj));
    reg [2:0] fault_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_r <= 3'd0;
        else fault_r <= {(|ovf_t) | (|ovf_u), 1'b0, f_amax};
    assign fault = fault_r;
endmodule
`undef OT_COLL_PORTS
`undef OT_COLL_ADAPTERS
