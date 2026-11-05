`default_nettype none
// HBM-REFORM-A3 11-05 d44v part 19: plan composition of the TKM tile, same ports as ot_hgi_coll_tkm_tp192_tile_core. Sub-blocks are the hard cores, each with its kit face shell.
// Same wiring as ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__split (reform_1103, reduced-chain EQ receipt).
module ot_hgi_coll_tkm_tp192_tile_core__splitc (
    input wire tile_clk, input wire tile_clr, output wire tile_clr_o, input wire tile_conv, output wire tile_conv_o,
    input wire [343:0] tile_ins_b, input wire tile_ins_v, input wire [343:0] tile_up_in,
    output wire [343:0] tile_ovf_b, output wire tile_ovf_v, output wire [343:0] tile_up_out);
    wire clr_ab, conv_ba, v_ab; wire [343:0] b_ab, up_ba;
    ot_hgi_coll_tkm_tp192_htile_core u_ha (.tile_clk(tile_clk), .tile_clr(tile_clr), .tile_clr_o(clr_ab), .tile_conv(conv_ba), .tile_conv_o(tile_conv_o),
        .tile_ins_v(tile_ins_v), .tile_ins_b(tile_ins_b), .tile_ovf_v(v_ab), .tile_ovf_b(b_ab), .tile_up_in(up_ba), .tile_up_out(tile_up_out));
    ot_hgi_coll_tkm_tp192_htile_core u_hb (.tile_clk(tile_clk), .tile_clr(clr_ab), .tile_clr_o(tile_clr_o), .tile_conv(tile_conv), .tile_conv_o(conv_ba),
        .tile_ins_v(v_ab), .tile_ins_b(b_ab), .tile_ovf_v(tile_ovf_v), .tile_ovf_b(tile_ovf_b), .tile_up_in(tile_up_in), .tile_up_out(up_ba));
endmodule
`default_nettype wire
