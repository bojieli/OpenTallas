`timescale 1ns/1ps
// HEAD regional successor: three explicit same-frequency roots. tx/rx0/1 use
// ck_A, tx/rx2/3 use ck_B, and the ctl/ML interface uses ck. The original
// ot_s81hd_lep and its legacy views remain separate. Each pair has its own
// two-stage parent reset release; the regional child owns its internal forests.
// CORE_CRED=12 matches the regional fixed-latency credit flight. No legacy CRED8
// lane or single-root LEP physical view may bind to this master.
// Regional child cost: C->pair +4, pair->C +5, outer lane payload/valid +2,
// reverse credits +2 (RTT +4). Parent ML reach remains an actual packing proof.
module ot_s81hd_lep_regional (
    input  wire           ck,
    input  wire           ck_A,
    input  wire           ck_B,
    input  wire           rst_n,
    input  wire           ch_b,
    output wire [511:0]   tx0,
    output wire [511:0]   tx1,
    input  wire [513:0]   rx0,
    input  wire [513:0]   rx1,
    output wire [511:0]   tx2,
    output wire [511:0]   tx3,
    input  wire [513:0]   rx2,
    input  wire [513:0]   rx3,
    input  wire [1103:0]  ro,
    output wire [1103:0]  ri,
    input  wire [33:0]    mu_c,
    output wire [31:0]    mu_rt,
    input  wire [10:0]    mu_rc,
    output wire [10:0]    lw,
    input  wire           sl_f,
    output wire           fault
);
    wire [1:0] rr_c;
    wire [2:0] rr_a, rr_b;
    ot_rst_relay_tree3 #(.REGIONS(2)) u_rr_c (.clk(ck), .rst_n_in(rst_n), .rst_n(rr_c));
    ot_rst_relay_tree3 #(.REGIONS(3)) u_rr_a (.clk(ck_A), .rst_n_in(rst_n), .rst_n(rr_a));
    ot_rst_relay_tree3 #(.REGIONS(3)) u_rr_b (.clk(ck_B), .rst_n_in(rst_n), .rst_n(rr_b));
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    wire [514:0] lrx0 = {rx0[512], rx0[513], rx0[511:0], rxv[0]};
    wire [514:0] lrx1 = {rx1[512], rx1[513], rx1[511:0], rxv[1]};
    wire [514:0] lrx2 = {rx2[512], rx2[513], rx2[511:0], rxvb[0]};
    wire [514:0] lrx3 = {rx3[512], rx3[513], rx3[511:0], rxvb[1]};
    wire mwv, mrv, mf, fo; wire [1103:0] mwd, mrd;
    reg slf_q; always @(posedge ck) slf_q <= sl_f;
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln0 (.ck(ck_A), .rs(rr_a[0]), .chb(ch_b), .rx(lrx0), .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln1 (.ck(ck_A), .rs(rr_a[1]), .chb(ch_b), .rx(lrx1), .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln2 (.ck(ck_B), .rs(rr_b[0]), .chb(ch_b), .rx(lrx2), .tx(tx2), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln3 (.ck(ck_B), .rs(rr_b[1]), .chb(ch_b), .rx(lrx3), .tx(tx3), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
    ot_s81sl_lep_mu_ab_regional_r3r #(.DR(12), .CRED(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_lep (.clk(ck), .clk_a(ck_A), .clk_b(ck_B), .rst_n(rr_c[0]), .rst_n_a(rr_a[2]), .rst_n_b(rr_b[2]), .ro(ro), .ri(ri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv), .sl_f(slf_q),
        .l0_f(f0), .l1_f(f1), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d),
        .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb), .l2_f(f2), .l3_f(f3),
        .fault(fo));
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(ck), .rst_n(rr_c[1]), .wv(mwv), .wd(mwd), .rc(mu_rc),
        .rv(mrv), .rd(mrd), .fault(mf));
    // landed-beat report {user [1056:1047], v}
    reg [10:0] lw_q;
    always @(posedge ck) lw_q <= {mwd[1056:1047], mwv && rr_c[1]};
    assign lw = lw_q;
    ot_pl_pad #(.W(1), .N(2)) u_fo (.ck(ck), .d(fo), .q(fault));
endmodule
