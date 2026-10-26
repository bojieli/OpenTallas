`timescale 1ns/1ps
// Explicit source identity of the existing TP8 four-lane upper-tree leaf.
// The implementation parameters match qfd_tt_up4_leafr. This wire-only wrapper
// adds no logic or clock edge. Physical use aliases the original published
// ot_qfd_band_upper view only after numeric pin and parameter equality checks.
module qfd_band_upper_tp8 (
    input wire clk,
    input wire rst_n,
    input wire [383:0] pw,
    input wire [2:0] pw_v,
    input wire [2:0] lf,
    input wire [12:0] sel_e,
    input wire [12:0] tv_e,
    output wire [383:0] tt_ty,
    output wire tt_use,
    output wire tt_v,
    output wire fault
);
    ot_qfd_band_upper #(
        .NL(4), .NB(3), .LNK(0), .DLY(1), .TREE_LAT(7),
        .MUT(0), .TCUT(7), .LG(12), .RPIN(1)
    ) u_leaf (
        .clk(clk), .rst_n(rst_n), .pw(pw), .pw_v(pw_v), .lf(lf),
        .sel_e(sel_e), .tv_e(tv_e), .tt_ty(tt_ty),
        .tt_use(tt_use), .tt_v(tt_v), .fault(fault)
    );
endmodule
