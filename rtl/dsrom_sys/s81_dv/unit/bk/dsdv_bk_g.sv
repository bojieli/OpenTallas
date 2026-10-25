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
    parameter integer BK_DRAIN_SINK = 1
) (
    input  wire [0:0]        clk,
    input  wire [0:0]        rst_n,       // die reset net (active low)
    input  wire [7:0]        tap_k,
    input  wire [7:0]        sink_k,
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
    input  wire [513:0]      vd,          // the merger / select control's vd {data 512, valid, rst}
    output reg  [0:0]        fault
);
    reg [1:0] rs;
    always @(posedge clk[0] or negedge rst_n[0]) if (!rst_n[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [2:0] ik_c, ek_c; reg [7:0] uid_c; reg egn_c;
    always @(posedge clk[0]) begin ik_c <= ik; ek_c <= ek; uid_c <= uid; egn_c <= eg_n[0]; end
    reg vdv; reg [511:0] vdd;                          // vd captured at the pin
    always @(posedge clk[0] or negedge rn) if (!rn) vdv <= 1'b0; else vdv <= vd[1];
    always @(posedge clk[0]) vdd <= vd[513:2];
    wire dnv, dsv; wire [V-1:0] dn, ds, ob; wire vs_f, vi_f, vo_f, ov;
    ot_dsdv_vstop #(.V(V), .BK_DRAIN_SINK(BK_DRAIN_SINK)) u_vs (.clk(clk[0]), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k), .bk_uid(uid), .vi_s(vi_s), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dnv), .dl_n(dn), .dl_sv(dsv), .dl_s(ds),
        .in_nv(ov && egn_c), .in_n(ob), .in_sv(ov && !egn_c), .in_s(ob), .fault(vs_f));
    wire drv; wire [7:0] drn, drd; wire [4*515-1:0] ln;
    assign ln0 = ln[0 +: 515]; assign ln1 = ln[515 +: 515]; assign ln2 = ln[2*515 +: 515]; assign ln3 = ln[3*515 +: 515];
    dsdv_bk_vin #(.V(V), .MUT(MUT)) u_vin (.clk(clk[0]), .rst_n(rn), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(ln), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    dsdv_bk_vout #(.V(V), .MUT(MUT)) u_vout (.clk(clk[0]), .rst_n(rn), .ek(ek_c), .w_v(vdv), .w_d(vdd),
        .dr_v(drv), .dr_n(drn), .dr_d(drd), .o_v(ov), .o_b(ob), .fault(vo_f));
    always @(posedge clk[0] or negedge rn) if (!rn) fault <= 1'b0; else fault <= vs_f | vi_f | vo_f;
endmodule
