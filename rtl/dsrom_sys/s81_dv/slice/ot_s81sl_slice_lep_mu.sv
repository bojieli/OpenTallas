`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81-2/DIE (2026-10-19): multi-user end-slice clusters and their parameter-free p4l die masters, on the hardened MU
// endpoint tops of record (MU-S81/KIT + MU-S81b, all in ot_s81sl_slice_lep.sv, which this file does NOT change, so the
// lep / lep_nh / lep_mu_a / lep_mu_ab kit sources stay byte-identical):
//   copy-A-only endpoint  ot_s81sl_lep_mu_a  (MU_EN 1, AB_EN 0, HOST_EN 0; kit s81sl_lepmua)  -> s_0N, s_0S, s_7S
//   copy-A/B endpoint     ot_s81sl_lep_mu_ab (MU_EN 1, AB_EN 1, HOST_EN 0; kit s81sl_lepmu)   -> s_0S of the AB die only
//   host-plane endpoint   ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0))  -> s_7N  (OWED: no parameter-free top / kit yet;
//                         its pair-B inputs are constant 0 here and unread inside at AB_EN 0, generate)
// beside the CLOSED landing leaf dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) (view dsdv_mu_land-263e13fc3).
// Cluster = slice + 2 (AB: 4) link lane tiles + endpoint + landing, exactly the MU_EN branch of ot_s81sl_slice_lep with
// the leaf chosen per die position (MU-S81/DIE 908a67c18 used the generic ot_s81sl_lep_mu for every end slice).
// Die masters (dv_plan --mu 1 / 2; bind tables bind_table_p4l3_mu / _mab):
//   dsdv_slice_lepw_mu      s_0N        W, lep_mu_a, mu_c / mu_rc in, mu_rt out (RX tag -> seqhost on rt_0N)
//   dsdv_slice_lepw_mus     s_0S (MU 1) W, lep_mu_a, mu_c / mu_rc in (S-tier RX tag not returned)
//   dsdv_slice_lepe_mu      s_7N        E, lep_mu HOST_EN 1, host plane + mu_c / mu_rc in, mu_rt out (in hf_7N_l2)
//   dsdv_slice_lepe_nh_mus  s_7S        E, lep_mu_a, mu_c / mu_rc in
//   dsdv_slice_lepw_mab     s_0S (MU 2) W, lep_mu_ab, + copy-B lane pair tx2 / tx3 / rx2 / rx3 (-> lk_WS2 / lk_WS3)
// S-tier mu_rt: the endpoint still checks nothing itself; its RX tag is not returned (column-4 margin, MU-S81/DIE owed).
// BIND/mu4 10-19: NO forwarded lane clock outputs.  tf / tfb (the lane tiles' kept clock feedthrough, a copy of clk) had no
// consumer on any die (census: only these wrappers exported them; the PHY / SerDes ports take tx only, every bench leaves
// .tf() open), so they are removed at the source: the lane tiles are the tf-less tops dsfd_coll_lane_w_ntf / _e_ntf
// (ot_s81ph_coll_lane.sv, same core and parameters, the clk feedthrough pin dropped) and no master here has tf / tfb.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_slice_lep_mux #(
    parameter integer SIDE = 0,
    parameter integer HOST_EN = 0,
    parameter integer AB_EN = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_n,
    output wire [1103:0]   ro_n,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    input  wire            ch_b,
    output wire [511:0]    tx0, output wire [511:0] tx1,
    input  wire [513:0]    rx0, input  wire [513:0] rx1,
    input  wire [76:0]     t_host, input wire [53:0] t_kd,
    output wire [514:0]    f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    input  wire [33:0]     mu_c,
    input  wire [10:0]     mu_rc,
    output wire [31:0]     mu_rt,
    output wire [511:0]    tx2, output wire [511:0] tx3,
    input  wire [513:0]    rx2, input  wire [513:0] rx3,
    output wire            fault
);
`ifndef SYNTHESIS
    initial if (HOST_EN != 0 && AB_EN != 0) $fatal(1, "ot_s81sl_slice_lep_mux: no host-plane copy-A/B endpoint exists");
