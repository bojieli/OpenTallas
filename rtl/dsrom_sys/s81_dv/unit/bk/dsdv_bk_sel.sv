`timescale 1ns/1ps
// FAIL-S81-1 11-14 (COORD): station depths default 0 = as built; defined here so file order never matters
// S81-GEOM-OPUS 11-19 (bank-leaf; FABLE-FIX-S81-LEAF netlist trace, main 35d4334b5b42: bk_sel__t2 had 22 core-to-core links,
// 0 stages, 16 over 405 um): OT_BKSEL_A2P = the S81-A2 station profile as ONE bare macro name, because plan verilog_defines take
// bare names only (gen_phys.type_verilog_defines): RC 3, RS 3, RO 4, RLN 3, for the re-placed bk_sel__t2 core layout where every
// control <-> quarter / glue -> quarter link is <= (D + 1) x 405 um.  The control core dsdv_bksel_c MUST be hardened with the same
// macro (XDX = 1 + ceil((RC + RS + QRX) / 2) = 5 with the eco3 QRX 1); quarters unchanged (DMX 0).  Explicit OT_BKSEL_* defines win.
// FABLE-FIX-S81-BKSEL-R2 11-20 (J3 placed bk_sel__t2 BAD: core links 0 stages; 300 um hop cap): OT_BKSEL_A3P = the S81-A2 station
// profile for the 300-um hop cap as ONE bare macro name: RC 5, RS 5, RO 7, RLN 5 (BK-PLACE core layout: control <-> quarter /
// glue -> quarter links <= 1,613 / 1,590 / 2,265 / 1,602 um pin to pin, every hop <= 283 um).  The control core dsdv_bksel_c MUST be
// hardened with the same macro (XDX = 1 + ceil((RC + RS + QRX) / 2) = 7 with the eco3 QRX 1); quarters unchanged (DMX 0).
// Listed before OT_BKSEL_A2P, so A3P wins when both are set; explicit OT_BKSEL_* defines win over both.  Inert when undefined.
`ifdef OT_BKSEL_A3P
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 5
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 5
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 7
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 5
`endif
`endif
`ifdef OT_BKSEL_A2P
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 3
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 3
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 4
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 3
`endif
`endif
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 0
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 0
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 0
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 0
`endif
// S81-CORES-R3 11-17 (S81-DIE-R3 NEEDS-LANE (a)): the hardened quarter parameter set of the dsdv_bksel_q view the die binds,
// written as literals (tools/die_plan/hard_core_param_all.py resolves `ifdef against the bind defines, not macro values).
//   default         = the hq3 view (dsdv_bksel_q defaults: OLL 0, RFH 0, HLAT 0), control QRX 0 (as built)
//   OT_BKQ_ECO3     = the signed eco3 view (kit VERILOG_TOP_PARAMS OLL 2 RFH 2 HLAT 1); RFH 2 adds one input edge in every
//                     quarter, so the control takes QRX 1 (dsdv_bksel_c XDX + ceil(1 / 2): fixed waits +2 edges)
//   OT_BKQ_QRX_MUT  = bench mutant only: eco3 quarters, control left at QRX 0 (under-counts the round trip by 1 edge)
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
    // RF 1: S81-062 RE-FORM (DIE-S81-51/RF-D 11-03): rung transit vi -> vo through the sel unit 3 -> 4 edges (relay +1,
    // vstop FPIPE 3); dv_layer_compile BKSEL_TRANSIT 4, lower_bk FWD 3.  +define+OT_DSDV_BKG_RF0 = the old leaf (benches).
    // RF 2 (form 2, 11-03): + vin LPIPE, ln0..ln3 +1 edge inside the unit (rung transit unchanged); +define+OT_DSDV_BKG_RF1
    // = form 1 (benches).  RF 3 (form 4, 11-03): RF 2 without the negedge out-face (0 cycles); +define+OT_DSDV_BKG_RF2
    // = form 2 (benches).  RF 4 (form 5, 11-03): RF 2 + posedge out-face pin registers, rung transit 4 -> 5 edges
    // (BKSEL_TRANSIT 5, lower_bk OFACE 1), ln0..ln3 +1; +define+OT_DSDV_BKG_RF3 = form 4 (benches).
