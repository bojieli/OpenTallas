`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 (2026-10-17): dsdv_bk_sel, the S81-DV index selector unit (plan p4h block bk_sel, column 4 V rung), as a
// WIRES-ONLY hardened cluster (no flops of its own) of hard children, each with its own clock tree:
//   u_g          dsdv_bk_g        the shared V-rung glue leaf (vstop + V ingress + V egress), S of the control
//   u_rw / u_re  dsdv_bksel_lr    lane relays (3 stages) beside the W / E quarter pairs (the quarter tiles' lane face
//                                 points AWAY from the control)
//   g_q[0..3]    dsfd_selt_q2     the CLOSED quarter tile (physical/redesign_ds/routes/s81b-selt_q2-frprildb-4b0140c9a-tc-rd:
//                                 DM 4, SAFE, CMP_RETIME, PIPE2, QIO, ILD, FRPR); E pair MY-mirrored
//   u_c          dsdv_bksel_c     = the UNCHANGED dsfd_selt_c configured for PIPE2 / QIO quarters (MRG_PIPE, RQPIPE,
//                                 SLAT 4, XDX 1) with its quarter bundles split per face (W: quarters 0 / 2, E: 1 / 3).
//                                 NOT CLOSED in this configuration (s81b-selt_c-xdx-mm2-9ac26e269-tt-f5-lvt-hm0
//                                 NEEDS_RTL TT -28.4 / FF -13.0); the closed dsfd_selt_c (mrg, SLAT 0 / XDX 0) pairs
//                                 only with plain quarters, so this child needs its own closure (kit s81dvbk_selc).
// S81U-BK's flattened leaves (sel_lm 30,768 sinks: TT insertion 564.4 ps, spread 94.7 ps; sel_lq = two 44.6k-sink
// quarters) are retired.  Hard children carry no #() under OT_DSDV_BK_HARD (their hardened configuration is the view);
// the RTL bench elaborates the same configuration explicitly.  The quarter -> control credit loop is internal and
// fixed-latency; no unit port carries credit / ready / back-pressure.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_sel #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    output wire          fault
);
    localparam integer CB = 66, SB = 865, OB = 354;   // = `SELT_CB / `SELT_SB / `SELT_OB (ot_s81ph_sel_tile.sv)
    wire [2*515-1:0] glw, gle; wire [4*515-1:0] ln; wire [513:0] vd;
`ifdef OT_DSDV_BK_HARD
    dsdv_bk_g u_g (
`else
    dsdv_bk_g #(.V(V), .MUT(MUT)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .ln_w(glw), .ln_e(gle), .vd(vd), .fault(fault));
    wire [1029:0] rwo, reo;
    dsdv_bksel_lr u_rw (.ck(clk), .i(glw), .o(rwo));
    dsdv_bksel_lr u_re (.ck(clk), .i(gle), .o(reo));
    assign ln = {reo[515 +: 515], rwo[515 +: 515], reo[0 +: 515], rwo[0 +: 515]};
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire [4*SB-1:0] fs; wire [4*OB-1:0] fo;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_q       // quarter 0 SW, 1 SE, 2 NW, 3 NE
`ifdef OT_DSDV_BK_HARD
        dsfd_selt_q2 u_q (
`else
        dsfd_selt_q2 #(.DM(4), .CMP_RETIME(1), .PIPE2(1), .QIO(1), .ILD(1), .FRPR(1)) u_q (
`endif
            .ck(clk), .rst(rst_n), .lane(ln[515 * g +: 515]), .f_c(tc[CB * g +: CB]), .f_cr(tcr[g]),
            .t_s(fs[SB * g +: SB]), .t_o(fo[OB * g +: OB]));
    end endgenerate
    dsdv_bksel_c u_c (.ck(clk), .rst(rst_n),
        .f_s_w({fs[2*SB +: SB], fs[0 +: SB]}), .f_s_e({fs[3*SB +: SB], fs[1*SB +: SB]}),
        .f_o_w({fo[2*OB +: OB], fo[0 +: OB]}), .f_o_e({fo[3*OB +: OB], fo[1*OB +: OB]}),
        .t_c_w({tc[2*CB +: CB], tc[0 +: CB]}), .t_c_e({tc[3*CB +: CB], tc[1*CB +: CB]}),
        .t_cr_w({tcr[2], tcr[0]}), .t_cr_e({tcr[3], tcr[1]}), .vd(vd));
endmodule

