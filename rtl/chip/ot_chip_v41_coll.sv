`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Collectives node of the DeepSeek-V4.1 universal die
// (docs/FULL_CHIP_IMPLEMENTATION.md): the five collective engines of
// rtl/rom/collectives -- MoE dispatch (multicast), MoE expert port, MoE
// combine, argmax reduce and the multicast node -- at the die's package edge,
// between the tiles' outward mesh ports and the UCIe die-to-die modules.
//
// PHYSICAL COMPOSITION, NOT A VERIFIED DATAPATH.  The engines are each
// verified against the golden in their own benches (tb_rom_moe_collectives,
// tb_rom_kv_argmax); how they attach to the V4.1 decode core (the expert work
// and result streams, the logit stream) is not in RTL yet.  This node gives
// them the placement, the wires and the timing they will have: tile side
// through the same pipelined credit links as the mesh (every pin a
// register), UCIe side through the PHY placeholders' flit interfaces.
//
//   tile port 0  out -> dispatch.in            dispatch.out   -> UCIe 0 tx
//                in  <- combine.out            UCIe 1 rx      -> combine.in
//   tile port 1  out -> expert_port.res        UCIe 0 rx      -> expert_port.in
//                in  <- expert_port.work       expert_port.out-> UCIe 1 tx
//   tile port 2  out -> argmax.lg (16 lanes)   UCIe 2 rx/tx   <-> argmax up/dn
//   tile port 3  out -> mcast.inj              UCIe 3 rx/tx   <-> mcast up/dn
//                in  <- mcast.loc
// ---------------------------------------------------------------------------
module ot_chip_v41_coll #(
    parameter integer F = 512,
    parameter integer LINK_STAGES = 3,
    parameter integer LINK_DEPTH  = 12
) (
    input  wire          clk,
    input  wire          rst_n,
    // tile side: four credit links (as a tile's mesh port)
    input  wire [3:0]    t_in_valid,          // from the tiles' m_out_*
    input  wire [4*F-1:0] t_in_data,
    input  wire [3:0]    t_in_last,
    output wire [3:0]    t_in_cr,
    output wire [3:0]    t_out_valid,         // to the tiles' m_in_*
    output wire [4*F-1:0] t_out_data,
    output wire [3:0]    t_out_last,
    input  wire [3:0]    t_out_cr,
    // UCIe side: four flit links (the PHY placeholders' tx/rx)
    output wire [3:0]    u_tx_valid,
    output wire [4*F-1:0] u_tx_data,
    output wire [3:0]    u_tx_last,
    input  wire [3:0]    u_tx_cr,
    input  wire [3:0]    u_rx_valid,
    input  wire [4*F-1:0] u_rx_data,
    input  wire [3:0]    u_rx_last,
    output wire [3:0]    u_rx_cr,
    output wire [4:0]    fault
);
    // -- link adapters: credit link <-> valid/ready ----------------------------------------
    wire [3:0] ti_v, ti_r, ti_l, to_v, to_r, to_l, ui_v, ui_r, ui_l, uo_v, uo_r, uo_l, ovf_t, ovf_u;
    wire [4*F-1:0] ti_d, to_d, ui_d, uo_d;
    genvar p;
    generate
        for (p = 0; p < 4; p = p + 1) begin : g_ad
            ot_chip_mesh_link_rx #(.W(F), .IN_STAGES(LINK_STAGES), .RET_STAGES(LINK_STAGES),
                                   .DEPTH(LINK_DEPTH)) u_trx (
                .clk(clk), .rst_n(rst_n), .ch_valid(t_in_valid[p]), .ch_data(t_in_data[p*F +: F]),
                .ch_last(t_in_last[p]), .out_valid(ti_v[p]), .out_ready(ti_r[p]),
                .out_data(ti_d[p*F +: F]), .out_last(ti_l[p]), .cr_ret(t_in_cr[p]), .overflow(ovf_t[p]));
            ot_chip_mesh_link_tx #(.W(F), .STAGES(LINK_STAGES), .CREDITS(LINK_DEPTH)) u_ttx (
                .clk(clk), .rst_n(rst_n), .in_valid(to_v[p]), .in_ready(to_r[p]),
                .in_data(to_d[p*F +: F]), .in_last(to_l[p]), .ch_valid(t_out_valid[p]),
                .ch_data(t_out_data[p*F +: F]), .ch_last(t_out_last[p]), .cr_ret(t_out_cr[p]));
            ot_chip_mesh_link_rx #(.W(F), .IN_STAGES(2), .RET_STAGES(2), .DEPTH(LINK_DEPTH)) u_urx (
                .clk(clk), .rst_n(rst_n), .ch_valid(u_rx_valid[p]), .ch_data(u_rx_data[p*F +: F]),
                .ch_last(u_rx_last[p]), .out_valid(ui_v[p]), .out_ready(ui_r[p]),
                .out_data(ui_d[p*F +: F]), .out_last(ui_l[p]), .cr_ret(u_rx_cr[p]), .overflow(ovf_u[p]));
            ot_chip_mesh_link_tx #(.W(F), .STAGES(2), .CREDITS(LINK_DEPTH)) u_utx (
                .clk(clk), .rst_n(rst_n), .in_valid(uo_v[p]), .in_ready(uo_r[p]),
                .in_data(uo_d[p*F +: F]), .in_last(uo_l[p]), .ch_valid(u_tx_valid[p]),
                .ch_data(u_tx_data[p*F +: F]), .ch_last(u_tx_last[p]), .cr_ret(u_tx_cr[p]));
        end
    endgenerate

    // -- MoE dispatch: tile 0 -> UCIe 0 ------------------------------------------------------
    wire f_disp, f_port, f_comb, f_amax;
    wire [31:0] d_tok, d_rec, d_flit;
    ot_rom_moe_dispatch #(.FLIT_W(F)) u_dispatch (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ti_v[0]), .in_ready(ti_r[0]), .in_data(ti_d[0 +: F]), .in_last(ti_l[0]),
        .out_valid(uo_v[0]), .out_ready(uo_r[0]), .out_data(uo_d[0 +: F]), .out_last(uo_l[0]),
        .tokens_in(d_tok), .records_out(d_rec), .flits_out(d_flit), .fault(f_disp));

    // -- MoE expert port: UCIe 0 -> work to tile 1; results from tile 1 -> UCIe 1 -------------
    wire [31:0] e_in, e_drop, e_out;
    ot_rom_moe_expert_port #(.FLIT_W(F)) u_port (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ui_v[0]), .in_ready(ui_r[0]), .in_data(ui_d[0 +: F]), .in_last(ui_l[0]),
        .work_valid(to_v[1]), .work_ready(to_r[1]), .work_data(to_d[F +: F]), .work_last(to_l[1]),
        .res_valid(ti_v[1]), .res_ready(ti_r[1]), .res_data(ti_d[F +: F]), .res_last(ti_l[1]),
        .res_tag(ti_d[F + 8 +: 8]), .res_rank(ti_d[F + 16 +: 3]), .res_home(ti_d[F + 20 +: 4]),
        .out_valid(uo_v[1]), .out_ready(uo_r[1]), .out_data(uo_d[F +: F]), .out_last(uo_l[1]),
        .records_in(e_in), .records_dropped(e_drop), .results_out(e_out), .fault(f_port));

    // -- MoE combine: UCIe 1 -> tile 0 (the engine never stalls: always ready) -----------------
    wire          c_v, c_l, c_tfv;
    wire [7:0]    c_tag, c_chunk, c_tf;
    wire [F-1:0]  c_d;
    wire [31:0]   c_res, c_iss, c_wait;
    ot_rom_moe_combine #(.FLIT_W(F), .TAGS(2)) u_combine (
        .clk(clk), .rst_n(rst_n),
        .in_valid(ui_v[1]), .in_ready(ui_r[1]), .in_data(ui_d[F +: F]), .in_last(ui_l[1]),
        .out_valid(c_v), .out_tag(c_tag), .out_chunk(c_chunk), .out_data(c_d), .out_last(c_l),
        .tag_free_valid(c_tfv), .tag_free(c_tf), .results_in(c_res), .chunks_issued(c_iss),
        .walker_waits(c_wait), .fault(f_comb));
    assign to_v[0] = c_v;
    assign to_d[0 +: F] = c_d;
    assign to_l[0] = c_l;

    // -- argmax reduce: tile 2's logits, UCIe 2 up/down ------------------------------------------
    wire [31:0] a_tok;
    ot_rom_argmax_reduce #(.FLIT_W(F)) u_argmax (
        .clk(clk), .rst_n(rst_n),
        .lg_valid(ti_v[2]), .lg_ready(ti_r[2]), .lg_data(ti_d[2*F +: F]), .lg_mask(16'hFFFF),
        .lg_base(32'd0), .lg_tag(8'd0), .lg_last(ti_l[2]),
        .up_valid(ui_v[2]), .up_ready(ui_r[2]), .up_data(ui_d[2*F +: F]), .up_last(ui_l[2]),
        .dn_valid(uo_v[2]), .dn_ready(uo_r[2]), .dn_data(uo_d[2*F +: F]), .dn_last(uo_l[2]),
        .tokens_out(a_tok), .fault(f_amax));
    assign to_v[2] = 1'b0; assign to_d[2*F +: F] = {F{1'b0}}; assign to_l[2] = 1'b0;

    // -- multicast node: tile 3 injects and takes its deliveries, UCIe 3 up/down --------------
    wire [31:0] m_del, m_fwd, m_inj;
    ot_rom_mcast_node #(.FLIT_W(F)) u_mcast (
        .clk(clk), .rst_n(rst_n),
        .up_valid(ui_v[3]), .up_ready(ui_r[3]), .up_data(ui_d[3*F +: F]), .up_last(ui_l[3]),
        .inj_valid(ti_v[3]), .inj_ready(ti_r[3]), .inj_data(ti_d[3*F +: F]), .inj_last(ti_l[3]),
        .dn_valid(uo_v[3]), .dn_ready(uo_r[3]), .dn_data(uo_d[3*F +: F]), .dn_last(uo_l[3]),
        .loc_valid(to_v[3]), .loc_ready(to_r[3]), .loc_data(to_d[3*F +: F]), .loc_last(to_l[3]),
        .delivered(m_del), .forwarded(m_fwd), .injected(m_inj));

    reg [4:0] fault_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_r <= 5'd0;
        else fault_r <= {|ovf_u | |ovf_t, f_amax, f_comb, f_port, f_disp} |
                        {c_v && !to_r[0], 4'd0};   // a combine result met a full link
    assign fault = fault_r;
endmodule
