`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 (2026-10-17): dsdv_bk_g, the V-rung glue leaf shared by BOTH S81-DV bk units (one master: dsdv_bk_sel and
// dsdv_bk_col differ only in their captured straps).  It is the only new logic of the units:
//   ot_dsdv_vstop  the fixed-latency V-rung stop (rung S side vi_s / vo_s, N side vi_n / vo_n)
//   dsdv_bk_vin    V ingress: rung beats -> 4 lane words {fault, live, data 512, valid} (lane 0 SW, 1 SE, 2 NW, 3 NE)
//   dsdv_bk_vout   V egress: the unit's vd words -> 128 x 512 SRAM buffer -> 2-beat words in compiled drain windows
// The closed tiles of each unit (selector: dsfd_selt_q2 x4 + dsfd_selt_c; collector: dsfd_colt_lane x4 + dsfd_colt_mrg)
// stay hard children of the unit cluster with their own clock trees; this leaf is flop-first / flop-last:
//   ln0..ln3 leave the vin lane registers;  vd   is captured at the pin (vd_q) before the egress buffer (+1 edge vs S81U-BK).
// S81U-BK3 (2026-10-17, coordinator 0cj (b): the units stack VERTICALLY in the 680-um column): one port per lane so the
// kit places each on its own face segment (W face: ln0 low / vd middle / ln2 high; E face: ln1 low / ln3 high), and the
// lane relays are gone (every glue -> tile hop of the vertical cut is <= ~405 um, results/rtl/s81_dv_1016/bk_units_bk2/vcut_plan.json).
// Straps (tap_k, sink_k, ik, ek, uid, eg_n) are captured pins, never parameters.  No port carries credit / ready /
// back-pressure; every violation is a sticky fault.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_g #(
    parameter integer V   = 276,
    parameter integer MUT = 0,
    // COORD ruling 2026-10-24 18:55: the addressed-drain sink is canonical (the BK drain / slice-CTL namespace collision
    // is a functional bug); 0 = the retired transparent-forwarding behaviour, kept only to reproduce old records.
    parameter integer BK_DRAIN_SINK = 1,
    // S81-KITS-RTLC 10-24 (ruling b): VD_PK = 1 (default; the S81 die master under dsdv_bk_sel): vd is the PACKED
    // dsfd_selt_c word {vd[512:502], vd[356:1]} (367 bits); vd[513] (kind msb) and vd[501:357] are constant 0 at
    // the producer (ot_s81ph_sel_tile.sv o_d kinds 3/4/5/7) and vd[0] (rst copy) is never read here: not pins.
    // VD_PK = 0: legacy 514-bit vd.
    parameter integer VD_PK = 1,
    // RF (DIE-S81-51/RF-D 11-03, S81-062 OWNER TWO-STRIKES RE-FORM; two failed full attempts, last routed TT -197.19 /
    // 541 ep on u_vs.bk_uid_c -> 8-b uid compare -> sink cross term -> 276-load vo_s / vo_n select, FF std hold -20.71 /
    // 476 ep on vi_s / vi_n -> stop input flops, rst_n -> rs removal -18):
    //   RF = 1: (a) PIPELINE CUT: ot_dsdv_vstop FPIPE 1 (registered forward decision, +1 edge on vi -> vo and in -> vo,
    //           deliver unchanged): rung transit through this leaf 2 -> 3 edges (dsdv_bk_sel BKSEL_TRANSIT 3 -> 4,
    //           lower_bk FWD 2 -> 3; the drain window LW is relative to the vo edge, unchanged);
    //           (b) NEGEDGE OUT-FACE (uniform out-face ruling 11-03, OLL 2): every output bit leaves a posedge flop through
    //           one negative-edge flop (0 cycles at a rising-edge sampler, receiver hold ~T/2 by construction);
    //           (c) NEGEDGE IN-FACE: vi_s / vi_n / vd land in a negative-edge flop, then the posedge capture flop (0 cycles:
    //           the posedge flop holds the value it held before; pin hold window ~T/2 by construction); rst_n is
    //           sampled by a negedge flop that clears the release synchronizer (reset held >= 64 edges, release edge
    //           unchanged when rst_n rises in the high phase).
    //   RF = 2 (form 2, 11-03: RF-D build 1 CTS TT -152.5 on u_vs.dl_n -> vin lane decode -> lanes[*]): RF 1 + dsdv_bk_vin
    //           LPIPE 1 (deliveries registered, one-hot lane hits pre-decoded): ln0..ln3 +1 edge (V pin -> lane word
    //           3 -> 4); vo and the drain window unchanged vs RF 1 (the selector tail is inside lower_bk TAIL_BUDGET).
    //   RF = 3 (form 4, 11-03: RF 2 at the plan sites routed congestion-free (GRT ov 0) but failed setup_tt -26.76 at the
    //           output ports vo_n / ln*: negedge launch 416.5 + insertion ~426 ps > vclk required 916.4): RF 2 WITHOUT the
    //           negedge out-face (b): every output leaves its existing posedge register (vstop vo regs, vin lane regs,
    //           fault_r); 0 cycles (a rising-edge sampler sees the same value); receiver hold -> parent io_hold check.
    //   RF = 4 (form 5, 11-03, owner pick: RF 3 build rfd4 died in GRT-0183 after repair_design; RF 2 rfd3a negedge out-face
    //           -26.76): RF 2 core + a POSEDGE per-face pin register on every output (vo_s / vo_n / ln* / fault), placed at
    //           its pin by face_flops.tcl (GEOM pin_reg).  +1 cycle on every output: rung transit vi -> vo 4 -> 5
    //           (dv_layer_compile BKSEL_TRANSIT 5, lower_bk OFACE 1, norm_q_report u_bk_sel 5, tb_dsdv_bk_wrap RL 3),
    //           V pin -> lane word 4 -> 5 (inside dsdv_bk_sel), fault +1.  Mutant OT_RFD_MUT_OF4: RF 4 without the face.
    //   RF = 5 (form 7 part a, 11-03; rfd5 FF hold -21.78 sdc / -69.28 std on the posedge strap captures ik / ek / uid /
    //           eg_n / tap_k / sink_k, removal -8.25 rs[1] -> u_vs.vo_s): RF 4 + (a) NEGEDGE IN-FACE on the strap / config
    //           inputs too (as vi / vd: 0 cycles) + the release synchronizer output KEPT-copied per consumer block
    //           (rn_t / rn_s / rn_i / rn_o, same D as rs[1]: 0 edges) so each reset tree starts local.  (A negedge rn as
    //           on bksel_c is NOT used here: rn's recovery slack is +194 ps of a full cycle over a ~3k-load tree; half a
    //           cycle would cost ~416 ps of it.)  0 edges vs RF 4.  Mutant OT_RFD_MUT_SF5 (posedge strap face).
    //   RF = 6 (form 7, 11-03; owner: two strikes -> pay a cycle; rfd5 TT -17.79 u_vin pn_q -> lane words): RF 5 +
    //           dsdv_bk_vin LPIPE 2 (one more per-lane register stage of the selected beat / valid / two-beat error):
    //           ln0..ln3 and fault +1 edge vs RF 5 (V pin -> lane word 5 -> 6, inside dsdv_bk_sel); vo_s / vo_n and
    //           the drain command unchanged (rung transit 5, RL 3: no parent constant changes).  Mutant OT_RFD_MUT_LPS.
    //   RF = 7 (form 8, 11-03, OWNER 18:57 conservative form + COORD 18:59: rfd6 TT -124.58 = u_vin q0 copy -> shared
    //           hv_n -> q1/q2 copies, a cross-slice recurrence): RF 6 with u_vin = dsdv_bk_vin3, the LPIPE 2 calendar with
    //           every per-lane state / select copied LOCALLY per 64-b slice (each slice keeps its own part-0-held copy hv
    //           from its own registered beat bits), and one stage-A beat pair per face side.  0 edges vs RF 6 (cycle
    //           identical).  Mutant OT_RFD_MUT_HD8.
    //   RF = 0: the old form.  dsdv_bk_sel passes RF 7; dsdv_bk_col (VD_PK 0) keeps RF 0.
    parameter integer RF = 0
) (
    input  wire [0:0]        clk,
    input  wire [0:0]        rst_n,       // die reset net (active low)
    // S81-KITS-RTLC 10-25: tap_k / sink_k bits 1 / 2 (kinds K_XQ / K_XB) are never read by ot_dsdv_vstop (it
    // excludes those kinds): packed straps {k[7:3], k[0]}, not pins
    input  wire [5:0]        tap_k,
    input  wire [5:0]        sink_k,
    input  wire [2:0]        ik,
    input  wire [2:0]        ek,
    input  wire [7:0]        uid,
    input  wire [0:0]        eg_n,        // egress direction: 0 = southbound (vo_s), 1 = northbound (vo_n)
    input  wire [V-1:0]      vi_s,
    output wire [V-1:0]      vo_s,
    input  wire [V-1:0]      vi_n,
    output wire [V-1:0]      vo_n,
    output wire [514:0]      ln0,         // lane words {fault, live, data 512, valid}: lane 0 SW, 1 SE, 2 NW, 3 NE
    output wire [514:0]      ln1,
    output wire [514:0]      ln2,
    output wire [514:0]      ln3,
    input  wire [(VD_PK ? 366 : 513):0] vd,   // the merger / select control's vd {data 512, valid, rst} (VD_PK: packed)
    output wire [0:0]        fault
);
    // ---------------------------------------------------------------- RF: negedge in-face (vi_s / vi_n / vd / rst_n)
    wire [V-1:0] vi_s_f, vi_n_f; wire [(VD_PK ? 366 : 513):0] vd_f; wire rst_f;
    generate if (RF != 0) begin : g_ifn
        reg [V-1:0] a_s, a_n; reg [(VD_PK ? 366 : 513):0] a_d; reg a_r;
        always @(negedge clk[0]) begin a_s <= vi_s; a_n <= vi_n; a_d <= vd; a_r <= rst_n[0]; end
        assign vi_s_f = a_s; assign vi_n_f = a_n; assign vd_f = a_d; assign rst_f = a_r;
    end else begin : g_ifw
        assign vi_s_f = vi_s; assign vi_n_f = vi_n; assign vd_f = vd; assign rst_f = rst_n[0];
    end endgenerate
    // ---------------------------------------------------------------- RF: out-face (vo_s / vo_n / ln* / fault): 1/2 negedge, 4 posedge
    wire [V-1:0] vo_s_r, vo_n_r; wire [4*515-1:0] ln; reg [0:0] fault_r;
    generate if (RF == 1 || RF == 2) begin : g_onf
        reg [V-1:0] o_s, o_n; reg [4*515-1:0] o_l; reg o_f;
        always @(negedge clk[0]) begin o_s <= vo_s_r; o_n <= vo_n_r; o_l <= ln; o_f <= fault_r[0]; end
        assign vo_s = o_s; assign vo_n = o_n; assign {ln3, ln2, ln1, ln0} = o_l; assign fault = o_f;
`ifdef OT_RFD_MUT_OF3   // bench mutant: RF 3 keeps a POSEDGE out-face (+1 edge on every output)
    end else if (RF == 3) begin : g_onm
        reg [V-1:0] o_s, o_n; reg [4*515-1:0] o_l; reg o_f;
        always @(posedge clk[0]) begin o_s <= vo_s_r; o_n <= vo_n_r; o_l <= ln; o_f <= fault_r[0]; end
        assign vo_s = o_s; assign vo_n = o_n; assign {ln3, ln2, ln1, ln0} = o_l; assign fault = o_f;
