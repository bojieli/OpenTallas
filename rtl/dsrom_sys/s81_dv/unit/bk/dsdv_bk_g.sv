`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK2 (2026-10-17): dsdv_bk_g, the V-rung glue leaf shared by BOTH S81-DV bk units (one master: dsdv_bk_sel and
// dsdv_bk_col differ only in their captured straps).  It is the only new logic of the units:
//   ot_dsdv_vstop  the fixed-latency V-rung stop (rung S side vi_s / vo_s, N side vi_n / vo_n)
//   dsdv_bk_vin    V ingress: rung beats -> 4 lane words {fault, live, data 512, valid} (lane 0 SW, 1 SE, 2 NW, 3 NE)
//   dsdv_bk_vout   V egress: the unit's vd words -> 128 x 512 SRAM buffer -> 2-beat words in compiled drain windows
// The closed tiles of each unit (selector: dsfd_selt_q2 x4 + dsfd_selt_c; collector: dsfd_colt_lane x4 + dsfd_colt_mrg)
// stay hard children of the unit cluster with their own clock trees; this leaf is flop-first / flop-last:
//   ln_w / ln_e leave the vin lane registers;  vd   is captured at the pin (vd_q) before the egress buffer (+1 edge vs S81U-BK).
// Straps (tap_k, sink_k, ik, ek, uid, eg_n) are captured pins, never parameters.  No port carries credit / ready /
// back-pressure; every violation is a sticky fault.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_g #(
    parameter integer V   = 276,
    parameter integer MUT = 0
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
    output wire [2*515-1:0]  ln_w,        // lane words {lane 2 NW, lane 0 SW} to the W relay / tile pair (W face)
    output wire [2*515-1:0]  ln_e,        // lane words {lane 3 NE, lane 1 SE} to the E relay / tile pair (E face)
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
    ot_dsdv_vstop #(.V(V)) u_vs (.clk(clk[0]), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dnv), .dl_n(dn), .dl_sv(dsv), .dl_s(ds),
        .in_nv(ov && egn_c), .in_n(ob), .in_sv(ov && !egn_c), .in_s(ob), .fault(vs_f));
    wire drv; wire [7:0] drn, drd; wire [4*515-1:0] ln;
    assign ln_w = {ln[2*515 +: 515], ln[0 +: 515]}; assign ln_e = {ln[3*515 +: 515], ln[1*515 +: 515]};
    dsdv_bk_vin #(.V(V), .MUT(MUT)) u_vin (.clk(clk[0]), .rst_n(rn), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(ln), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    dsdv_bk_vout #(.V(V), .MUT(MUT)) u_vout (.clk(clk[0]), .rst_n(rn), .ek(ek_c), .w_v(vdv), .w_d(vdd),
        .dr_v(drv), .dr_n(drn), .dr_d(drd), .o_v(ov), .o_b(ob), .fault(vo_f));
    always @(posedge clk[0] or negedge rn) if (!rn) fault <= 1'b0; else fault <= vs_f | vi_f | vo_f;
endmodule

// Lane relay leaf: two lane words (2 x 515) through STG registers (no reset: the glue's lane registers are 0 in reset,
// so the pipe is flushed long before the tiles leave theirs).  It sits beside a lane / quarter pair whose lane pins face
// AWAY from the merger / control (the closed tiles' c_in / lane face), so the glue -> tile hop stays <= ~405 um.
module dsdv_bk_lr_core #(parameter integer STG = 2) (
    input  wire [0:0]        ck,
    input  wire [2*515-1:0]  i,
    output wire [2*515-1:0]  o
);
    reg [2*515-1:0] p [0:STG-1];
    integer k;
    always @(posedge ck[0]) begin p[0] <= i; for (k = 1; k < STG; k = k + 1) p[k] <= p[k-1]; end
    assign o = p[STG-1];
endmodule
// collector relay (beside a 2 x 129.6 um lane-tile stack): 2 stages
module dsdv_bkcol_lr (input wire [0:0] ck, input wire [2*515-1:0] i, output wire [2*515-1:0] o);
    dsdv_bk_lr_core #(.STG(2)) u_p (.ck(ck), .i(i), .o(o));
endmodule
// selector relay (beside a 2 x 280.8 um quarter-tile stack): 3 stages
module dsdv_bksel_lr (input wire [0:0] ck, input wire [2*515-1:0] i, output wire [2*515-1:0] o);
    dsdv_bk_lr_core #(.STG(3)) u_p (.ck(ck), .i(i), .o(o));
endmodule