`ifdef OT_DSDV_BKG_RF0
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(0)) u_g (
`elsif OT_DSDV_BKG_RF1
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(1)) u_g (
`elsif OT_DSDV_BKG_RF2
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(2)) u_g (
`elsif OT_DSDV_BKG_RF3
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(3)) u_g (
`elsif OT_DSDV_BKG_RF4
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(4)) u_g (
`elsif OT_DSDV_BKG_RF5   // RF 5 (form 7a, 11-03): RF 4 + strap negedge in-face + rn copies, 0 edges vs RF 4
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(5)) u_g (
`elsif OT_DSDV_BKG_RF6   // RF 6 (form 7, 11-03): RF 5 + vin LPIPE 2 (lane words +1 inside dsdv_bk_sel; rung edges = RF 4)
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(6)) u_g (
`else   // RF 7 (form 8, 11-03 conservative): RF 6 with slice-local vin copies (dsdv_bk_vin3), 0 edges vs RF 6
    dsdv_bk_g #(.V(V), .MUT(MUT), .RF(7)) u_g (
`endif
`endif
        .clk(clk), .rst_n(rst_n), .tap_k({tap_k[7:3], tap_k[0]}), .sink_k({sink_k[7:3], sink_k[0]}), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_s_r), .vo_s(vo_s), .vi_n(vi_n_r), .vo_n(vo_n), .ln0(l0), .ln1(l1), .ln2(l2), .ln3(l3), .vd(vd), .fault(fault));
    wire [4*515-1:0] ln = {l3, l2, l1, l0};
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire [4*SB-1:0] fs; wire [4*OB-1:0] fo;
    genvar g;
    // S81-A2 plan stations (dsdv_bksel_c.sv header): *_q = quarter side, *_c = control side
    wire [4*CB-1:0] tc_q; wire [3:0] tcr_q; wire [4*SB-1:0] fs_c; wire [4*OB-1:0] fo_c; wire [4*515-1:0] ln_q;
    dsdv_bk_stn #(.W(4*CB + 4), .D(`OT_BKSEL_RC)) u_stn_c (.ck(clk), .d({tc, tcr}), .q({tc_q, tcr_q}));
    dsdv_bk_stn #(.W(4*SB), .D(`OT_BKSEL_RS)) u_stn_s (.ck(clk), .d(fs), .q(fs_c));
    dsdv_bk_stn #(.W(4*OB), .D(`OT_BKSEL_RO)) u_stn_o (.ck(clk), .d(fo), .q(fo_c));
    dsdv_bk_stn #(.W(4*515), .D(`OT_BKSEL_RLN)) u_stn_l (.ck(clk), .d(ln), .q(ln_q));
    generate for (g = 0; g < 4; g = g + 1) begin : g_q       // quarter 0 SW, 1 SE, 2 NW, 3 NE
`ifdef OT_BKQ_ECO3
        dsdv_bksel_q #(.OLL(2), .RFH(2), .HLAT(1)) u_q (.ck(clk), .rst(rst_n), .lane(ln_q[515 * g +: 515]), .f_c(tc_q[CB * g +: CB]),
            .f_cr(tcr_q[g]), .t_s(fs[SB * g +: SB]), .t_o(fo[OB * g +: OB]));
`else
        dsdv_bksel_q u_q (.ck(clk), .rst(rst_n), .lane(ln_q[515 * g +: 515]), .f_c(tc_q[CB * g +: CB]), .f_cr(tcr_q[g]),
            .t_s(fs[SB * g +: SB]), .t_o(fo[OB * g +: OB]));
`endif
    end endgenerate
    // S81-CORES-R3 11-17: the control is bound with the parameter set of its SIGNED view (bksel_c3_1104 rfd6, odb 11f32154:
    // -G OLL=2 SELOH=1 RNF=1 LQH=1, ss29 LEC gold.ys); before this the die took the module defaults (SEARCH_PIPE 1 instead of
    // the hardened 4) and HCPARAM-ALL allowlisted the core.  OT_BKQ_ECO3 adds QRX 1 (the re-signed QRX view).
`ifdef OT_BKQ_ECO3
`ifdef OT_BKQ_QRX_MUT
    dsdv_bksel_c #(.OLL(2), .SELOH(1), .RNF(1), .LQH(1)) u_c (.ck(clk), .rst(rst_n),
`else
    dsdv_bksel_c #(.OLL(2), .SELOH(1), .RNF(1), .LQH(1), .QRX(1)) u_c (.ck(clk), .rst(rst_n),
`endif
`else
    dsdv_bksel_c #(.OLL(2), .SELOH(1), .RNF(1), .LQH(1)) u_c (.ck(clk), .rst(rst_n),
`endif
        .f_s_s(fs_c[0 +: 2*SB]), .f_s_n(fs_c[2*SB +: 2*SB]), .f_o_s(fo_c[0 +: 2*OB]), .f_o_n(fo_c[2*OB +: 2*OB]),
        .t_c_s(tc[0 +: 2*CB]), .t_c_n(tc[2*CB +: 2*CB]), .t_cr_s(tcr[1:0]), .t_cr_n(tcr[3:2]), .vd(vd));
endmodule

// S81-A2: D reset-less register stations (the plan internal_stations model; D = 0: wires)
module dsdv_bk_stn #(parameter integer W = 1, parameter integer D = 0) (input wire ck, input wire [W-1:0] d,
                                                                       output wire [W-1:0] q);
    generate if (D == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] r [0:D-1];
        integer i;
        always @(posedge ck) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
        assign q = r[D-1];
    end endgenerate
endmodule
