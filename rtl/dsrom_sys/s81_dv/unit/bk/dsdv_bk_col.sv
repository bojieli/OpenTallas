`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 (2026-10-17): dsdv_bk_col, the S81-DV row collector unit (plan p4h block bk_col, column 1 V rung), as a
// WIRES-ONLY hardened cluster (no flops of its own) of hard children, each with its own clock tree:
//   u_g          dsdv_bk_g        the shared V-rung glue leaf (vstop + V ingress + V egress), S of the merger
//   u_rw / u_re  dsdv_bkcol_lr    lane relays (2 stages) beside the W / E lane-tile pairs (the closed lane tiles'
//                                 c_in face points AWAY from the merger, so the glue reaches it through a relay)
//   g_l[0..3]    dsfd_colt_lane   the CLOSED lane tile (physical/s81_ph_views/closed/dsfd_colt_lane, 7345266ce-e:
//                                 DEPTH 256, DM 8, shift head buffer); E pair MY-mirrored
//   u_m          dsfd_colt_mrg    the CLOSED merger (physical/s81_ph_views/closed/dsfd_colt_mrg, cd3337221-b: DM 8, PACE 2)
// S81U-BK's single flat leaf (50,134 sinks on one root: TT insertion 683.5 ps, spread 157.7 ps) is retired.  Children are
// instantiated WITHOUT parameters: their closed defaults ARE the hardened configuration (no #() on a hard child).
// Lane tile <-> merger: closed-tile pin flop to pin flop, no station (ot_s81ph_col_t had HOPS 5; DM 8 covers the shorter
// credit round trip).  That lane -> merger credit loop is internal and fixed-latency; no unit port carries credit / ready
// / back-pressure.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
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
    wire [2*515-1:0] glw, gle; wire [4*515-1:0] cl; wire [513:0] vd; wire vf_fwd;
`ifdef OT_DSDV_BK_HARD
    dsdv_bk_g u_g (
`else
    dsdv_bk_g #(.V(V), .MUT(MUT)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .ln_w(glw), .ln_e(gle), .vd(vd), .fault(fault));
    // relays: W pair = lanes 0 (SW), 2 (NW); E pair = lanes 1 (SE), 3 (NE)
    wire [1029:0] rwo, reo;
    dsdv_bkcol_lr u_rw (.ck(clk), .i(glw), .o(rwo));
    dsdv_bkcol_lr u_re (.ck(clk), .i(gle), .o(reo));
    assign cl = {reo[515 +: 515], rwo[515 +: 515], reo[0 +: 515], rwo[0 +: 515]};
    wire [3:0] tcr; wire [4*513-1:0] fw; wire [4*4-1:0] ff;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_l       // lane 0 SW, 1 SE, 2 NW, 3 NE
        dsfd_colt_lane u_l (.ck(clk), .rst(rst_n), .c_in(cl[515 * g +: 515]), .f_cr(tcr[g]), .t_w(fw[513 * g +: 513]),
            .t_f(ff[4 * g +: 4]));
    end endgenerate
    dsfd_colt_mrg u_m (.ck(clk), .rst(rst_n), .f_w(fw), .f_f(ff), .t_cr(tcr), .vd(vd), .vf(vf_fwd));
endmodule