`endif
`ifndef OT_RFD_MUT_OF4   // bench mutant: RF 4 without its posedge out-face (0 cycles instead of +1)
    end else if (RF >= 4) begin : g_onp
        reg [V-1:0] o_s, o_n; reg [4*515-1:0] o_l; reg o_f;
        always @(posedge clk[0]) begin o_s <= vo_s_r; o_n <= vo_n_r; o_l <= ln; o_f <= fault_r[0]; end
        assign vo_s = o_s; assign vo_n = o_n; assign {ln3, ln2, ln1, ln0} = o_l; assign fault = o_f;
`endif
    end else begin : g_onw
        assign vo_s = vo_s_r; assign vo_n = vo_n_r; assign {ln3, ln2, ln1, ln0} = ln; assign fault = fault_r;
    end endgenerate
    reg [1:0] rs;
    always @(posedge clk[0] or negedge rst_f) if (!rst_f) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn, rn_s, rn_i, rn_o;
    generate if (RF >= 5) begin : g_rnc
        (* keep = "true" *) reg r_t, r_s, r_i, r_o;      // kept copies of rs[1] (same D, same reset)
        always @(posedge clk[0] or negedge rst_f) if (!rst_f) {r_t, r_s, r_i, r_o} <= 4'd0; else {r_t, r_s, r_i, r_o} <= {4{rs[0]}};
        assign rn = r_t, rn_s = r_s, rn_i = r_i, rn_o = r_o;
    end else begin : g_rn1
        assign rn = rs[1], rn_s = rs[1], rn_i = rs[1], rn_o = rs[1];
    end endgenerate
    // RF 5 (a): negedge in-face on the strap / config inputs (0 cycles, as vi / vd)
    wire [2:0] ik_f, ek_f; wire [7:0] uid_f; wire egn_f; wire [5:0] tap_f, sink_f;
    generate if (RF >= 5) begin : g_sfn
        reg [2:0] a_ik, a_ek; reg [7:0] a_uid; reg a_eg; reg [5:0] a_tap, a_sink;
`ifdef OT_RFD_MUT_SF5   // bench mutant: the strap face is a posedge flop (+1 edge)
        always @(posedge clk[0]) begin a_ik <= ik; a_ek <= ek; a_uid <= uid; a_eg <= eg_n[0]; a_tap <= tap_k; a_sink <= sink_k; end
