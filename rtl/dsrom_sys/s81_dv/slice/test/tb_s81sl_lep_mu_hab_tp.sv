`timescale 1ns/1ps
// MU-S81/LINK (2026-10-18): multi-user stage hand-off bench of the end-slice link endpoint (ot_s81sl_lep_mu + NEW leaf
// dsdv_mu_land + the hardened lane tiles dsfd_coll_lane_w / _e LCR 1 + ot_pdie_ucie behavioural PMA, lane 1 skewed).
// Dies: P = the stage BEFORE a duplicated group (W end, AB_EN 1: pair A lanes -> copy A die, pair B lanes -> copy B die);
//       A / B = the two copies' receiving end slices (E end, MU_EN 1, each with its dsdv_mu_land, NB beats a message);
//       RP -> RA = the single-user reference (pre-MU leaf tops ot_s81sl_lep_nh, same PMA latencies) driven with ONLY the
//       latency user's traffic at the same cycles.
// Static calendar (slot S): user u's h message (NB XB beats, rate ~0.6, pos 100 + u) leaves P at T0 + u S under a TX tag
// window {u, pos, land, ab}: u0 A cut-through (latency user), u1 B land, u2 A land, u3 B cut, u4 B land (re-uses the slot
// u1's replay freed), u5 A cut; plus untagged background ring beats before T0 (pair A).  Replays (compiler slots) at
// T0 + u S + R on the receiving die.  Checks:
//   every beat on the right die, bit-exact, in order, tag stripped on ri, mu_rt = {1, user, pos} (0 for untagged);
//   the latency user's beats (and the background) reach A's ri at the SAME cycles and bits as the single-user RA run;
//   no fault in the main phase; then F1 two landed messages without a replay (write to a full slot) -> A fault,
//   F2 replay of an empty slot -> B fault, F3 ab = 1 for user 0 -> P fault.
// RETURN phase (MU-S81-2/RX 10-19: the A/B master's RX = post-group endpoint, pair-B merge + land on both pairs): after the
//   main phase dies A and B transmit back to P one after the other (static calendar, no pair collision): A untagged
//   NB beats, B user 3 cut-through, B user 4 land, A user 5 cut-through, A user 2 land.  P's ri must carry the cut-through
//   / untagged beats bit-exact in order with mu_rt, and P's ml_wv / ml_wd the landed beats (tag kept), no fault.
// Mutant +define+OT_S81SL_LEP_MUT_STALEHD (RX head register without show-ahead) must fail.
// Mutants: +define+OT_S81SL_LEP_MUT_TAGDROP, +define+OT_S81SL_LEP_MUT_WRONGCOPY, +define+OT_DSDV_MU_LAND_MUT_OVR,
//          +define+OT_S81SL_LEP_MUT_LANDCUT (RX side: dies A / B).
// Verdict: "PASS lep_mu ..." or "FAIL lep_mu ...".
// S81-LINK5 L5B-LEPBENCH (10-21): P_RX_SRAM / P_IN_PIPE / P_NATIVE32 = die P's ot_s81sl_lep_mu_ab opt-ins (kits
//   s81sl_lepmu_t5c / _t5d set all three to 1; defaults 0 = the original s81sl_lepmu bench).  IN_PIPE puts one registered
//   face stage on ro / mu_c (+1 edge on both, same relative timing).  The lanes move flit pairs, so a +1 input shift is
//   NOT a constant +1 at A's ri (a beat that queued behind its predecessor in the reference arrives at the same cycle);
//   the single-user reference RP therefore sees the same face stage (rp_ro registered P_IN_PIPE times, as P's ro_x) and
//   the latency-user identity stays cycle- and bit-exact A vs RA.
module tb_s81sl_lep_mu_hab_tp #(parameter integer NB = 80, parameter integer S = 700, parameter integer R = 420,
                         parameter integer SEED = 1, parameter integer WAIT = 8000,
                         parameter integer P_RX_SRAM = 0, parameter integer P_IN_PIPE = 0, parameter integer P_NATIVE32 = 0);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // ------------------------------------------------------------------ die P (pre-group, AB_EN 1)
    reg [1103:0] p_ro = 0, rp_ro = 0; reg [33:0] p_mc = 0; reg [10:0] a_rc = 0, b_rc = 0;
    reg [1103:0] a_ro = 0, b_ro = 0; reg [33:0] a_mc = 0, b_mc = 0;      // RETURN phase: dies A / B transmit to P
    wire p_mwv; wire [1103:0] p_mwd;
    wire [1103:0] p_ri, a_ri, b_ri, rp_ri, ra_ri; wire [31:0] a_rt, b_rt, p_rt; wire p_f, a_f, b_f, rp_f, ra_f;
    wire [3:0] plv, plr, piv, pir; wire [4*553-1:0] pld, pid; wire [11:0] pf; wire [3:0] prxv;
    wire [4*512-1:0] ptx, prx; wire [7:0] pst; wire [4*513-1:0] ppa; wire [3:0] pta;
    // MU-S81/KIT: die P = the hardened copy A/B master ot_s81sl_lep_mu_ab (kit s81sl_lepmu; = lep_mu HOST_EN 0 AB_EN 1)
    ot_s81sl_lep_mu_hab_tp #(.SRAM(1), .NB(NB), .RX_SRAM(P_RX_SRAM), .IN_PIPE(P_IN_PIPE), .NATIVE32(P_NATIVE32)) lp (.t_host(77'd0), .t_kd(54'd0), .l0_st(2'd0), .l1_st(2'd0), .f_host(), .f_lf(), .f_ks(), .tp_i(276'd0), .tp_o(), .clk(clk), .rst_n(rst_n), .ro(p_ro), .ri(p_ri),
        .lo0_v(plv[0]), .lo0_r(plr[0]), .lo0_d(pld[0 +: 553]), .lo1_v(plv[1]), .lo1_r(plr[1]), .lo1_d(pld[553 +: 553]),
        .li0_v(piv[0]), .li0_r(pir[0]), .li0_d(pid[0 +: 553]), .li1_v(piv[1]), .li1_r(pir[1]), .li1_d(pid[553 +: 553]),
        .rxv(prxv[1:0]), .sl_f(1'b0), .l0_f(pf[2:0]), .l1_f(pf[5:3]),
        .mu_c(p_mc), .mu_rt(p_rt), .ml_wv(p_mwv), .ml_wd(p_mwd), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
        .lo2_v(plv[2]), .lo2_r(plr[2]), .lo2_d(pld[1106 +: 553]), .lo3_v(plv[3]), .lo3_r(plr[3]), .lo3_d(pld[1659 +: 553]),
        .li2_v(piv[2]), .li2_r(pir[2]), .li2_d(pid[1106 +: 553]), .li3_v(piv[3]), .li3_r(pir[3]), .li3_d(pid[1659 +: 553]),
        .rxvb(prxv[3:2]), .l2_f(pf[8:6]), .l3_f(pf[11:9]), .fault(p_f));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_pl
        dsfd_coll_lane_w #(.LCR(1)) u_l (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({pst[2*g], pst[2*g+1], prx[512*g +: 512], prxv[g]}),
            .tx(ptx[512*g +: 512]), .tf(), .lo_v(plv[g]), .lo_r(plr[g]), .lo_d(pld[553*g +: 553]),
            .li_v(piv[g]), .li_r(pir[g]), .li_d(pid[553*g +: 553]), .flt(pf[3*g +: 3]));
    end endgenerate
    // ------------------------------------------------------------------ dies A / B (copies, MU_EN 1, AB_EN 0) + landing
    // MU-S81b: dies A / B = the hardened copy-A-only master ot_s81sl_lep_mu_a (kit s81sl_lepmua; = lep_mu HOST_EN 0 AB_EN 0)
    `define TB_RXDIE(X, LP) \
    wire [1:0] X``lv, X``lr, X``iv, X``ir, X``rxv; wire [2*553-1:0] X``ld, X``id; wire [5:0] X``fl; \
    wire [1023:0] X``tx, X``rx; wire [3:0] X``st; wire X``mwv, X``mrv, X``mf; wire [1103:0] X``mwd, X``mrd; \
    ot_s81sl_lep_mu_a #(.SRAM(1), .NB(NB)) l``X (.clk(clk), .rst_n(rst_n), .ro(X``_ro), .ri(X``_ri), \
        .lo0_v(X``lv[0]), .lo0_r(X``lr[0]), .lo0_d(X``ld[0 +: 553]), .lo1_v(X``lv[1]), .lo1_r(X``lr[1]), .lo1_d(X``ld[553 +: 553]), \
        .li0_v(X``iv[0]), .li0_r(X``ir[0]), .li0_d(X``id[0 +: 553]), .li1_v(X``iv[1]), .li1_r(X``ir[1]), .li1_d(X``id[553 +: 553]), \
        .rxv(X``rxv), .sl_f(1'b0), .l0_f(X``fl[2:0]), .l1_f(X``fl[5:3]), \
        .mu_c(X``_mc), .mu_rt(X``_rt), .ml_wv(X``mwv), .ml_wd(X``mwd), .ml_rv(X``mrv), .ml_rd(X``mrd), .ml_f(X``mf), \
        .fault(X``_f)); \
    dsdv_mu_land #(.NB(NB), .NS(1), .SRAM(1)) m``X (.clk(clk), .rst_n(rst_n), .wv(X``mwv), .wd(X``mwd), .rc(X``_rc), \
        .rv(X``mrv), .rd(X``mrd), .fault(X``mf)); \
    dsfd_coll_lane_e #(.LCR(1)) X``_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({X``st[0], X``st[1], X``rx[511:0], X``rxv[0]}), \
        .tx(X``tx[511:0]), .tf(), .lo_v(X``lv[0]), .lo_r(X``lr[0]), .lo_d(X``ld[0 +: 553]), \
        .li_v(X``iv[0]), .li_r(X``ir[0]), .li_d(X``id[0 +: 553]), .flt(X``fl[2:0])); \
    dsfd_coll_lane_e #(.LCR(1)) X``_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({X``st[2], X``st[3], X``rx[1023:512], X``rxv[1]}), \
        .tx(X``tx[1023:512]), .tf(), .lo_v(X``lv[1]), .lo_r(X``lr[1]), .lo_d(X``ld[553 +: 553]), \
        .li_v(X``iv[1]), .li_r(X``ir[1]), .li_d(X``id[553 +: 553]), .flt(X``fl[5:3])); \
    wire [512:0] X``pa0, X``pa1, X``pb0, X``pb1; wire X``ta0, X``ta1, X``tb0, X``tb1; \
    ot_pdie_ucie #(.PMA_LAT(2)) X``_up0 (.clk(clk), .rst(rst_n), .tx(ptx[512*(LP) +: 512]), .rx(prx[512*(LP) +: 512]), .st(pst[2*(LP) +: 2]), \
        .pma_tx(X``pa0), .pma_tck(X``ta0), .pma_rx(X``pb0), .pma_rck(X``tb0)); \
    ot_pdie_ucie #(.PMA_LAT(2)) X``_ux0 (.clk(clk), .rst(rst_n), .tx(X``tx[511:0]), .rx(X``rx[511:0]), .st(X``st[1:0]), \
        .pma_tx(X``pb0), .pma_tck(X``tb0), .pma_rx(X``pa0), .pma_rck(X``ta0)); \
    ot_pdie_ucie #(.PMA_LAT(9)) X``_up1 (.clk(clk), .rst(rst_n), .tx(ptx[512*(LP+1) +: 512]), .rx(prx[512*(LP+1) +: 512]), .st(pst[2*(LP+1) +: 2]), \
        .pma_tx(X``pa1), .pma_tck(X``ta1), .pma_rx(X``pb1), .pma_rck(X``tb1)); \
    ot_pdie_ucie #(.PMA_LAT(9)) X``_ux1 (.clk(clk), .rst(rst_n), .tx(X``tx[1023:512]), .rx(X``rx[1023:512]), .st(X``st[3:2]), \
        .pma_tx(X``pb1), .pma_tck(X``tb1), .pma_rx(X``pa1), .pma_rck(X``ta1));
    `TB_RXDIE(a, 0)
    `TB_RXDIE(b, 2)
    // ------------------------------------------------------------------ single-user reference RP -> RA (pre-MU tops)
    wire [1:0] rplv, rplr, rpiv, rpir, rprxv, ralv, ralr, raiv, rair, rarxv; wire [2*553-1:0] rpld, rpid, rald, raid;
    wire [5:0] rpfl, rafl; wire [1023:0] rptx, rprx, ratx, rarx; wire [3:0] rpst, rast;
    reg [1103:0] rp_rod [0:3]; wire [1103:0] rp_rox = (P_IN_PIPE != 0) ? rp_rod[P_IN_PIPE - 1] : rp_ro;
    always @(posedge clk) begin rp_rod[0] <= rp_ro; rp_rod[1] <= rp_rod[0]; rp_rod[2] <= rp_rod[1]; rp_rod[3] <= rp_rod[2]; end
    ot_s81sl_lep_nh lrp (.clk(clk), .rst_n(rst_n), .ro(rp_rox), .ri(rp_ri),
        .lo0_v(rplv[0]), .lo0_r(rplr[0]), .lo0_d(rpld[0 +: 553]), .lo1_v(rplv[1]), .lo1_r(rplr[1]), .lo1_d(rpld[553 +: 553]),
        .li0_v(rpiv[0]), .li0_r(rpir[0]), .li0_d(rpid[0 +: 553]), .li1_v(rpiv[1]), .li1_r(rpir[1]), .li1_d(rpid[553 +: 553]),
        .rxv(rprxv), .sl_f(1'b0), .l0_f(rpfl[2:0]), .l1_f(rpfl[5:3]), .fault(rp_f));
    ot_s81sl_lep_nh lra (.clk(clk), .rst_n(rst_n), .ro(1104'd0), .ri(ra_ri),
        .lo0_v(ralv[0]), .lo0_r(ralr[0]), .lo0_d(rald[0 +: 553]), .lo1_v(ralv[1]), .lo1_r(ralr[1]), .lo1_d(rald[553 +: 553]),
        .li0_v(raiv[0]), .li0_r(rair[0]), .li0_d(raid[0 +: 553]), .li1_v(raiv[1]), .li1_r(rair[1]), .li1_d(raid[553 +: 553]),
        .rxv(rarxv), .sl_f(1'b0), .l0_f(rafl[2:0]), .l1_f(rafl[5:3]), .fault(ra_f));
    generate for (g = 0; g < 2; g = g + 1) begin : g_rl
        dsfd_coll_lane_w #(.LCR(1)) u_p (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({rpst[2*g], rpst[2*g+1], rprx[512*g +: 512], rprxv[g]}),
            .tx(rptx[512*g +: 512]), .tf(), .lo_v(rplv[g]), .lo_r(rplr[g]), .lo_d(rpld[553*g +: 553]),
            .li_v(rpiv[g]), .li_r(rpir[g]), .li_d(rpid[553*g +: 553]), .flt(rpfl[3*g +: 3]));
        dsfd_coll_lane_e #(.LCR(1)) u_a (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({rast[2*g], rast[2*g+1], rarx[512*g +: 512], rarxv[g]}),
            .tx(ratx[512*g +: 512]), .tf(), .lo_v(ralv[g]), .lo_r(ralr[g]), .lo_d(rald[553*g +: 553]),
            .li_v(raiv[g]), .li_r(rair[g]), .li_d(raid[553*g +: 553]), .flt(rafl[3*g +: 3]));
        wire [512:0] pa, pb; wire ta, tb;
        ot_pdie_ucie #(.PMA_LAT(g == 0 ? 2 : 9)) u_up (.clk(clk), .rst(rst_n), .tx(rptx[512*g +: 512]), .rx(rprx[512*g +: 512]),
            .st(rpst[2*g +: 2]), .pma_tx(pa), .pma_tck(ta), .pma_rx(pb), .pma_rck(tb));
        ot_pdie_ucie #(.PMA_LAT(g == 0 ? 2 : 9)) u_ua (.clk(clk), .rst(rst_n), .tx(ratx[512*g +: 512]), .rx(rarx[512*g +: 512]),
            .st(rast[2*g +: 2]), .pma_tx(pb), .pma_tck(tb), .pma_rx(pa), .pma_rck(ta));
    end endgenerate

    // ------------------------------------------------------------------ scoreboards
    localparam integer QN = 4096;
    reg [1103:0] eqa [0:QN-1]; reg [31:0] eta [0:QN-1]; reg [1103:0] eqb [0:QN-1]; reg [31:0] etb [0:QN-1];
    reg [1103:0] lqd [0:15][0:255]; integer lqn [0:15];               // landed beats per user (expected replay order)
    integer na = 0, nb = 0, ra = 0, rb = 0, bad = 0, badt = 0;
    // latency-user identity: A's ri vs RA's ri for the reference traffic (background + user 0), cycle and bits
    reg [1103:0] ida [0:1023]; integer ica [0:1023]; reg [1103:0] idr [0:1023]; integer icr [0:1023];
    integer nia = 0, nir = 0, mtag = 0;
    reg [1103:0] eqp [0:1023]; reg [31:0] etp [0:1023]; reg [1103:0] eqm [0:1023];   // RETURN: P ri / P landing port
    integer np = 0, rpn = 0, nm = 0, rmn = 0;
    always @(posedge clk) begin
        if (a_ri[0]) begin
            if (ra >= na || a_ri !== eqa[ra] || a_rt !== eta[ra]) begin
                bad = bad + 1;
                if (bad < 8) $display("MISMATCH A beat %0d cyc %0d: got %h.. rt %h exp %h.. rt %h", ra, cyc, a_ri[63:0], a_rt,
                    eqa[ra][63:0], eta[ra]);
            end
            if (a_rt[31] == 1'b0 || a_rt[30:21] == 10'd0) begin ida[nia] = a_ri; ica[nia] = cyc; nia = nia + 1; end
            ra = ra + 1;
        end
        if (b_ri[0]) begin
            if (rb >= nb || b_ri !== eqb[rb] || b_rt !== etb[rb]) begin
                bad = bad + 1;
                if (bad < 8) $display("MISMATCH B beat %0d cyc %0d: got %h.. rt %h exp %h.. rt %h", rb, cyc, b_ri[63:0], b_rt,
                    eqb[rb][63:0], etb[rb]);
            end
            rb = rb + 1;
        end
        if (ra_ri[0]) begin idr[nir] = ra_ri; icr[nir] = cyc; nir = nir + 1; end
        if (p_ri[0]) begin                                            // RETURN phase only
            if (rpn >= np || p_ri !== eqp[rpn] || p_rt !== etp[rpn]) begin
                bad = bad + 1;
                if (bad < 8) $display("MISMATCH P beat %0d cyc %0d: got %h.. rt %h exp %h.. rt %h", rpn, cyc, p_ri[63:0], p_rt,
                    eqp[rpn][63:0], etp[rpn]);
            end
            rpn = rpn + 1;
        end
        if (p_mwv) begin
            if (rmn >= nm || p_mwd !== eqm[rmn]) begin
                bad = bad + 1;
                if (bad < 8) $display("MISMATCH P landed beat %0d cyc %0d: got %h..", rmn, cyc, p_mwd[63:0]);
            end
            rmn = rmn + 1;
        end
    end
    function automatic [1103:0] xb(input integer dummy);              // an XB ring beat (spare bits 0, as ot_s81sl_vq)
        integer i; reg [1103:0] b;
        begin
            b = 0; for (i = 0; i < 32; i = i + 1) b[21 + 32 * i +: 32] = $urandom;
            b[20:13] = $urandom; b[12:9] = $urandom; b[8:4] = 5'd1 + ($urandom % 8); b[3:1] = 3'd2; b[0] = 1'b1; xb = b;
        end
    endfunction
    // per-user calendar: copy (1 = B), land
    function automatic integer cp(input integer u); cp = (u == 1 || u == 3 || u == 4) ? 1 : 0; endfunction
    function automatic integer ld(input integer u); ld = (u == 1 || u == 2 || u == 4 || u >= 6) ? 1 : 0; endfunction
    integer T0, u, k, f_main, fa1, fb2, fp3, idok;
    reg [1103:0] bt;
    task automatic send_msg(input integer uu, input integer abv, input integer ref_too);
        integer kk;
        begin
            @(negedge clk); p_mc = {21'(100 + uu), 10'(uu), 1'(ld(uu)), 1'(abv), 1'b1};
            @(negedge clk); p_mc = 0;
            repeat (3) @(negedge clk);
            kk = 0;
            while (kk < NB) begin
                p_ro = 0; rp_ro = 0;
                if (($urandom % 100) < 60) begin
                    bt = xb(0); p_ro = bt; if (ref_too) rp_ro = bt;
                    if (ld(uu) != 0) begin
                        lqd[uu][kk] = bt;
                    end else if (cp(uu) == 0 || abv == 0) begin
                        eqa[na] = bt; eta[na] = {1'b1, 10'(uu), 21'(100 + uu)}; na = na + 1;
                    end else begin
                        eqb[nb] = bt; etb[nb] = {1'b1, 10'(uu), 21'(100 + uu)}; nb = nb + 1;
                    end
                    kk = kk + 1;
                end
                @(negedge clk);
            end
            p_ro = 0; rp_ro = 0; lqn[uu] = NB;
        end
    endtask
    task automatic replay(input integer uu, input integer onb);       // compiler replay slot on die A (0) / B (1)
        integer kk;
        begin
            for (kk = 0; kk < lqn[uu]; kk = kk + 1)
                if (onb != 0) begin eqb[nb] = lqd[uu][kk]; etb[nb] = {1'b1, 10'(uu), 21'(100 + uu)}; nb = nb + 1; end
                else begin eqa[na] = lqd[uu][kk]; eta[na] = {1'b1, 10'(uu), 21'(100 + uu)}; na = na + 1; end
            @(negedge clk); if (onb != 0) b_rc = {10'(uu), 1'b1}; else a_rc = {10'(uu), 1'b1};
            @(negedge clk); a_rc = 0; b_rc = 0;
        end
    endtask
    task automatic send_ret(input integer onb, input integer uu, input integer lnd, input integer tgd);
        integer kk; reg [1103:0] bs;
        begin
            if (tgd != 0) begin
                @(negedge clk); if (onb != 0) b_mc = {21'(200 + uu), 10'(uu), 1'(lnd), 1'b0, 1'b1};
                                else a_mc = {21'(200 + uu), 10'(uu), 1'(lnd), 1'b0, 1'b1};
                @(negedge clk); a_mc = 0; b_mc = 0;
                repeat (3) @(negedge clk);
            end
            kk = 0;
            while (kk < NB) begin
                a_ro = 0; b_ro = 0;
                if (($urandom % 100) < 60) begin
                    bt = xb(0); if (onb != 0) b_ro = bt; else a_ro = bt;
                    if (tgd != 0 && lnd != 0) begin
                        bs = bt; bs[1045 +: 33] = {21'(200 + uu), 10'(uu), 1'b1, 1'b1}; eqm[nm] = bs; nm = nm + 1;
                    end else begin
                        eqp[np] = bt; etp[np] = (tgd != 0) ? {1'b1, 10'(uu), 21'(200 + uu)} : 32'd0; np = np + 1;
                    end
                    kk = kk + 1;
                end
                @(negedge clk);
            end
            a_ro = 0; b_ro = 0;
            repeat (300) @(negedge clk);                              // drain: the next sender's beats never collide
        end
    endtask
    initial begin
        void'($urandom(SEED));
        for (u = 0; u < 16; u = u + 1) lqn[u] = 0;
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);                                 // link-up
        // background (untagged collective-like ring beats, pair A), mirrored to the reference
        k = 0;
        while (k < 40) begin
            @(negedge clk); p_ro = 0; rp_ro = 0;
            if (($urandom % 100) < 50) begin bt = xb(0); p_ro = bt; rp_ro = bt; eqa[na] = bt; eta[na] = 0; na = na + 1; k = k + 1; end
        end
        @(negedge clk); p_ro = 0; rp_ro = 0;
        T0 = cyc + 200;
        fork
            begin                                                     // P: the static calendar of the 6 users
                for (u = 0; u < 6; u = u + 1) begin
                    while (cyc < T0 + u * S) @(negedge clk);
                    send_msg(u, cp(u), u == 0);
                end
            end
            begin                                                     // receivers: replay slots
                while (cyc < T0 + 1 * S + R) @(negedge clk); replay(1, 1);
                while (cyc < T0 + 2 * S + R) @(negedge clk); replay(2, 0);
                while (cyc < T0 + 4 * S + R) @(negedge clk); replay(4, 1);
            end
        join
        while (cyc < T0 + 6 * S) @(negedge clk);
        // ---- RETURN phase: A / B -> P (pair A / pair B of the A/B master), one sender at a time
        send_ret(0, 0, 0, 0); send_ret(1, 3, 0, 1); send_ret(1, 4, 1, 1); send_ret(0, 5, 0, 1); send_ret(0, 2, 1, 1);
        f_main = {p_f, a_f, b_f, rp_f, ra_f, ma.fault, mb.fault};
        // ---- latency-user identity (A vs single-user RA)
        idok = (nia == nir && nia == 40 + NB) ? 1 : 0;
        for (k = 0; k < nia && k < nir; k = k + 1) if (ica[k] != icr[k] || ida[k] !== idr[k]) begin
            if (idok) $display("IDENT_MISMATCH beat %0d: A cyc %0d ref cyc %0d bits %0d", k, ica[k], icr[k],
                ida[k] === idr[k]);
            idok = 0;
        end
        // ---- fault phase
        send_msg(6, 0, 0);                                            // F1: two landed messages to A without a replay
        while (cyc < T0 + 6 * S + 300) @(negedge clk);
        send_msg(7, 0, 0);
        repeat (400) @(negedge clk);
        fa1 = a_f;
        @(negedge clk); b_rc = {10'd9, 1'b1}; @(negedge clk); b_rc = 0;   // F2: replay of an empty slot on B
        repeat (20) @(negedge clk);
        fb2 = b_f;
        @(negedge clk); p_mc = {21'd5, 10'd0, 1'b0, 1'b1, 1'b1}; @(negedge clk); p_mc = 0;   // F3: ab = 1 for user 0
        repeat (20) @(negedge clk);
        fp3 = p_f;
        $display("LEP_MU_STATS A recv %0d/%0d B recv %0d/%0d mismatches %0d | latency user identity %0d (A %0d beats, ref %0d) | main faults %b | F1 full-slot %0d F2 empty-replay %0d F3 ab-user0 %0d | return P ri %0d/%0d landed %0d/%0d",
            ra, na, rb, nb, bad, idok, nia, nir, f_main[6:0], fa1, fb2, fp3, rpn, np, rmn, nm);
        if (bad == 0 && ra == na && rb == nb && na == 40 + 3 * NB && nb == 3 * NB && idok && f_main[6:0] == 0 && fa1 && fb2 && fp3
            && rpn == np && np == 3 * NB && rmn == nm && nm == 2 * NB)
            $display("PASS lep_mu: 6 users on the static calendar, copies A/B by the slot bit (user 0 on A), %0d + %0d beats bit-exact with tags, 2 landed + replayed per copy, latency user cycle- and bit-identical to the single-user run (%0d beats), F1/F2/F3 faulted; return to the A/B master over pairs A and B: %0d cut-through and %0d landed beats exact", ra, rb, nia, rpn, rmn);
        else
            $display("FAIL lep_mu: recv A %0d/%0d B %0d/%0d mismatches %0d identity %0d main faults %b F1 %0d F2 %0d F3 %0d return P %0d/%0d L %0d/%0d",
                ra, na, rb, nb, bad, idok, f_main[6:0], fa1, fb2, fp3, rpn, np, rmn, nm);
        $finish;
    end
    initial begin #(0.8333 * (WAIT + 12 * S + 20000)); $display("FAIL lep_mu: TIMEOUT recv A %0d/%0d B %0d/%0d", ra, na, rb, nb); $finish; end
endmodule
