`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LEAD2-S81/CAPC2 (2026-10-19): ot_s81sl_capc2 = the RELEASE capture cluster of one DV slice, as one non-parameterised
// module (a hard view carries no parameters, so the slice / die bind it by name with no override and no $paramod rename).
//   = ot_s81sl_cap_p1 #(.PINPIPE(1), .EDLY(24), .WL3DLY(16)):
//     PINPIPE 1  every data input / output registered at the face (+1 input edge, +1 output edge), reset landed in 2
//                registered stages (g_pin.rst_l0 / rst_l1, +2 release edges)            (S81-CAPC-NATIVEP1, closed 267b)
//     EDLY 24    u_ed  ot_s81sl_cap_ed: E capture-tree word +24 edges before n6        (TOK.DS.BENCH.1 calendar s_16_24)
//     WL3DLY 16  u_ld3 ot_s81sl_cap_ld: W lane 3 (R01) +16 edges before the W tree      (fullsix_l16e24: tree-fault free)
// Hard children (kit s81sl_capc2): u_p.u_core.g_hard.{u_rt, u_tw, u_te}, u_p.u_core.g_ld3.u_ld3, u_p.u_core.g_ed.u_ed.
// Ports = ot_s81sl_cap_p1 = ot_s81sl_cap (drop-in at every slice site).  Schedule: static; the compiler owns +2 (PINPIPE),
// +24 (E words) and +16 (W lane 3 words); bench tools/s81_slice/cap_p1_cal_bench.sh (vs the closed 3-child RTL + TB delays).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_capc2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt_w,
    input  wire [279:0]  rt_e,
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    ot_s81sl_cap_p1 #(.PINPIPE(1), .EDLY(24), .WL3DLY(16)) u_p (.clk(clk), .rst_n(rst_n), .rt_w(rt_w), .rt_e(rt_e),
        .cfg_v(cfg_v), .cfg_d(cfg_d), .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d),
        .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d), .fault(fault));
endmodule
`default_nettype wire
