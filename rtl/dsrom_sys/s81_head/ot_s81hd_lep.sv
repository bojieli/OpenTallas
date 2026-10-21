`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HD-CTL (S81-HEAD 10-21): ot_s81hd_lep = the head die's stage-circuit endpoint (SPEC results/arch/s81_head_1021/SPEC.md
// section 1).  The same endpoint as the stage end slice s_0N (ot_s81sl_slice_lepw_mab_mu_72, G7), so the head speaks
// the stage NEXT-circuit protocol bit for bit:
//   4 x dsfd_coll_lane_w_safe8_ntf  pair A = lk_WN0/1 (u_ln0 / u_ln1), pair B = lk_WN2/3 (u_ln2 / u_ln3)
//   ot_s81sl_lep_mu_ab #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1))   (lepmu t5c/t5d kit parameters)
//   dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1))              the MU second h landing (as the end parent's u_land)
// Head use: pair B RX = the XB message (h, 5,120 BF16 = 80 ring beats of 64 BF16, tagged {user, pos} through mu_rt)
// from S240 or the previous head group, merged by the lep into ri; pair A TX = ring beats the ctl drives on ro (XB
// forward to the next head group under a mu_c tag window, token return / forward beats, in-band host frames).
// Differences from the end parent (all wiring; the lep / lanes / land are unchanged):
//   * one clock region (K): the slice (region S) and the ML landing region are not on the head die; the landing leaf
//     runs on the lep clock, so the end parent's S<->K and K<->ML landing rings are not needed inside this block.
//     The ctl <-> lep crossing is a die-level land-plan row (fixed-latency landing ring, HD-CHAIN).
//   * sl_f = the ctl fault (pin flop) instead of the slice fault.
//   * lw [10:0] = {user, v} of every beat the lep diverts to the landing leaf (from a flop), so the ctl knows when a
//     landed message is complete and can issue its replay command mu_rc {user, v} by the static rule (no hidden state).
// Ports: rx* = {ot_pdie_serdes st {live, fault}, beat}; tx* = lane beat; ro / ri ring form (ri[0] = beat valid, ro[0]
// likewise); mu_c {pos 21, user 10, land, ab, v}; mu_rt {v, user 10, pos 21}; mu_rc {user 10, v}.
// Reset: rst_n -> ot_rst_relay_tree3 (2-stage landing + 6 leaves: 4 lanes, lep, land); every child keeps its own tree.
// Cycles vs the end parent: identical lep / lane cycles; fault out +2 edges (as the end parent's u_lpo_fault); lw +1.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_lep (
    input  wire           ck,
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
    wire [5:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(6)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    wire [514:0] lrx0 = {rx0[512], rx0[513], rx0[511:0], rxv[0]};
    wire [514:0] lrx1 = {rx1[512], rx1[513], rx1[511:0], rxv[1]};
    wire [514:0] lrx2 = {rx2[512], rx2[513], rx2[511:0], rxvb[0]};
    wire [514:0] lrx3 = {rx3[512], rx3[513], rx3[511:0], rxvb[1]};
    wire mwv, mrv, mf, fo; wire [1103:0] mwd, mrd;
    reg slf_q; always @(posedge ck) slf_q <= sl_f;
    dsfd_coll_lane_w_safe8_ntf u_ln0 (.ck(ck), .rs(rr[0]), .chb(ch_b), .rx(lrx0), .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
    dsfd_coll_lane_w_safe8_ntf u_ln1 (.ck(ck), .rs(rr[1]), .chb(ch_b), .rx(lrx1), .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    dsfd_coll_lane_w_safe8_ntf u_ln2 (.ck(ck), .rs(rr[2]), .chb(ch_b), .rx(lrx2), .tx(tx2), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));
    dsfd_coll_lane_w_safe8_ntf u_ln3 (.ck(ck), .rs(rr[3]), .chb(ch_b), .rx(lrx3), .tx(tx3), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));
    ot_s81sl_lep_mu_ab #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_lep (.clk(ck), .rst_n(rr[4]), .ro(ro), .ri(ri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv), .sl_f(slf_q),
        .l0_f(f0), .l1_f(f1), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d),
        .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb), .l2_f(f2), .l3_f(f3),
        .fault(fo));
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(ck), .rst_n(rr[5]), .wv(mwv), .wd(mwd), .rc(mu_rc),
        .rv(mrv), .rd(mrd), .fault(mf));
    // landed-beat report {user [1056:1047], v}
    reg [10:0] lw_q;
    always @(posedge ck) lw_q <= {mwd[1056:1047], mwv && rr[5]};
    assign lw = lw_q;
    ot_pl_pad #(.W(1), .N(2)) u_fo (.ck(ck), .d(fo), .q(fault));
endmodule
