// DIE-HBM-61/SPLIT d44v part 6 (u_core -> ot_hgi_coll_tkm_tp192_tile_core__splitc); from gen_core_kit_hbm.py (ELEM-HBM): pass-through wrapper, plan pins -> RTL top; wires only.
`default_nettype none
module ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fcore (
    input wire tile_clk,
    input wire tile_clr,
    output wire tile_clr_o,
    input wire tile_conv,
    output wire tile_conv_o,
    input wire [343:0] tile_ins_b,
    input wire tile_ins_v,
    output wire [343:0] tile_ovf_b,
    output wire tile_ovf_v,
    input wire [343:0] tile_up_in,
    output wire [343:0] tile_up_out
);
    ot_hgi_coll_tkm_tp192_tile_core__splitc u_core (
        .tile_clk(tile_clk),
        .tile_clr(tile_clr),
        .tile_clr_o(tile_clr_o),
        .tile_conv(tile_conv),
        .tile_conv_o(tile_conv_o),
        .tile_ins_b(tile_ins_b),
        .tile_ins_v(tile_ins_v),
        .tile_ovf_b(tile_ovf_b),
        .tile_ovf_v(tile_ovf_v),
        .tile_up_in(tile_up_in),
        .tile_up_out(tile_up_out));
endmodule
`default_nettype wire

// DIE-HBM-61/SPLIT d44v part 6: plan module ot_hgi_coll_tkm_tp192_tile_core__idpin__strap = thin parent glue of the split hard core (wires only; the
// sub-cores of ot_hgi_coll_tkm_tp192_tile_core__splitc are the hard cores, each with its own kit face shell).  Ports open in the composition: none.
`default_nettype none
module ot_hgi_coll_tkm_tp192_tile_core__idpin__strap (
    input wire tile_clk,
    input wire tile_clr,
    output wire tile_clr_o,
    input wire tile_conv,
    output wire tile_conv_o,
    input wire [343:0] tile_ins_b,
    input wire tile_ins_v,
    output wire [343:0] tile_ovf_b,
    output wire tile_ovf_v,
    input wire [343:0] tile_up_in,
    output wire [343:0] tile_up_out
);
    ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fcore u_fcore (.tile_clk(tile_clk), .tile_clr(tile_clr), .tile_clr_o(tile_clr_o), .tile_conv(tile_conv), .tile_conv_o(tile_conv_o), .tile_ins_b(tile_ins_b), .tile_ins_v(tile_ins_v), .tile_ovf_b(tile_ovf_b), .tile_ovf_v(tile_ovf_v), .tile_up_in(tile_up_in), .tile_up_out(tile_up_out));
endmodule
`default_nettype wire
