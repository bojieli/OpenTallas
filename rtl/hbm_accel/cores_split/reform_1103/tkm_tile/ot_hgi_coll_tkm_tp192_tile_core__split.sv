`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03: split compositions of the TKM tp192 tile cores (same pins as the uncut kit cores,
// face-shelled form): two half tiles hA (entries 0..31, root side) + hB (entries 32..63, deep side) wired exactly as two
// consecutive chain elements of the face-shelled parent (ot_hbm_tkm_path_tkx_ft21): down ovf -> ins, up up_out ->
// up_in, clr systolic hA -> hB (clr_o), conv deep-first hB -> hA (conv_o, the HOP-2 deskew of
// ot_hgi_coll_tkm_conv_skew).  Sub-blocks are instantiated in face-shelled form (<sub>__fs = facewrap.py model of the
// kit face shell) so this module is the hardened composition, edge for edge.
// MUT (bench only): 1 = conv broadcast to hA and hB at equal latency (no deskew inside the pair, must FAIL);
//                   2 = one extra edge on the hB -> hA up hop (must FAIL).
module ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__split #(parameter integer MUT = 0) (
    input wire tile_clk, input wire tile_clr, output wire tile_clr_o, input wire tile_conv, output wire tile_conv_o,
    input wire [343:0] tile_ins_b, input wire tile_ins_v, output wire [343:0] tile_ovf_b, output wire tile_ovf_v,
    input wire [343:0] tile_up_in, output wire [343:0] tile_up_out);
    wire clr_ab, conv_ba, conv_bo, v_ab; wire [343:0] b_ab, up_ba, up_ba_d;
    reg [343:0] up_x;
    always @(posedge tile_clk) up_x <= up_ba;
    assign up_ba_d = (MUT == 2) ? up_x : up_ba;
    ot_hgi_coll_tkm_tp192_htile_core__fs u_ha (.tile_clk(tile_clk), .tile_clr(tile_clr), .tile_clr_o(clr_ab),
        .tile_conv((MUT == 1) ? tile_conv : conv_ba), .tile_conv_o(tile_conv_o), .tile_ins_v(tile_ins_v), .tile_ins_b(tile_ins_b),
        .tile_ovf_v(v_ab), .tile_ovf_b(b_ab), .tile_up_in(up_ba_d), .tile_up_out(tile_up_out));
    ot_hgi_coll_tkm_tp192_htile_core__fs u_hb (.tile_clk(tile_clk), .tile_clr(clr_ab), .tile_clr_o(tile_clr_o),
        .tile_conv(tile_conv), .tile_conv_o(conv_bo), .tile_ins_v(v_ab), .tile_ins_b(b_ab),
        .tile_ovf_v(tile_ovf_v), .tile_ovf_b(tile_ovf_b), .tile_up_in(tile_up_in), .tile_up_out(up_ba));
    assign conv_ba = conv_bo;
endmodule

// Chain end (as-built tile NT-1): hB's up_in = 0 (up[NT] = 0), hB's ovf open; same two masters.
module ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__split #(parameter integer MUT = 0) (
    input wire tile_clk, input wire tile_clr, output wire tile_clr_o, input wire tile_conv, output wire tile_conv_o,
    input wire [343:0] tile_ins_b, input wire tile_ins_v, output wire [343:0] tile_up_out);
    wire unused_v; wire [343:0] unused_b;
    ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__split #(.MUT(MUT)) u_pair (.tile_clk(tile_clk), .tile_clr(tile_clr),
        .tile_clr_o(tile_clr_o), .tile_conv(tile_conv), .tile_conv_o(tile_conv_o), .tile_ins_b(tile_ins_b),
        .tile_ins_v(tile_ins_v), .tile_ovf_b(unused_b), .tile_ovf_v(unused_v), .tile_up_in(344'd0), .tile_up_out(tile_up_out));
endmodule
`default_nettype wire
