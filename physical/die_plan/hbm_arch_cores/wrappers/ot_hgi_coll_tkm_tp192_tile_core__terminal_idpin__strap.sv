// HBM-CORES-R8 10-27: hand-checked pass-through wrapper (wires + one source constant), plan module
// ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap (planU6b pins cores/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__chain.json
// @76c8acd22222, 8 buses) around the common tile core ot_hgi_coll_tkm_tp192_tile_core.
// Terminal tile t = NT-1: the as-built master ties its up_in to the constant chain end
//   rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_p.sv:155  assign up[NT]=0;  (.up_in(up[t+1]))
// and leaves its ovf_v/ovf_b (dv[NT], down[NT]) unread at the parent -> open outputs here.
// Identical to the qualified face cohort fcore wrapper
//   tools/hbm_b2/q3stageb/tkm_face_cohort/rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/noid_v2/
//   ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__wrap.sv  (module renamed to the plan module).
`default_nettype none
module ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap (
    input wire tile_clk,
    input wire tile_clr,
    output wire tile_clr_o,
    input wire tile_conv,
    output wire tile_conv_o,
    input wire [343:0] tile_ins_b,
    input wire tile_ins_v,
    output wire [343:0] tile_up_out
);
    ot_hgi_coll_tkm_tp192_tile_core u_core (
        .tile_clk(tile_clk),
        .tile_clr(tile_clr),
        .tile_clr_o(tile_clr_o),
        .tile_conv(tile_conv),
        .tile_conv_o(tile_conv_o),
        .tile_ins_b(tile_ins_b),
        .tile_ins_v(tile_ins_v),
        .tile_up_out(tile_up_out),
        .tile_up_in(344'd0),
        .tile_ovf_v(),
        .tile_ovf_b());
endmodule
`default_nettype wire