`else
        always @(negedge clk[0]) begin a_ik <= ik; a_ek <= ek; a_uid <= uid; a_eg <= eg_n[0]; a_tap <= tap_k; a_sink <= sink_k; end
`endif
        assign ik_f = a_ik, ek_f = a_ek, uid_f = a_uid, egn_f = a_eg, tap_f = a_tap, sink_f = a_sink;
    end else begin : g_sfw
        assign ik_f = ik, ek_f = ek, uid_f = uid, egn_f = eg_n[0], tap_f = tap_k, sink_f = sink_k;
    end endgenerate
    reg [2:0] ik_c, ek_c; reg [7:0] uid_c; reg egn_c;
    always @(posedge clk[0]) begin ik_c <= ik_f; ek_c <= ek_f; uid_c <= uid_f; egn_c <= egn_f; end
    wire [513:0] vdu;                                  // vd unpacked (VD_PK: dropped constant bits are 0)
    reg vdv; reg [511:0] vdd;                          // vd captured at the pin
    always @(posedge clk[0] or negedge rn) if (!rn) vdv <= 1'b0; else vdv <= vdu[1];
`ifdef OT_RTLC_MUT_BKVD   // bench mutant: the packed kind / seg_tag field lands one bit high
    generate if (VD_PK) begin : g_vpk assign vdu = {vd_f[366:356], 1'b0, 145'd0, vd_f[355:0], 1'b0}; end
`else
    generate if (VD_PK) begin : g_vpk assign vdu = {1'b0, vd_f[366:356], 145'd0, vd_f[355:0], 1'b0}; end
`endif
    else begin : g_vfl assign vdu = vd_f; end endgenerate
    always @(posedge clk[0]) vdd <= vdu[513:2];
    wire dnv, dsv; wire [V-1:0] dn, ds, ob; wire vs_f, vi_f, vo_f, ov;
    ot_dsdv_vstop #(.V(V), .BK_DRAIN_SINK(BK_DRAIN_SINK), .FPIPE(RF != 0)) u_vs (.clk(clk[0]), .rst_n(rn_s), .tap_k({tap_f[5:1], 2'b00, tap_f[0]}), .sink_k({sink_f[5:1], 2'b00, sink_f[0]}), .bk_uid(uid_f), .vi_s(vi_s_f), .vo_n(vo_n_r),
        .vi_n(vi_n_f), .vo_s(vo_s_r), .dl_nv(dnv), .dl_n(dn), .dl_sv(dsv), .dl_s(ds),
        .in_nv(ov && egn_c), .in_n(ob), .in_sv(ov && !egn_c), .in_s(ob), .fault(vs_f));
    wire drv; wire [7:0] drn, drd;
    generate if (RF >= 7) begin : g_vin3
    dsdv_bk_vin3 #(.V(V), .MUT(MUT)) u_vin (.clk(clk[0]), .rst_n(rn_i), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(ln), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    end else begin : g_vin
    dsdv_bk_vin #(.V(V), .MUT(MUT), .LPIPE((RF >= 6) ? 2 : (RF >= 2) ? 1 : 0)) u_vin (.clk(clk[0]), .rst_n(rn_i), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(ln), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    end endgenerate
    dsdv_bk_vout #(.V(V), .MUT(MUT)) u_vout (.clk(clk[0]), .rst_n(rn_o), .ek(ek_c), .w_v(vdv), .w_d(vdd),
        .dr_v(drv), .dr_n(drn), .dr_d(drd), .o_v(ov), .o_b(ob), .fault(vo_f));
    always @(posedge clk[0] or negedge rn) if (!rn) fault_r <= 1'b0; else fault_r <= vs_f | vi_f | vo_f;
endmodule
