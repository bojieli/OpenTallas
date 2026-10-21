`timescale 1ns/1ps
// DRIVE-S81-SLICEP (10-20): WIRES-ONLY flat expansion of the MU die master ot_s81sl_slice_lepw_mu (s_0N: W end, no host
// plane, MU) = ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(0)) (ot_s81sl_slice_lep_mu.sv) with the generate
// resolved, for tools/landed_parent/lp.py -> ot_s81sl_slice_lepw_mu_x_lp (regions S = slice cluster, K = copy-A MU
// endpoint + MU landing leaf + 2 lane tiles at the slice's W line face).  The parent line port is on the E side (ri_e/ro_e).
//   u_sl   ot_s81sl_slice; u_lep ot_s81sl_lep_mu_a (kit s81sl_lepmua); u_land dsdv_mu_land (closed view, SRAM 1);
//   u_ln0 / u_ln1 dsfd_coll_lane_w_ntf (LCR 1 via +define+OT_S81PH_LANE_CR).
// dsdv_slice_lepw_mus (s_0S MU 1) = this master without the mu_rt output: the same physical kit serves it (mu_rt pins left
// unconnected at the die / mu_rt flops pruned), no separate parent kit.
module ot_s81sl_slice_lepw_mu_x (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [512:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc, output wire [31:0] mu_rt,
    output wire fault
);
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0, lrx1;
    wire mwv, mrv, mf; wire [1103:0] mwd, mrd;
    assign lrx0 = {rx0[512], rx0[513], rx0[511:0], rxv[0]};
    assign lrx1 = {rx1[512], rx1[513], rx1[511:0], rxv[1]};
    ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(lri), .ri_e(ri_e), .ro_e(ro_e), .ro_w(lro),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
        .ck_rt(ck_rt), .fault(sf));
    dsfd_coll_lane_w_ntf u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx0),
        .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
    dsfd_coll_lane_w_ntf u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx1),
        .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    ot_s81sl_lep_mu_a u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf), .fault(fault));
    dsdv_mu_land u_land (.clk(clk), .rst_n(rst_n), .wv(mwv), .wd(mwd), .rc(mu_rc),
        .rv(mrv), .rd(mrd), .fault(mf));
    // u_land: no #() on a hard child (blackbox = LEF macro dsdv_mu_land). Its view dsdv_mu_land-263e13fc3 is the SRAM 1 build;
    // W 1104 / NB 80 / NS 1 are the module defaults and SRAM only selects the storage implementation (same cycles, dsdv_mu_land.sv:26).
endmodule
