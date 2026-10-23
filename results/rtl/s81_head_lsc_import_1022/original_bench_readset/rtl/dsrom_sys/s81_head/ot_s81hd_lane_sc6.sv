`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HEAD LANE (b) STACKED, MAIN (6 sub-children; STW-S81c-COLLA2-LANE 10-22): ot_s81hd_lane with the static adapter as
// STACKED hard sub-children (ot_s81hd_lsc_parts.sv), each with its own local CTS root.  Same module name, ports,
// protocol and per-bit edges as ot_s81hd_lane.sv (frozen interface):
//   u_ln             dsfd_coll_lane_w_safe8_ntf (closed view, unchanged)
//   u_t0 / u_t1 / u_t2  ot_s81hd_lsc_t9 (ONE master x3): TX slices 0..8 / 9..17 / 18..26, bits 0..431
//   u_t3             ot_s81hd_lsc_t8: TX slices 27..34 (bits 432..552), lo_v / TX overflow from slice 34
//   u_r0             ot_s81hd_lsc_r0m: kf copies (one pair per TX child), RX bits 0..287, credit check, faults, resets
//   u_r1             ot_s81hd_lsc_r1m: RX bits 288..552
//   rxen             the one parent flop (lane rx word valid; as ot_s81hd_lane_ha.sv)
// Stack (S -> N, 43.2-um lattice, >= 21.6-um channels): t0 t1 t2 t3 (64.8 tall) r0 (108) r1 (129.6).
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
    wire [3:0] tvk, crk; wire ovf_t;
    wire [3:0] tvk_t = tvk;
`ifdef OT_S81HD_LSC_MUT_SKEW
    // MUTANT (sim only): the kf -> t1 seam lands one cycle late (t1 out of lock step with its neighbours)
    reg tv1_late; always @(posedge ck) tv1_late <= tvk[1];
    wire tv1_use = tv1_late;
`else
    wire tv1_use = tvk_t[1];
`endif
    ot_s81hd_lsc_t9 u_t0 (.ck(ck), .rst_n(rst_n), .td(tx_d[143:0]),   .tvk(tvk_t[0]), .crk(crk[0]), .lod(lo_d[143:0]));
    ot_s81hd_lsc_t9 u_t1 (.ck(ck), .rst_n(rst_n), .td(tx_d[287:144]), .tvk(tv1_use),  .crk(crk[1]), .lod(lo_d[287:144]));
    ot_s81hd_lsc_t9 u_t2 (.ck(ck), .rst_n(rst_n), .td(tx_d[431:288]), .tvk(tvk_t[2]), .crk(crk[2]), .lod(lo_d[431:288]));
    ot_s81hd_lsc_t8 u_t3 (.ck(ck), .rst_n(rst_n), .td(tx_d[552:432]), .tvk(tvk_t[3]), .crk(crk[3]), .lod(lo_d[552:432]),
        .lv(lo_v), .ovf(ovf_t));
    ot_s81hd_lsc_r0m u_r0 (.ck(ck), .rst_n(rst_n), .tx_v(tx_v), .lo_r(lo_r), .tvk(tvk), .crk(crk), .li_v(li_v), .li_r(li_r),
        .li_d(li_d[287:0]), .rx_d(rx_d[287:0]), .rx_v(rx_v), .lf(lf), .ovf_t(ovf_t), .flt(flt), .r_lane(r_lane),
        .r_misc_o(r_misc));
    ot_s81hd_lsc_r1m u_r1 (.ck(ck), .li_d(li_d[552:288]), .rx_d(rx_d[552:288]));
`ifndef SYNTHESIS
`ifdef OT_S81HD_LANE_CHK
    // every TX slice of every sub-child in lock step (the original single-adapter check, across the seams)
    wire [34:0] lov_all = {u_t3.lov_s, u_t2.lov_s, u_t1.lov_s, u_t0.lov_s};
    always @(posedge ck) if (u_t0.rr[0] && (lov_all != {35{1'b0}}) && (lov_all != {35{1'b1}}))
        $fatal(1, "ot_s81hd_lane (sc6): TX slices out of lock step");
`endif
`endif
endmodule
