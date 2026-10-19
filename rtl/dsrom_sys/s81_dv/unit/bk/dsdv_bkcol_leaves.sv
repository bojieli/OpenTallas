`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK3 (2026-10-17): the collector hard leaves of the VERTICAL cut of the S81-DV bk units (coordinator 0cj (b): the clusters
// stack inside the 680-um column, square-ish leaves; plan results/rtl/s81_dv_1016/bk_units_bk2/vcut_plan.json).
// Each wrapper is the UNCHANGED closed-tile RTL in its hardened configuration, re-pinned top-down for its new
// neighbours (a kit port sits on ONE face, so the multi-lane buses are split per face).  No logic is added: every
// wrapper is wires only around one instance, so the tile's latency, credit loop and pin flops are exactly the closed
// tile's.  The closed views (432 x 129.6 lane, 216 x 151.2 merger) cannot be reused: their lane
// faces point away from the merger, which made every binding ~1,160 um wide.
// ---------------------------------------------------------------------------------------------------------------------

// collector lane tile: dsfd_colt_lane (DEPTH 256, DM 8, RING 1 = the TT-closed ring configuration)
module dsdv_bkcol_l (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,
    input  wire [514:0] c_in,
    input  wire [0:0]   f_cr,
    output wire [512:0] t_w,
    output wire [3:0]   t_f
);
    dsfd_colt_lane #(.DEPTH(256), .RING(1), .DM(8)) u_l (.ck(ck), .rst(rst), .c_in(c_in), .f_cr(f_cr), .t_w(t_w), .t_f(t_f));
endmodule

// collector merger tile: dsfd_colt_mrg (DM 8, PACE 2); S face = lanes 0 / 1 (the S lane row), N face = lanes 2 / 3.
// Its forwarded-clock output vf is not used on the V rung.
module dsdv_bkcol_m (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    input  wire [2*513-1:0] f_w_s,           // {lane 1, lane 0}
    input  wire [2*513-1:0] f_w_n,           // {lane 3, lane 2}
    input  wire [2*4-1:0]   f_f_s,
    input  wire [2*4-1:0]   f_f_n,
    output wire [1:0]       t_cr_s,
    output wire [1:0]       t_cr_n,
    output wire [513:0]     vd
);
    wire [3:0] tcr; wire vf_unused;
    dsfd_colt_mrg #(.DM(8), .PACE(2)) u_m (.ck(ck), .rst(rst), .f_w({f_w_n, f_w_s}), .f_f({f_f_n, f_f_s}), .t_cr(tcr),
        .vd(vd), .vf(vf_unused));
    assign t_cr_s = tcr[1:0]; assign t_cr_n = tcr[3:2];
endmodule
