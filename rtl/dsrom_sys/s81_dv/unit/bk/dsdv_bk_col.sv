`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 / S81U-BK3 (2026-10-17): dsdv_bk_col, the S81-DV row collector unit (plan p4h block bk_col, column 1 V rung),
// as a WIRES-ONLY hardened cluster (no flops of its own) of hard children, each with its own clock tree.
// S81U-BK3 VERTICAL CUT (coordinator 0cj (b), 10-17 ~20:10): the cluster stacks inside the 680-um column (673.92 x 864;
// results/rtl/s81_dv_1016/bk_units_bk2/vcut_plan.json): S row lanes 0 / 1, middle row merger + glue, N row lanes 2 / 3.
//   u_g          dsdv_bk_g        the shared V-rung glue leaf (vstop + V ingress + V egress), middle row E
//   g_l[0..3]    dsdv_bkcol_l     the lane tile (= dsfd_colt_lane DEPTH 256 / DM 8 / RING 1), re-pinned and re-cut
//                                 square-ish (259.2 x 216); N row MX-mirrored
//   u_m          dsdv_bkcol_m     the merger (= dsfd_colt_mrg DM 8 / PACE 2), re-pinned: S face lanes 0/1, N face 2/3
// Every leaf-to-leaf hop is <= ~405 um, so the S81U-BK2 lane relays (2 stages) are gone (-2 edges on the lane path).
// S81U-BK's single flat leaf (50,134 sinks on one root: TT insertion 683.5 ps, spread 157.7 ps) is retired.  Children are
// instantiated WITHOUT parameters: their wrappers fix the hardened configuration (no #() on a hard child).
// Lane tile <-> merger: tile pin flop to pin flop, no station.  That lane -> merger credit loop is internal and
// fixed-latency; no unit port carries credit / ready / back-pressure.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_col #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,       // die reset net (active low)
    input  wire [7:0]    tap_k,       // straps (captured in u_g)
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,        // egress direction: 0 = southbound (vo_s), 1 = northbound (vo_n)
    input  wire [V-1:0]  vi_s,        // rung, S side (northbound arrivals)
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,        // rung, N side (southbound arrivals)
    output wire [V-1:0]  vo_s,
    output wire          fault
);
    wire [514:0] l0, l1, l2, l3; wire [513:0] vd;
`ifdef OT_DSDV_BK_HARD
    dsdv_bk_g #(.VD_PK(0)) u_g (
`else
    dsdv_bk_g #(.V(V), .MUT(MUT), .VD_PK(0)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .ln0(l0), .ln1(l1), .ln2(l2), .ln3(l3), .vd(vd), .fault(fault));
    wire [4*515-1:0] cl = {l3, l2, l1, l0};
    wire [3:0] tcr; wire [4*513-1:0] fw; wire [4*4-1:0] ff;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_l       // lane 0 SW, 1 SE, 2 NW, 3 NE
        dsdv_bkcol_l u_l (.ck(clk), .rst(rst_n), .c_in(cl[515 * g +: 515]), .f_cr(tcr[g]), .t_w(fw[513 * g +: 513]),
            .t_f(ff[4 * g +: 4]));
    end endgenerate
    dsdv_bkcol_m u_m (.ck(clk), .rst(rst_n), .f_w_s(fw[0 +: 2*513]), .f_w_n(fw[2*513 +: 2*513]), .f_f_s(ff[0 +: 8]),
        .f_f_n(ff[8 +: 8]), .t_cr_s(tcr[1:0]), .t_cr_n(tcr[3:2]), .vd(vd));
endmodule