`endif
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    generate if (SIDE == 0) begin : g_w
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(lri), .ri_e(ri_n), .ro_e(ro_n), .ro_w(lro),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_w_ntf #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_w_ntf #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
        if (AB_EN != 0) begin : g_b
        dsfd_coll_lane_w_ntf #(.LCR(1)) u_ln2 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx2[512], rx2[513], rx2[511:0], rxvb[0]}),
            .tx(tx2), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
        dsfd_coll_lane_w_ntf #(.LCR(1)) u_ln3 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx3[512], rx3[513], rx3[511:0], rxvb[1]}),
            .tx(tx3), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
        end
    end else begin : g_e
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ri_e(lri), .ro_e(lro), .ro_w(ro_n),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_e_ntf #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_e_ntf #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
        if (AB_EN != 0) begin : g_b
        dsfd_coll_lane_e_ntf #(.LCR(1)) u_ln2 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx2[512], rx2[513], rx2[511:0], rxvb[0]}),
            .tx(tx2), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
        dsfd_coll_lane_e_ntf #(.LCR(1)) u_ln3 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx3[512], rx3[513], rx3[511:0], rxvb[1]}),
            .tx(tx3), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
        end
    end endgenerate
    generate if (AB_EN == 0) begin : g_nb
        assign tx2 = 512'd0; assign tx3 = 512'd0;
        assign l2r = 1'b0; assign l3r = 1'b0; assign i2v = 1'b0; assign i3v = 1'b0; assign i2d = 553'd0; assign i3d = 553'd0;
        assign f2 = 3'd0; assign f3 = 3'd0;
    end endgenerate
    wire mwv, mrv, mf; wire [1103:0] mwd, mrd;
    generate if (HOST_EN != 0) begin : g_h        // s_7N: host-plane endpoint (OWED parameter-free top / kit)
    ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0)) u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .l0_st(rx0[513:512]), .l1_st(rx1[513:512]),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
        .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
        .l2_f(3'd0), .l3_f(3'd0), .fault(fault));
    end else if (AB_EN != 0) begin : g_ab     // copy-A/B endpoint (kit s81sl_lepmu)
    ot_s81sl_lep_mu_ab u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d),
        .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb),
        .l2_f(f2), .l3_f(f3), .fault(fault));
    assign f_host = 515'd0; assign f_lf = 4'd0; assign f_ks = 53'd0;
    end else begin : g_a                         // copy-A-only endpoint (kit s81sl_lepmua)
    ot_s81sl_lep_mu_a u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf), .fault(fault));
    assign f_host = 515'd0; assign f_lf = 4'd0; assign f_ks = 53'd0;
    end endgenerate
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(clk), .rst_n(rst_n), .wv(mwv), .wd(mwd), .rc(mu_rc),
        .rv(mrv), .rd(mrd), .fault(mf));
endmodule

module ot_s81sl_slice_lepw_mu (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc, output wire [31:0] mu_rt,
    output wire fault
);
    ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt),
        .ch_b(ch_b), .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),   // no host plane (lep_mu_a has no host ports)
        .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(mu_rt), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .fault(fault));
endmodule
module ot_s81sl_slice_lepw_mus (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc,
    output wire fault
);
    ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt),
        .ch_b(ch_b), .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .fault(fault));
endmodule
module ot_s81sl_slice_lepe_mu (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [76:0] t_host, input wire [53:0] t_kd, output wire [514:0] f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc, output wire [31:0] mu_rt,
    output wire fault
);
    ot_s81sl_slice_lep_mux #(.SIDE(1), .HOST_EN(1), .AB_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt),
        .ch_b(ch_b), .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(mu_rt), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .fault(fault));
endmodule
module ot_s81sl_slice_lepe_nh_mus (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc,
    output wire fault
);
    ot_s81sl_slice_lep_mux #(.SIDE(1), .HOST_EN(0), .AB_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt),
        .ch_b(ch_b), .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(), .tx2(), .tx3(), .rx2(514'd0), .rx3(514'd0), .fault(fault));
endmodule
module ot_s81sl_slice_lepw_mab (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    input  wire [33:0] mu_c, input wire [10:0] mu_rc,
    output wire [511:0] tx2, output wire [511:0] tx3, input wire [513:0] rx2, input wire [513:0] rx3,
    output wire fault
);
    ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e),
        .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt),
        .ch_b(ch_b), .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(), .tx2(tx2), .tx3(tx3), .rx2(rx2), .rx3(rx3), .fault(fault));
endmodule

// MU-S81-2/DIE: vertical 512 / 562 stations of the copy-B lane pair (s_0S -> lk_WS2 / lk_WS3 along the 40-um frame/PHY
// gap).  Same ot_dvrly_st HC 1 body as every dsfd_dvrlyh master (dsfd_rly_masters_dvh.sv, unchanged); NO closed
// physical view: soft forwarded-clock relay flops placed by the die repeater flow (copy-B relay plan).
module dsfd_dvrlyh_512_NS (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_512_SN (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_562_NS (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_dvrly_st #(.W(562), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
