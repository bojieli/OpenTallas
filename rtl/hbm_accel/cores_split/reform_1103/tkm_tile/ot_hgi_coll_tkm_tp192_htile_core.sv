`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03 (OWNER TWO-STRIKES RE-FORM, HBM batch HBM-RF1 / plan event d44v): TKM tp192 HALF TILE.
// The uncut chain element ot_hgi_coll_tkm_tp192_tile_core (= ot_hgi_coll_tkm_tile_e86 = ot_hgi_coll_tkm_tile_rg
// #(EW 86, PT 64), 176k / 172k cells with the face shell, > 150k) is re-formed as TWO chain elements of PT 32 each:
// the SAME insertion tile RTL (ot_hgi_coll_tkm_tile_rg, rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv,
// unchanged) at PT 32.  The TKM chain becomes 64 elements of 32 entries (KMAX 2048 unchanged).
// Why a chain cut and not a position cut: every insertion position q reads X[q-4..q] and the per-position compare
// counts of q-4..q in the SAME edge (and conv shifts X[q] <= X[q+4] in the same edge), so any cut inside the 64-entry
// array is a single-edge combinational coupling; a chain element boundary is the only register-to-register seam
// (ovf_b/ovf_v reg -> next p_bg/p_vg reg down, up_out reg -> X conv mux up), the one the 32 tiles already use.
// Ports and control lanes = ot_hgi_coll_tkm_tp192_tile_core (plan pin template): clr systolic down (+1 FT flop),
// conv forwarded up (+0), tid dead (tied 0, owner ruling 10-25 14:44), tau unused.  ONE master for all 64 elements;
// the chain-end element ties up_in to 0 at the parent (as-built up[NT] = 0) and leaves ovf open.
module ot_hgi_coll_tkm_tp192_htile_core #(parameter integer PT = 32) (
    input wire tile_clk,
    input wire tile_clr,
    input wire tile_conv,
    output reg tile_clr_o,
    output wire tile_conv_o,
    input wire tile_ins_v,
    input wire [343:0] tile_ins_b,
    input wire [343:0] tile_up_in,
    output wire tile_ovf_v,
    output wire [343:0] tile_ovf_b,
    output wire [343:0] tile_up_out
);
    ot_hgi_coll_tkm_tile_rg #(.EW(86), .PT(PT)) u_tile (
        .clk(tile_clk), .clk_r0(tile_clk), .clk_r1(tile_clk), .clk_r2(tile_clk), .clk_r3(tile_clk),
        .tid(6'd0), .clr(tile_clr), .conv(tile_conv), .tau_t(6'd0), .tau_l(7'd0),
        .ins_v(tile_ins_v), .ins_b(tile_ins_b), .ovf_v(tile_ovf_v), .ovf_b(tile_ovf_b),
        .up_in(tile_up_in), .up_out(tile_up_out), .tau_o(), .busy());
    always @(posedge tile_clk) tile_clr_o <= tile_clr;   // native chain control: clr +1 core edge, conv +0
    assign tile_conv_o = tile_conv;
endmodule
`default_nettype wire
