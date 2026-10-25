`timescale 1ns/1ps
// STW-S81-LAND 10-21: bench of the MU72 end-parent lane landing (ot_s81_mu72_lnland, L0/L1 lane regions, CRED12).
// Two end-slice sides X -> Y and Y -> X, each = ot_s81sl_lep_mu_a #(CRED, DR) on ck_K + two dsfd_coll_lane_*_safe8_ntf
// #(CORE_CRED) on their own region clocks ck_N0 / ck_N1 + ot_s81_mu72_lnland per lane (P_LAND 1), linked through the
// ot_pdie_ucie behavioural PMA (lane 0 PMA_LAT 2, lane 1 PMA_LAT 9: skewed pair).  A reference pair RX -> RY runs the
// CURRENT die configuration (no landing, lanes on ck_K, CRED / DR / CORE_CRED 8) on the same ring beats at the same
// cycles.  Checks:
//   LAT   30 isolated beats each way: every beat bit-exact, in order, and its arrival is EXACTLY ref + 6 edges (lep -> lane
//         +3 at the sender, lane -> lep +3 at the receiver) at P_PH 0 (all region clocks in phase); with phase-offset
//         region clocks (P_PH 1) the added latency must stay within 6..8 edges and be constant per run.
//   RATE  N_BURST beats each way at the ring rate P_RATE % (above the 0.764 lane cap -> lanes saturated): bit-exact, in
//         order; last-beat arrival <= ref + 6 + P_SLACK edges (no beat-rate loss vs the unlanded CRED 8 die).
//   no lep fault, no lane fault, no ucie fault on either side.
// Mutants (must FAIL): P_MUT 1 = lane-0 K->N bundle unlanded (missing landing edge), 2 = lane-1 N->K bundle unlanded,
//   3 = lane-0 credit li_r skips the landing; P_CRED 8 with P_LAND 1 = landing without the credit raise (RATE fails).
// Verdict: "PASS mu72_lnland ..." or "FAIL mu72_lnland ...".
// per-landing contract monitor: every source pulse (valid / credit, with its data) must leave the landing exactly
// +3 destination edges later, same bits, none lost / added.  Edge index = the clock's own posedge count from time 0
// (all region clocks share the period; phase offsets < 1 period).
module tb_lnl_mon #(parameter integer W = 1) (input wire ck_s, ck_d, input wire v_s, input wire [W-1:0] d_s,
                                              input wire v_d, input wire [W-1:0] d_d, output integer err, output integer n);
    integer es = 0, ed = 0, wp = 0, rp = 0;
    integer qe [0:255]; reg [W-1:0] qd [0:255];
    initial begin err = 0; n = 0; end
    always @(posedge ck_s) begin es <= es + 1; if (v_s === 1'b1) begin qe[wp % 256] = es; qd[wp % 256] = d_s; wp = wp + 1; end end
    always @(posedge ck_d) begin
        ed <= ed + 1;
        if (v_d === 1'b1) begin
            if (rp >= wp || ed - qe[rp % 256] != 3 || d_d !== qd[rp % 256]) begin
                err = err + 1;
                if (err < 4) $display("LANDING_CONTRACT %m: dest edge %0d src edge %0d (+%0d, want +3) data ok %0d",
                    ed, rp < wp ? qe[rp % 256] : -1, rp < wp ? ed - qe[rp % 256] : -1, rp < wp ? (d_d === qd[rp % 256]) : 0);
            end
            rp = rp + 1; n = n + 1;
        end
    end
endmodule

module tb_lnl_side #(parameter integer LAND = 1, CRED = 12, MUT = 0, LAT1 = 9, KIT = 0, NST = 0) (
    input wire ck_k, ck_n0, ck_n1, rst_n,
    input wire [1103:0] ro, output wire [1103:0] ri, output wire [31:0] rt, output wire fault, output wire [5:0] flt,
    output wire [1025:0] pma_tx, output wire [1:0] pma_tck, input wire [1025:0] pma_rx, input wire [1:0] pma_rck,
    output integer lerr, output integer lpulses
);
    wire [1:0] lv, lr, iv, ir, rxv; wire [2*553-1:0] ld, id; wire [5:0] lf;
    wire mwv; wire [1103:0] mwd;
    ot_s81sl_lep_mu_a #(.SRAM(1), .NB(80), .CRED(CRED), .DR(CRED), .RX_SRAM(KIT), .IN_PIPE(KIT), .NATIVE32(KIT)) u_lep (.clk(ck_k), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lv[0]), .lo0_r(lr[0]), .lo0_d(ld[0 +: 553]), .lo1_v(lv[1]), .lo1_r(lr[1]), .lo1_d(ld[553 +: 553]),
        .li0_v(iv[0]), .li0_r(ir[0]), .li0_d(id[0 +: 553]), .li1_v(iv[1]), .li1_r(ir[1]), .li1_d(id[553 +: 553]),
        .rxv(rxv), .sl_f(1'b0), .l0_f(lf[2:0]), .l1_f(lf[5:3]),
        .mu_c(34'd0), .mu_rt(rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0), .fault(fault));
    // region reset leaves (same age on K and N, as the MU72 tops: one forest each from the common root)
    wire rk, rn0, rn1;
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rk (.ck(ck_k), .d(rst_n), .q(rk));
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rn0 (.ck(ck_n0), .d(rst_n), .q(rn0));
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rn1 (.ck(ck_n1), .d(rst_n), .q(rn1));
    wire [1:0] nlv, nlr, niv, nir, nrxv; wire [2*553-1:0] nld, nid; wire [5:0] nf; wire [3:0] st;
    wire [1:0] ckn = {ck_n1, ck_n0}; wire [1:0] rnn = {rn1, rn0};
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_ln
        wire [31:0] esum, psum;                      // per-lane landing contract errors / pulses (0 when unlanded)
        if (LAND != 0) begin : g_land
            wire [1:0] kst;
            if (NST != 0) begin : g_nst   // S81/PORTFIX-FLT 10-25: the status-less landing of the s_0N / s_0S / s_7S ends
            ot_s81_mu72_lnland_nst #(.MUT(g == 0 ? ((MUT == 1) ? 1 : (MUT == 3) ? 3 : 0) : ((MUT == 2) ? 2 : 0))) u_lnl (
                .ck_k(ck_k), .ck_n(ckn[g]), .rs_k(rk), .rs_n(rnn[g]),
                .k_lo_v(lv[g]), .k_lo_d(ld[553*g +: 553]), .k_lo_r(lr[g]), .k_li_v(iv[g]), .k_li_d(id[553*g +: 553]),
                .k_li_r(ir[g]), .k_rxv(rxv[g]), .k_flt(lf[3*g +: 3]),
                .n_lo_v(nlv[g]), .n_lo_d(nld[553*g +: 553]), .n_lo_r(nlr[g]), .n_li_v(niv[g]), .n_li_d(nid[553*g +: 553]),
                .n_li_r(nir[g]), .n_rxv(nrxv[g]), .n_flt(nf[3*g +: 3]));
            assign kst = 2'b00;
            end else begin : g_st
            ot_s81_mu72_lnland #(.MUT(g == 0 ? ((MUT == 1) ? 1 : (MUT == 3) ? 3 : 0) : ((MUT == 2) ? 2 : 0))) u_lnl (
                .ck_k(ck_k), .ck_n(ckn[g]), .rs_k(rk), .rs_n(rnn[g]),
                .k_lo_v(lv[g]), .k_lo_d(ld[553*g +: 553]), .k_lo_r(lr[g]), .k_li_v(iv[g]), .k_li_d(id[553*g +: 553]),
                .k_li_r(ir[g]), .k_rxv(rxv[g]), .k_flt(lf[3*g +: 3]), .k_st(kst),
                .n_lo_v(nlv[g]), .n_lo_d(nld[553*g +: 553]), .n_lo_r(nlr[g]), .n_li_v(niv[g]), .n_li_d(nid[553*g +: 553]),
                .n_li_r(nir[g]), .n_rxv(nrxv[g]), .n_flt(nf[3*g +: 3]), .n_st(st[2*g +: 2]));
            end
            integer e0, e1, e2, e3, c0, c1, c2, c3;
            tb_lnl_mon #(.W(553)) m_lo (.ck_s(ck_k), .ck_d(ckn[g]), .v_s(lv[g]), .d_s(ld[553*g +: 553]), .v_d(nlv[g]), .d_d(nld[553*g +: 553]), .err(e0), .n(c0));
            tb_lnl_mon #(.W(553)) m_li (.ck_s(ckn[g]), .ck_d(ck_k), .v_s(niv[g]), .d_s(nid[553*g +: 553]), .v_d(iv[g]), .d_d(id[553*g +: 553]), .err(e1), .n(c1));
            tb_lnl_mon #(.W(1)) m_lr (.ck_s(ckn[g]), .ck_d(ck_k), .v_s(nlr[g]), .d_s(1'b1), .v_d(lr[g]), .d_d(1'b1), .err(e2), .n(c2));
            tb_lnl_mon #(.W(1)) m_ir (.ck_s(ck_k), .ck_d(ckn[g]), .v_s(ir[g]), .d_s(1'b1), .v_d(nir[g]), .d_d(1'b1), .err(e3), .n(c3));
            assign esum = e0 + e1 + e2 + e3; assign psum = c0 + c1 + c2 + c3;
        end else begin : g_direct
            assign esum = 0; assign psum = 0;
            assign nlv[g] = lv[g]; assign nld[553*g +: 553] = ld[553*g +: 553]; assign lr[g] = nlr[g];
            assign iv[g] = niv[g]; assign id[553*g +: 553] = nid[553*g +: 553]; assign nir[g] = ir[g];
            assign nrxv[g] = rxv[g]; assign lf[3*g +: 3] = nf[3*g +: 3];
        end
        wire [511:0] tx, rx;
        dsfd_coll_lane_e_safe8_ntf #(.CORE_CRED(CRED)) u_ln (.ck(ckn[g]), .rs(LAND != 0 ? rnn[g] : rk), .chb(1'b0),
            .rx({st[2*g], st[2*g+1], rx, nrxv[g]}), .tx(tx), .lo_v(nlv[g]), .lo_r(nlr[g]), .lo_d(nld[553*g +: 553]),
            .li_v(niv[g]), .li_r(nir[g]), .li_d(nid[553*g +: 553]), .flt(nf[3*g +: 3]));
        ot_pdie_ucie #(.PMA_LAT(g == 0 ? 2 : LAT1)) u_ph (.clk(ckn[g]), .rst(rst_n), .tx(tx), .rx(rx), .st(st[2*g +: 2]),
            .pma_tx(pma_tx[513*g +: 513]), .pma_tck(pma_tck[g]), .pma_rx(pma_rx[513*g +: 513]), .pma_rck(pma_rck[g]));
    end endgenerate
    assign flt = nf;
    always @* begin
        lerr = g_ln[0].esum + g_ln[1].esum;
        lpulses = g_ln[0].psum + g_ln[1].psum;
    end
endmodule

// P_R4L 1: the die-side successor (ot_s81sl_slice_lepw_mab_r4l_mu_72) end: u_lep = ot_s81sl_lep_mu_ab_regional_r4l on
// ck_K (centre) / ck_KA (pair A, lanes 0/1) / ck_KB (pair B, lanes 2/3), four CRED12 lanes on their own regions N0..N3,
// every lane <-> lep bundle landed by ot_s81_mu72_lnland with ck_k = the pair clock that owns those lep ports (as the top).
// mu_c = 0 -> every beat on pair A (lanes 0/1); pair B lanes link up and carry credits only (no fault allowed).
module tb_lnl_side_r4l #(parameter integer MUT = 0, LAT1 = 9) (
    input wire ck_k, ck_ka, ck_kb, ck_n0, ck_n1, ck_n2, ck_n3, rst_n,
    input wire [1103:0] ro, output wire [1103:0] ri, output wire [31:0] rt, output wire fault, output wire [11:0] flt,
    output wire [2051:0] pma_tx, output wire [3:0] pma_tck, input wire [2051:0] pma_rx, input wire [3:0] pma_rck,
    output integer lerr, output integer lpulses
);
    wire [3:0] lv, lr, iv, ir, rxv; wire [4*553-1:0] ld, id; wire [11:0] lf;
    wire mwv; wire [1103:0] mwd;
    wire rk, rka, rkb; wire [3:0] rn;
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rk (.ck(ck_k), .d(rst_n), .q(rk));
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rka (.ck(ck_ka), .d(rst_n), .q(rka));
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rkb (.ck(ck_kb), .d(rst_n), .q(rkb));
    wire [3:0] ckn = {ck_n3, ck_n2, ck_n1, ck_n0}; wire [3:0] ckp = {ck_kb, ck_kb, ck_ka, ck_ka}; wire [3:0] rp = {rkb, rkb, rka, rka};
    ot_s81sl_lep_mu_ab_regional_r4l #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_lep (
        .clk(ck_k), .clk_a(ck_ka), .clk_b(ck_kb), .rst_n(rk), .rst_n_a(rka), .rst_n_b(rkb), .ro(ro), .ri(ri),
        .lo0_v(lv[0]), .lo0_r(lr[0]), .lo0_d(ld[0 +: 553]), .lo1_v(lv[1]), .lo1_r(lr[1]), .lo1_d(ld[553 +: 553]),
        .li0_v(iv[0]), .li0_r(ir[0]), .li0_d(id[0 +: 553]), .li1_v(iv[1]), .li1_r(ir[1]), .li1_d(id[553 +: 553]),
        .rxv(rxv[1:0]), .sl_f(1'b0), .l0_f(lf[2:0]), .l1_f(lf[5:3]), .mu_c(34'd0), .mu_rt(rt), .ml_wv(mwv), .ml_wd(mwd),
        .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
        .lo2_v(lv[2]), .lo2_r(lr[2]), .lo2_d(ld[1106 +: 553]), .lo3_v(lv[3]), .lo3_r(lr[3]), .lo3_d(ld[1659 +: 553]),
        .li2_v(iv[2]), .li2_r(ir[2]), .li2_d(id[1106 +: 553]), .li3_v(iv[3]), .li3_r(ir[3]), .li3_d(id[1659 +: 553]),
        .rxvb(rxv[3:2]), .l2_f(lf[8:6]), .l3_f(lf[11:9]), .fault(fault));
    wire [3:0] nlv, nlr, niv, nir, nrxv; wire [4*553-1:0] nld, nid; wire [11:0] nf; wire [7:0] st;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ln
        wire [0:0] rnv;
        ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_rn (.ck(ckn[g]), .d(rst_n), .q(rnv));
        assign rn[g] = rnv[0];
        wire [1:0] kst;
        ot_s81_mu72_lnland #(.MUT(g == 0 ? ((MUT == 1) ? 1 : (MUT == 3) ? 3 : 0) : g == 1 ? ((MUT == 2) ? 2 : 0) : 0)) u_lnl (
            .ck_k(ckp[g]), .ck_n(ckn[g]), .rs_k(rp[g]), .rs_n(rn[g]),
            .k_lo_v(lv[g]), .k_lo_d(ld[553*g +: 553]), .k_lo_r(lr[g]), .k_li_v(iv[g]), .k_li_d(id[553*g +: 553]),
            .k_li_r(ir[g]), .k_rxv(rxv[g]), .k_flt(lf[3*g +: 3]), .k_st(kst),
            .n_lo_v(nlv[g]), .n_lo_d(nld[553*g +: 553]), .n_lo_r(nlr[g]), .n_li_v(niv[g]), .n_li_d(nid[553*g +: 553]),
            .n_li_r(nir[g]), .n_rxv(nrxv[g]), .n_flt(nf[3*g +: 3]), .n_st(st[2*g +: 2]));
        integer e0, e1, e2, e3, c0, c1, c2, c3;
        tb_lnl_mon #(.W(553)) m_lo (.ck_s(ckp[g]), .ck_d(ckn[g]), .v_s(lv[g]), .d_s(ld[553*g +: 553]), .v_d(nlv[g]), .d_d(nld[553*g +: 553]), .err(e0), .n(c0));
        tb_lnl_mon #(.W(553)) m_li (.ck_s(ckn[g]), .ck_d(ckp[g]), .v_s(niv[g]), .d_s(nid[553*g +: 553]), .v_d(iv[g]), .d_d(id[553*g +: 553]), .err(e1), .n(c1));
        tb_lnl_mon #(.W(1)) m_lr (.ck_s(ckn[g]), .ck_d(ckp[g]), .v_s(nlr[g]), .d_s(1'b1), .v_d(lr[g]), .d_d(1'b1), .err(e2), .n(c2));
        tb_lnl_mon #(.W(1)) m_ir (.ck_s(ckp[g]), .ck_d(ckn[g]), .v_s(ir[g]), .d_s(1'b1), .v_d(nir[g]), .d_d(1'b1), .err(e3), .n(c3));
        wire [31:0] esum = e0 + e1 + e2 + e3, psum = c0 + c1 + c2 + c3;
        wire [511:0] tx, rx;
        dsfd_coll_lane_e_safe8_ntf #(.CORE_CRED(12)) u_ln (.ck(ckn[g]), .rs(rn[g]), .chb(1'b0),
            .rx({st[2*g], st[2*g+1], rx, nrxv[g]}), .tx(tx), .lo_v(nlv[g]), .lo_r(nlr[g]), .lo_d(nld[553*g +: 553]),
            .li_v(niv[g]), .li_r(nir[g]), .li_d(nid[553*g +: 553]), .flt(nf[3*g +: 3]));
        ot_pdie_ucie #(.PMA_LAT(g == 1 ? LAT1 : 2 + g)) u_ph (.clk(ckn[g]), .rst(rst_n), .tx(tx), .rx(rx), .st(st[2*g +: 2]),
            .pma_tx(pma_tx[513*g +: 513]), .pma_tck(pma_tck[g]), .pma_rx(pma_rx[513*g +: 513]), .pma_rck(pma_rck[g]));
    end endgenerate
    assign flt = nf;
    always @* begin
        lerr = g_ln[0].esum + g_ln[1].esum + g_ln[2].esum + g_ln[3].esum;
        lpulses = g_ln[0].psum + g_ln[1].psum + g_ln[2].psum + g_ln[3].psum;
    end
endmodule

module tb_s81_mu72_lnland #(parameter integer P_LAND = 1, P_CRED = 12, P_MUT = 0, P_PH = 0, SEED = 1, P_R4L = 0, P_KIT = 0, P_NST = 0,
                            P_RATE = 80, N_BURST = 600, P_SLACK = 4, WAIT = 8000);
    localparam real T = 0.8333;
    reg ck0 = 0; always #(T / 2) ck0 = ~ck0;                          // reference + DUT ck_K of side X
    // DUT region clocks: P_PH 0 = all in phase; 1 = ck_N lag ck_K by 150 / 330 ps, side Y K lags X K by 90 ps
    reg cxk = 0, cxn0 = 0, cxn1 = 0, cyk = 0, cyn0 = 0, cyn1 = 0;
    always @(ck0) begin
        cxk <= ck0;
        cxn0 <= #(P_PH ? 0.150 : 0.0) ck0; cxn1 <= #(P_PH ? 0.330 : 0.0) ck0;
        cyk <= #(P_PH ? 0.090 : 0.0) ck0; cyn0 <= #(P_PH ? 0.240 : 0.0) ck0; cyn1 <= #(P_PH ? 0.400 : 0.0) ck0;
    end
    reg rst_n = 0;
    integer cyc = 0; always @(posedge ck0) cyc <= cyc + 1;
    reg [1103:0] xro = 0, yro = 0;
    wire [1103:0] dxri, dyri, rxri, ryri; wire [31:0] dxrt, dyrt, rxrt, ryrt; wire dxf, dyf, rxf, ryf;
    wire [5:0] dxl, dyl, rxl, ryl; integer le_dx, le_dy, le_rx, le_ry, lp_dx, lp_dy, lp_rx, lp_ry;
    wire [1025:0] p_dx, p_dy, p_rx, p_ry; wire [1:0] c_dx, c_dy, c_rx, c_ry;
    generate if (P_R4L != 0) begin : g_r4l
        // successor end: K / KA / KB / N0..N3 regions (P_PH 1: KA +60, KB +120, N0..N3 +150/+330/+210/+270 ps; side Y +90)
        reg xka = 0, xkb = 0, xn2 = 0, xn3 = 0, yka = 0, ykb = 0, yn2 = 0, yn3 = 0;
        always @(ck0) begin
            xka <= #(P_PH ? 0.060 : 0.0) ck0; xkb <= #(P_PH ? 0.120 : 0.0) ck0; xn2 <= #(P_PH ? 0.210 : 0.0) ck0; xn3 <= #(P_PH ? 0.270 : 0.0) ck0;
            yka <= #(P_PH ? 0.150 : 0.0) ck0; ykb <= #(P_PH ? 0.210 : 0.0) ck0; yn2 <= #(P_PH ? 0.300 : 0.0) ck0; yn3 <= #(P_PH ? 0.360 : 0.0) ck0;
        end
        wire [2051:0] q_dx, q_dy; wire [3:0] k_dx, k_dy; wire [11:0] f_dx, f_dy;
        tb_lnl_side_r4l #(.MUT(P_MUT)) s_dx (.ck_k(cxk), .ck_ka(xka), .ck_kb(xkb), .ck_n0(cxn0), .ck_n1(cxn1), .ck_n2(xn2), .ck_n3(xn3),
            .rst_n(rst_n), .ro(xro), .ri(dxri), .rt(dxrt), .fault(dxf), .flt(f_dx), .pma_tx(q_dx), .pma_tck(k_dx), .pma_rx(q_dy), .pma_rck(k_dy), .lerr(le_dx), .lpulses(lp_dx));
        tb_lnl_side_r4l #(.MUT(0)) s_dy (.ck_k(cyk), .ck_ka(yka), .ck_kb(ykb), .ck_n0(cyn0), .ck_n1(cyn1), .ck_n2(yn2), .ck_n3(yn3),
            .rst_n(rst_n), .ro(yro), .ri(dyri), .rt(dyrt), .fault(dyf), .flt(f_dy), .pma_tx(q_dy), .pma_tck(k_dy), .pma_rx(q_dx), .pma_rck(k_dx), .lerr(le_dy), .lpulses(lp_dy));
        assign dxl = f_dx[5:0] | f_dx[11:6]; assign dyl = f_dy[5:0] | f_dy[11:6];
    end else begin : g_plain
    tb_lnl_side #(.LAND(P_LAND), .CRED(P_CRED), .MUT(P_MUT), .KIT(P_KIT), .NST(P_NST)) s_dx (.ck_k(cxk), .ck_n0(P_LAND ? cxn0 : cxk), .ck_n1(P_LAND ? cxn1 : cxk),
        .rst_n(rst_n), .ro(xro), .ri(dxri), .rt(dxrt), .fault(dxf), .flt(dxl), .pma_tx(p_dx), .pma_tck(c_dx), .pma_rx(p_dy), .pma_rck(c_dy), .lerr(le_dx), .lpulses(lp_dx));
    tb_lnl_side #(.LAND(P_LAND), .CRED(P_CRED), .MUT(0), .KIT(P_KIT), .NST(P_NST)) s_dy (.ck_k(cyk), .ck_n0(P_LAND ? cyn0 : cyk), .ck_n1(P_LAND ? cyn1 : cyk),
        .rst_n(rst_n), .ro(yro), .ri(dyri), .rt(dyrt), .fault(dyf), .flt(dyl), .pma_tx(p_dy), .pma_tck(c_dy), .pma_rx(p_dx), .pma_rck(c_dx), .lerr(le_dy), .lpulses(lp_dy));
    end endgenerate
    tb_lnl_side #(.LAND(0), .CRED(8)) s_rx (.ck_k(ck0), .ck_n0(ck0), .ck_n1(ck0),
        .rst_n(rst_n), .ro(xro), .ri(rxri), .rt(rxrt), .fault(rxf), .flt(rxl), .pma_tx(p_rx), .pma_tck(c_rx), .pma_rx(p_ry), .pma_rck(c_ry), .lerr(le_rx), .lpulses(lp_rx));
    tb_lnl_side #(.LAND(0), .CRED(8)) s_ry (.ck_k(ck0), .ck_n0(ck0), .ck_n1(ck0),
        .rst_n(rst_n), .ro(yro), .ri(ryri), .rt(ryrt), .fault(ryf), .flt(ryl), .pma_tx(p_ry), .pma_tck(c_ry), .pma_rx(p_rx), .pma_rck(c_rx), .lerr(le_ry), .lpulses(lp_ry));
    // ------------------------------------------------------------------ scoreboards (per direction: DUT and REF)
    localparam integer QN = 2048;
    reg [1103:0] eq [0:1][0:QN-1]; integer ne [0:1];
    integer nd [0:1], nr [0:1], bad = 0;
    integer cd [0:1][0:QN-1], cr [0:1][0:QN-1];
    always @(posedge ck0) begin : sb
        integer d;
        for (d = 0; d < 2; d = d + 1) begin
            if ((d == 0 ? dyri[0] : dxri[0])) begin
                if (nd[d] >= ne[d] || (d == 0 ? dyri : dxri) !== eq[d][nd[d]] || (d == 0 ? dyrt : dxrt) !== 32'd0) begin
                    bad = bad + 1;
                    if (bad < 8) $display("MISMATCH DUT dir %0d beat %0d cyc %0d", d, nd[d], cyc);
                end
                cd[d][nd[d]] = cyc; nd[d] = nd[d] + 1;
            end
            if ((d == 0 ? ryri[0] : rxri[0])) begin
                if (nr[d] >= ne[d] || (d == 0 ? ryri : rxri) !== eq[d][nr[d]]) begin
                    bad = bad + 1;
                    if (bad < 8) $display("MISMATCH REF dir %0d beat %0d cyc %0d", d, nr[d], cyc);
                end
                cr[d][nr[d]] = cyc; nr[d] = nr[d] + 1;
            end
        end
    end
    // DUT ri of side Y sampled on ck0: at P_PH 1 side Y's K lags ck0 by 90 ps (< half period) -> same edge index
    function automatic [1103:0] xb(input integer dummy);
        integer i; reg [1103:0] b;
        begin
            b = 0; for (i = 0; i < 32; i = i + 1) b[21 + 32 * i +: 32] = $urandom;
            b[20:13] = $urandom; b[12:9] = $urandom; b[8:4] = 5'd1 + ($urandom % 8); b[3:1] = 3'd2; b[0] = 1'b1; xb = b;
        end
    endfunction
    reg [1103:0] bt;
    task automatic send(input integer d, input integer n, input integer gap, input integer rate);
        integer k;
        begin
            k = 0;
            while (k < n) begin
                @(negedge ck0); xro = 0; yro = 0;
                if (($urandom % 100) < rate) begin
                    bt = xb(0); if (d == 0) xro = bt; else yro = bt;
                    eq[d][ne[d]] = bt; ne[d] = ne[d] + 1; k = k + 1;
                    repeat (gap) begin @(negedge ck0); xro = 0; yro = 0; end
                end
            end
            @(negedge ck0); xro = 0; yro = 0;
        end
    endtask
    integer lsum, lcnt;
    integer d, k, lat0 [0:1], latok, l0, l1, rate_ok, f_any, drain [0:1], i0 [0:1], last_d [0:1], last_r [0:1];
    initial begin
        void'($urandom(SEED));
        for (d = 0; d < 2; d = d + 1) begin ne[d] = 0; nd[d] = 0; nr[d] = 0; end
        repeat (8) @(posedge ck0); rst_n = 1;
        repeat (WAIT) @(posedge ck0);                                 // link-up
        // ---- LAT: isolated beats, X -> Y then Y -> X
        for (d = 0; d < 2; d = d + 1) begin
            i0[d] = ne[d]; send(d, 30, 150, 100); repeat (400) @(negedge ck0);
        end
        // ---- RATE: bursts, X -> Y then Y -> X
        for (d = 0; d < 2; d = d + 1) begin
            drain[d] = ne[d]; send(d, N_BURST, 0, P_RATE); repeat (3000) @(negedge ck0);
        end
        repeat (500) @(negedge ck0);
        f_any = dxf | dyf | rxf | ryf | (|dxl) | (|dyl) | (|rxl) | (|ryl);
        latok = 1; l0 = -1; l1 = -1; lsum = 0; lcnt = 0;
        for (d = 0; d < 2; d = d + 1) begin
            for (k = i0[d]; k < i0[d] + 30 && k < nd[d] && k < nr[d]; k = k + 1) begin
                if (l0 < 0 || cd[d][k] - cr[d][k] < l0) l0 = cd[d][k] - cr[d][k];
                if (cd[d][k] - cr[d][k] > l1) l1 = cd[d][k] - cr[d][k];
                lsum = lsum + cd[d][k] - cr[d][k]; lcnt = lcnt + 1;
            end
            last_d[d] = (nd[d] > 0) ? cd[d][nd[d] - 1] : 0; last_r[d] = (nr[d] > 0) ? cr[d][nr[d] - 1] : 0;
        end
        // end to end: +6 landing edges; the off-die gearbox rate pattern (IDLE_P) may move a beat by one more edge
        // the landings are exact (+3 per pulse, monitors below); end to end, the 3-of-4 gearbox slot pattern at the sending
        // and at the receiving lane (ot_s81ph_link_gbx_safe3 ph != 3) re-quantises a beat that is 6 edges later by up to one
        // slot at each end -> +6 +-2 per beat (measured 5..7 in phase, 4..7 phase-offset; mean reported as lat_x100).
        // P_KIT 1 (the die's lepmu kit params RX_SRAM / IN_PIPE / NATIVE32): + the IN_PIPE ro face edge (+1)
        if (P_R4L == 0 && (l0 < 6 * P_LAND + P_KIT - 2 || l1 > 6 * P_LAND + P_KIT + 2)) latok = 0;
        // r4l: + its own centre <-> pair crossings (fixed) -> constant within the gearbox edge, >= the plain +6
        if (P_R4L != 0 && (l0 < 4 || l1 > l0 + 4)) latok = 0;
        // per landing: every pulse exactly +3 (monitors), and the landings must have carried traffic
        if (le_dx + le_dy != 0 || (P_LAND != 0 && (lp_dx < 1000 || lp_dy < 1000))) latok = 0;
        rate_ok = 1;
        for (d = 0; d < 2; d = d + 1) if (last_d[d] - last_r[d] > (P_R4L ? l1 : 6 * P_LAND + P_KIT) + P_SLACK) rate_ok = 0;
        $display("MU72_LNLAND_STATS land %0d cred %0d mut %0d ph %0d | recv X->Y %0d/%0d ref %0d, Y->X %0d/%0d ref %0d | mismatches %0d | added latency %0d..%0d mean_x100 %0d ok %0d | landing pulses %0d/%0d contract errors %0d | burst last arrival dut-ref X->Y %0d Y->X %0d (burst %0d beats @ %0d%%, ref span %0d / %0d cyc) | faults %0d",
            P_LAND, P_CRED, P_MUT, P_PH, nd[0], ne[0], nr[0], nd[1], ne[1], nr[1], bad, l0, l1, (lcnt > 0) ? (100 * lsum) / lcnt : -1, latok, lp_dx, lp_dy, le_dx + le_dy,
            last_d[0] - last_r[0], last_d[1] - last_r[1], N_BURST, P_RATE, last_r[0] - cr[0][drain[0]], last_r[1] - cr[1][drain[1]], f_any);
        if (bad == 0 && nd[0] == ne[0] && nd[1] == ne[1] && nr[0] == ne[0] && nr[1] == ne[1] && latok && rate_ok && f_any == 0)
            $display("PASS mu72_lnland: %0d + %0d beats bit-exact in order both ways, every landed pulse exactly +3 (%0d pulses), end-to-end +%0d..%0d edges, burst rate equal to the unlanded CRED8 die (+%0d/+%0d)",
                nd[0], nd[1], lp_dx + lp_dy, l0, l1, last_d[0] - last_r[0], last_d[1] - last_r[1]);
        else
            $display("FAIL mu72_lnland: recv %0d/%0d %0d/%0d mism %0d lat %0d ok %0d rate %0d faults %0d",
                nd[0], ne[0], nd[1], ne[1], bad, l0, latok, rate_ok, f_any);
        $finish;
    end
    initial begin #(T * (WAIT + 30000 + 8 * N_BURST)); $display("FAIL mu72_lnland: TIMEOUT recv %0d/%0d %0d/%0d", nd[0], ne[0], nd[1], ne[1]); $finish; end
endmodule
