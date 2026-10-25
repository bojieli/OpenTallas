`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 / S81U-BK3 (2026-10-17): dsdv_bk_sel, the S81-DV index selector unit (plan p4h block bk_sel, column 4 V
// rung), as a WIRES-ONLY hardened cluster (no flops of its own) of hard children, each with its own clock tree.
// S81U-BK3 VERTICAL CUT (coordinator 0cj (b), 10-17 ~20:10): the cluster stacks inside the 680-um column (673.92 x
// 1,192.32; results/rtl/s81_dv_1016/bk_units_bk2/vcut_plan.json): S row quarters 0 / 1, middle row control + glue,
// N row quarters 2 / 3.
//   u_g          dsdv_bk_g        the shared V-rung glue leaf (vstop + V ingress + V egress), middle row E
//   g_q[0..3]    dsdv_bksel_q     the quarter tile (= dsfd_selt_q2 DM 4, SAFE, CMP_RETIME, PIPE2, QIO, ILD, FRPR),
//                                 re-pinned and re-cut (280.8 x 432); N row MX-mirrored
//   u_c          dsdv_bksel_c     = the UNCHANGED dsfd_selt_c configured for PIPE2 / QIO quarters (MRG_PIPE, RQPIPE,
//                                 SLAT 4, XDX 1), quarter bundles split per face (S: quarters 0 / 1, N: 2 / 3).
//                                 Its 26,013 sinks FAIL the clock rule (s81dvbk_selc: TT insertion 347.4 ps): it needs a
//                                 control / landing split before closure (decision owed, see the lane file).
// Every leaf-to-leaf hop is <= ~405 um, so the S81U-BK2 lane relays (3 stages) are gone (-3 edges on the lane path).
// S81-TILES8/bk (10-18, spec tools/ref_tile/specs_s81dvbk/s81dvbk_selv.json rung_relays, coordinator S81-TILES6 10-17):
// the sel rung segment face -> glue is ~518-562 um (> 405 planned reach), so each input direction lands in ONE closed
// 276-b relay inside the cluster: u_rs = dsfd_dvrly_276_SN (s81dv_rly_276_sn) at the S face (518.4, 43.2) on vi_s,
// u_rn = dsfd_dvrly_276_NS (s81dv_rly_276_ns) at the N face (518.4, 1252.8) on vi_n.  LATENCY: +1 rung cycle per
// direction through the sel unit (vi -> vo through beats 2 -> 3 edges; the drain CTL reaches the vstop 1 cycle later,
// so the egress window moves +1 with it).  The compiler's rung schedule (SLAT / rung arrival) takes the +1; the bench
// model (tb_dsdv_bk_wrap RL) carries it.  ck_o is unused here (forwarded clock only between die stations).  The col
// unit is unchanged (no relay).  The cluster now has 2 x 276 relay flops of its own (inside hard relay children).
// Hard children carry no #(): their wrappers fix the hardened configuration.  The quarter -> control credit loop is
// internal and fixed-latency; no unit port carries credit / ready / back-pressure.  MUT (bench only) 1..4:
// dsdv_bk_v.sv mutants.
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
    wire [514:0] l0, l1, l2, l3; wire [366:0] vd;   // packed (bk_g VD_PK)
    wire [V-1:0] vi_s_r, vi_n_r; wire rck_s, rck_n;      // rung relays (+1 cycle per direction); ck_o unused
    dsfd_dvrly_276_SN u_rs (.ck(clk), .rs(rst_n), .i(vi_s), .o(vi_s_r), .ck_o(rck_s));
    dsfd_dvrly_276_NS u_rn (.ck(clk), .rs(rst_n), .i(vi_n), .o(vi_n_r), .ck_o(rck_n));
`ifdef OT_DSDV_BK_HARD
    dsdv_bk_g u_g (
`else
    dsdv_bk_g #(.V(V), .MUT(MUT)) u_g (
`endif
        .clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s_r), .vo_s(vo_s), .vi_n(vi_n_r), .vo_n(vo_n), .ln0(l0), .ln1(l1), .ln2(l2), .ln3(l3), .vd(vd), .fault(fault));
    wire [4*515-1:0] ln = {l3, l2, l1, l0};
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire [4*SB-1:0] fs; wire [4*OB-1:0] fo;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_q       // quarter 0 SW, 1 SE, 2 NW, 3 NE
        dsdv_bksel_q u_q (.ck(clk), .rst(rst_n), .lane(ln[515 * g +: 515]), .f_c(tc[CB * g +: CB]), .f_cr(tcr[g]),
            .t_s(fs[SB * g +: SB]), .t_o(fo[OB * g +: OB]));
    end endgenerate
    dsdv_bksel_c u_c (.ck(clk), .rst(rst_n),
        .f_s_s(fs[0 +: 2*SB]), .f_s_n(fs[2*SB +: 2*SB]), .f_o_s(fo[0 +: 2*OB]), .f_o_n(fo[2*OB +: 2*OB]),
        .t_c_s(tc[0 +: 2*CB]), .t_c_n(tc[2*CB +: 2*CB]), .t_cr_s(tcr[1:0]), .t_cr_n(tcr[3:2]), .vd(vd));
endmodule
