`timescale 1ns/1ps
// b2 two-lane upper leaf: halfband words W0,E0,W1,E1,W2,E2.
// L10 combines each original band, L11 combines bands in the original order.
// NEW physical source; never alias the NB3 closed view. Clock and pipeline
// parameters match the exact halfband composition bench.
module qfd_band_upper_b2_l2 (
    input wire clk,
    input wire rst_n,
    input wire [383:0] pw,
    input wire [5:0] pw_v,
    input wire [5:0] lf,
    input wire [12:0] sel_e,
    input wire [12:0] tv_e,
    output wire [191:0] tt_ty,
    output wire tt_use,
    output wire tt_v,
    output wire fault
);
    ot_qfd_band_upper #(
        .NL(2), .NB(6), .LNK(0), .DLY(1), .TREE_LAT(7),
        .MUT(0), .TCUT(6), .LG(12), .RPIN(1)
    ) u_leaf (
        .clk(clk), .rst_n(rst_n), .pw(pw), .pw_v(pw_v), .lf(lf),
        .sel_e(sel_e), .tv_e(tv_e), .tt_ty(tt_ty),
        .tt_use(tt_use), .tt_v(tt_v), .fault(fault)
    );
endmodule
