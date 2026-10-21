`timescale 1ns/1ps
// S81-SLICE3-LEPENH (10-19): WIRES-ONLY flat expansion of the die master ot_s81sl_slice_lepe_nh (s_7S: E end, no host
// plane) = ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(0), .MU_EN(0), .AB_EN(0)) with the generate resolved, so that
// tools/landed_parent/lp.py can turn it into the LANDED parent ot_s81sl_slice_lepe_nh_x_lp (regions S = the slice
// cluster, K = lep_nh leaf + 2 lane tiles at the slice's E line face).  Same ports, same children, same connections:
//   u_sl  ot_s81sl_slice           (vector slice cluster, HB 0)
//   u_lep ot_s81sl_lep_nh          (link-port leaf, HOST_EN 0: no host pins at all)
//   u_ln0 / u_ln1 dsfd_coll_lane_e  (LCR 1 = credit core faces: requires +define+OT_S81PH_LANE_CR, as run_die_layer.sh; no
//                 parameter on a hard child)
// No tied child input: every child pin is driven by a port or a child output (the _nh leaf has no l*_st / host pins).
// ch_b is the die strap (S81-DIE7 port map: 1'b1, board / switched lane timeout basis); sid is the slice-id strap.
module ot_s81sl_slice_lepe_nh_x (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [512:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0, lrx1;
    wire tf0, tf1;
    assign lrx0 = {rx0[512], rx0[513], rx0[511:0], rxv[0]};
    assign lrx1 = {rx1[512], rx1[513], rx1[511:0], rxv[1]};
    assign tf = {tf1, tf0};
    ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(lri), .ro_e(lro), .ro_w(ro_w),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
        .ck_rt(ck_rt), .fault(sf));
    dsfd_coll_lane_e u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx0),
        .tx(tx0), .tf(tf0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
    dsfd_coll_lane_e u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx1),
        .tx(tx1), .tf(tf1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    ot_s81sl_lep_nh u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .fault(fault));
endmodule
