// CORE-HBM-SPLIT 2026-10-23.  Split piece ot_hbm_su_static_pgslice_lg__side_softplus (master
// ot_hbm_su_static_pgslice_lg__pv0, plan q_su0/q_su1) = u_side.u_sp of the HBM-P5-RTLB twin ot_hbm_su_static_side_s
// (rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side_s.sv): ot_hbm_su_static_side_softplus_s
// #(LM 3, LA 3, FREG 1) (pinned softplus + fault pin register).  Its 'sp' output is unread in the master (left open
// there), so it is not a pin of the core.
`timescale 1ns/1ps
module ot_hbm_su_side_softplus_core (
    input  wire [2:0]  clk,      // clk_side[4:2]
    input  wire        rst_n,
    input  wire        v,        // side_rest sp_v
    input  wire [31:0] x,        // lane side_x
    output wire [31:0] r,
    output wire        fault
);
    ot_hbm_su_static_side_softplus_s #(.LM(3), .LA(3), .FREG(1)) u_sp (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .sp(),
        .r(r), .vo(), .fault(fault));
endmodule
