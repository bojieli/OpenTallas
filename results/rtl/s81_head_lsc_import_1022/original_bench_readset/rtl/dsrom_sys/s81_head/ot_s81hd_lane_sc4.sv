`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HEAD LANE (b) STACKED, FALLBACK (4 sub-children; STW-S81c-COLLA2-LANE 10-22): the same frozen ot_s81hd_lane as
// ot_s81hd_lane_sc6.sv with a DIFFERENT split: fewer, taller TX children and one combined control + RX child.
//   u_t0 / u_t1  ot_s81hd_lsc_t12 (ONE master x2): TX slices 0..11 / 12..23, bits 0..383
//   u_t2         ot_s81hd_lsc_t11: TX slices 24..34 (bits 384..552), lo_v / TX overflow from slice 34
//   u_r          ot_s81hd_lsc_rf: kf copies (one pair per TX child), all RX bits, credit check, faults, resets
//   rxen         the one parent flop
// Stack (S -> N, 43.2-um lattice, >= 21.6-um channels): t0 t1 t2 (108 tall) r (194.4).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_lane (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          chb,
    input  wire [513:0]  rx,
    output wire [511:0]  tx,
    input  wire          tx_v,
    input  wire [552:0]  tx_d,
    output wire          rx_v,
    output wire [552:0]  rx_d,
    output wire [3:0]    flt
);
    wire r_lane, r_misc;
    reg rxen;
    always @(posedge ck or negedge r_misc) if (!r_misc) rxen <= 1'b0; else rxen <= 1'b1;
    wire [514:0] lrx = {rx[512], rx[513], rx[511:0], rxen};
    wire lo_v, lo_r, li_v, li_r; wire [552:0] lo_d, li_d; wire [2:0] lf;
    dsfd_coll_lane_w_safe8_ntf u_ln (.ck(ck), .rs(r_lane), .chb(chb), .rx(lrx), .tx(tx), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(lf));
    wire [2:0] tvk, crk; wire ovf_t;
`ifdef OT_S81HD_LSC_MUT_SKEW
    reg tv1_late; always @(posedge ck) tv1_late <= tvk[1];
    wire tv1_use = tv1_late;
`else
    wire tv1_use = tvk[1];
`endif
    ot_s81hd_lsc_t12 u_t0 (.ck(ck), .rst_n(rst_n), .td(tx_d[191:0]),   .tvk(tvk[0]), .crk(crk[0]), .lod(lo_d[191:0]));
    ot_s81hd_lsc_t12 u_t1 (.ck(ck), .rst_n(rst_n), .td(tx_d[383:192]), .tvk(tv1_use), .crk(crk[1]), .lod(lo_d[383:192]));
    ot_s81hd_lsc_t11 u_t2 (.ck(ck), .rst_n(rst_n), .td(tx_d[552:384]), .tvk(tvk[2]), .crk(crk[2]), .lod(lo_d[552:384]),
        .lv(lo_v), .ovf(ovf_t));
    ot_s81hd_lsc_rf u_r (.ck(ck), .rst_n(rst_n), .tx_v(tx_v), .lo_r(lo_r), .tvk(tvk), .crk(crk), .li_v(li_v), .li_r(li_r),
        .li_d(li_d), .rx_d(rx_d), .rx_v(rx_v), .lf(lf), .ovf_t(ovf_t), .flt(flt), .r_lane(r_lane), .r_misc_o(r_misc));
`ifndef SYNTHESIS
`ifdef OT_S81HD_LANE_CHK
    wire [34:0] lov_all = {u_t2.lov_s, u_t1.lov_s, u_t0.lov_s};
    always @(posedge ck) if (u_t0.rr[0] && (lov_all != {35{1'b0}}) && (lov_all != {35{1'b1}}))
        $fatal(1, "ot_s81hd_lane (sc4): TX slices out of lock step");
`endif
`endif
endmodule
