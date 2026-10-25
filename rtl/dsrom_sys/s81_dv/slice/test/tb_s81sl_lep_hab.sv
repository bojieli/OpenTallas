`timescale 1ns/1ps
// S81-XDIE (2026-10-24): HOST-PLANE + PAIR-B bench of the s_7N copy-A/B endpoint ot_s81sl_lep_mu_hab (HOST_EN 1, AB_EN 1,
// MU_EN 1; reserve 6th SerDes pair lk_EN2 / lk_EN3 of RELEASE_RACK 2.1).  Die A = ot_s81sl_lep_mu_hab + 4 x dsfd_coll_lane_w
// (LCR 1) + 4 x ot_pdie_ucie (lane 1 / 3 skewed).  Peer H = 4 x dsfd_coll_lane_e + a behavioural frame codec on the lanes'
// core faces: H pair A = the host-side endpoint (as tb_s81sl_lep_host), H pair B = the copy-B peer.
// Traffic, all at once (main phase):
//   H -> A  on pair A: ring beats + HOST frames {h_cls 2, h_d 512} + KS frames: A's ri / f_host / f_ks bit-exact in order;
//   A -> H  ring beats on A's ro at 0.4 + t_host events (t_v words, status changes, one merge case) + t_kd done words, AND
//           copy-B TX tag windows: mu_c {pos, user >= 1, land 0, ab 1, v} then NB XB beats (spare bits 0) at 0.4 while the
//           host plane keeps sending.  H pair A must receive exactly the un-windowed ring beats and one THOST / TKD frame
//           per event, UNSTAMPED, bit-exact, in order; H pair B exactly the windowed beats, stamped [1045] tag 1, [1046]
//           land 0, [1056:1047] user, [1077:1057] pos, bit-exact, in order; pair parity equal per frame;
//   f_lf = {fault, live} x 2 (pair A lanes) = 4'b0101 once live; A.fault 0 at the end of the main phase.
// Phase F: H sends ONE HOST frame on pair B: A must NOT deliver it on f_host (host frames are pair-A only) and must raise
// its sticky fault (protocol error).
// P_PROD 1 = the die opt-ins of the s_7N top (RX_SRAM / IN_PIPE / NATIVE32 1, as ot_s81sl_slice_lepe_mab_mu_72); 0 = defaults.
// Mutants (must FAIL): +define+OT_S81SL_LEP_MUT_WRONGCOPY (windows on pair A), OT_S81SL_LEP_MUT_TAGDROP (no stamp),
//   OT_S81SL_LEP_MUT_HSTAMP (P_PROD 1: host frame stamped inside a window), OT_S81SL_LEP_MUT_HACCB (HOST frame accepted
//   from pair B), OT_S81SL_LEP_MUT_KSOFF (key-store payload one bit off).
// Verdict: "PASS lep_hab ..." or "FAIL lep_hab ...".
module tb_s81sl_lep_hab #(parameter integer N = 400, parameter integer SEED = 3, parameter integer WAIT = 8000,
                          parameter integer NB = 80, parameter integer P_PROD = 0);
    localparam integer TG = 1045;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_ro = 0; wire [1103:0] a_ri; wire a_f; reg [33:0] a_mc = 0; wire [31:0] a_rt;
    reg [76:0] t_host = 0; reg [53:0] t_kd = 0; wire [514:0] f_host; wire [3:0] f_lf; wire [52:0] f_ks;
    wire [3:0] alv, alr, aiv, air; wire [4*553-1:0] ald, aid; wire [11:0] af; wire [3:0] arxv;
    wire [3:0] hlr, hiv; wire [4*553-1:0] hid; wire [11:0] hf;
    reg [1:0] hva = 0, hvb = 0; reg [2*553-1:0] hda = 0, hdb = 0;
    wire [3:0] hlv = {hvb, hva}; wire [4*553-1:0] hld = {hdb, hda};
    wire [4*512-1:0] atx, arx, htx, hrx; wire [7:0] ast, hst;
    wire [4*513-1:0] pa, ph; wire [3:0] ta, th;
    wire mwv; wire [1103:0] mwd;
    ot_s81sl_lep_mu_hab #(.SRAM(1), .NB(NB), .RX_SRAM(P_PROD), .IN_PIPE(P_PROD), .NATIVE32(P_PROD)) la (.clk(clk), .rst_n(rst_n),
        .ro(a_ro), .ri(a_ri),
        .lo0_v(alv[0]), .lo0_r(alr[0]), .lo0_d(ald[0 +: 553]), .lo1_v(alv[1]), .lo1_r(alr[1]), .lo1_d(ald[553 +: 553]),
        .li0_v(aiv[0]), .li0_r(air[0]), .li0_d(aid[0 +: 553]), .li1_v(aiv[1]), .li1_r(air[1]), .li1_d(aid[553 +: 553]),
        .rxv(arxv[1:0]), .sl_f(1'b0), .l0_f(af[2:0]), .l1_f(af[5:3]), .l0_st(ast[1:0]), .l1_st(ast[3:2]),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(a_mc), .mu_rt(a_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
        .lo2_v(alv[2]), .lo2_r(alr[2]), .lo2_d(ald[1106 +: 553]), .lo3_v(alv[3]), .lo3_r(alr[3]), .lo3_d(ald[1659 +: 553]),
        .li2_v(aiv[2]), .li2_r(air[2]), .li2_d(aid[1106 +: 553]), .li3_v(aiv[3]), .li3_r(air[3]), .li3_d(aid[1659 +: 553]),
        .rxvb(arxv[3:2]), .l2_f(af[8:6]), .l3_f(af[11:9]), .fault(a_f));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ln
        dsfd_coll_lane_w #(.LCR(1)) a_l (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast[2*g], ast[2*g+1], arx[512*g +: 512], arxv[g]}),
            .tx(atx[512*g +: 512]), .tf(), .lo_v(alv[g]), .lo_r(alr[g]), .lo_d(ald[553*g +: 553]),
            .li_v(aiv[g]), .li_r(air[g]), .li_d(aid[553*g +: 553]), .flt(af[3*g +: 3]));
        dsfd_coll_lane_e h_l (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst[2*g], hst[2*g+1], hrx[512*g +: 512], rst_n}),
            .tx(htx[512*g +: 512]), .tf(), .lo_v(hlv[g]), .lo_r(hlr[g]), .lo_d(hld[553*g +: 553]),
            .li_v(hiv[g]), .li_r(1'b1), .li_d(hid[553*g +: 553]), .flt(hf[3*g +: 3]));
        ot_pdie_ucie #(.PMA_LAT(g % 2 == 0 ? 2 : 6)) ua (.clk(clk), .rst(rst_n), .tx(atx[512*g +: 512]), .rx(arx[512*g +: 512]),
            .st(ast[2*g +: 2]), .pma_tx(pa[513*g +: 513]), .pma_tck(ta[g]), .pma_rx(ph[513*g +: 513]), .pma_rck(th[g]));
        ot_pdie_ucie #(.PMA_LAT(g % 2 == 0 ? 2 : 6)) uh (.clk(clk), .rst(rst_n), .tx(htx[512*g +: 512]), .rx(hrx[512*g +: 512]),
            .st(hst[2*g +: 2]), .pma_tx(ph[513*g +: 513]), .pma_tck(th[g]), .pma_rx(pa[513*g +: 513]), .pma_rck(ta[g]));
    end endgenerate

    function automatic [1103:0] rnd(input integer dummy);
        integer i; reg [1103:0] b;
        begin for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom; rnd = b; end
    endfunction
    // ---------------- H -> A (pair A): frames to send, and what A must deliver
    reg [1103:0] hs [0:2047]; integer hn = 0, hp0 = 0, hp1 = 0;
    reg [1103:0] er [0:2047]; integer ern = 0, erk = 0;
    reg [513:0]  eh [0:511];  integer ehn = 0, ehk = 0;
    reg [52:0]   ek [0:511];  integer ekn = 0, ekk = 0;
    // ---------------- A -> H: pair A (ring / THOST / TKD per class) and pair B (windowed beats, stamped)
    reg [1103:0] ea [0:4095]; integer ean = 0, eak = 0; reg [1103:0] eth [0:1023]; integer ethn = 0, ethk = 0;
    reg [1103:0] etk [0:1023]; integer etkn = 0, etkk = 0;
    reg [1103:0] eb [0:8191]; integer ebn = 0, ebk = 0;
    reg [1103:0] fx, fy;
    reg [552:0] r0 [0:4095]; reg [552:0] r1 [0:4095]; integer rn0 = 0, rn1 = 0, rk = 0;
    reg [552:0] r2 [0:8191]; reg [552:0] r3 [0:8191]; integer rn2 = 0, rn3 = 0, rkb = 0;
    integer bad = 0, cyc = 0, k, lf_bad = 0, nh = 0, nk = 0, nr = 0, nb = 0, nwin = 0, nhwin = 0, phase_f = 0, fh_f = 0;
    function automatic [1103:0] hfrm(input [2:0] ty, input [513:0] pay);
        begin hfrm = 1104'd0; hfrm[3:1] = ty; hfrm[4 +: 514] = pay; end
    endfunction
    // H transmit on pair A (flit parity = frame index parity on both lanes); pair B driven by phase F only
    reg fb_go = 0; integer fb2 = 0, fb3 = 0;
    reg [1103:0] fbf;
    always @(negedge clk) begin
        hva[0] <= hp0 < hn; hda[0 +: 553] <= {hp0[0], hs[hp0][551:0]};
        hva[1] <= hp1 < hn; hda[553 +: 553] <= {hp1[0], hs[hp1][1103:552]};
        hvb[0] <= fb_go && fb2 < 1; hdb[0 +: 553] <= {1'b0, fbf[551:0]};
        hvb[1] <= fb_go && fb3 < 1; hdb[553 +: 553] <= {1'b0, fbf[1103:552]};
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (hlv[0] && hlr[0]) hp0 = hp0 + 1;
        if (hlv[1] && hlr[1]) hp1 = hp1 + 1;
        if (hlv[2] && hlr[2]) fb2 = fb2 + 1;
        if (hlv[3] && hlr[3]) fb3 = fb3 + 1;
        if (a_ri[0]) begin
            if (erk >= ern || a_ri !== er[erk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH ring H->A %0d", erk); end
            erk = erk + 1;
        end
        if (f_host[0]) begin
            if (phase_f) fh_f = fh_f + 1;
            if (ehk >= ehn || f_host[514:1] !== eh[ehk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH f_host %0d (phase F %0d)", ehk, phase_f); end
            ehk = ehk + 1;
        end
        if (f_ks[52]) begin
            if (ekk >= ekn || f_ks !== ek[ekk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH f_ks %0d got %h exp %h", ekk, f_ks, ek[ekk]); end
            ekk = ekk + 1;
        end
        if (mwv) begin bad = bad + 1; $display("MISMATCH ml_wv (no land window was opened)"); end
        // H pair A receives
        if (hiv[0]) begin r0[rn0] = hid[0 +: 553]; rn0 = rn0 + 1; end
        if (hiv[1]) begin r1[rn1] = hid[553 +: 553]; rn1 = rn1 + 1; end
        while (rk < rn0 && rk < rn1) begin
            fx = {r1[rk][551:0], r0[rk][551:0]};
            if (r0[rk][552] !== r1[rk][552]) begin bad = bad + 1; $display("MISMATCH A->H pair A parity %0d", rk); end
            if (fx[0]) begin
                if (eak >= ean || fx !== ea[eak]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H pair A ring %0d (tag %b)", eak, fx[TG]); end
                eak = eak + 1; nr = nr + 1;
            end else if (fx[3:1] == 3'd3) begin
                if (ethk >= ethn || fx !== eth[ethk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H THOST %0d got %h exp %h", ethk, fx[80:4], eth[ethk][80:4]); end
                if (fx[1103:81] != 0) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H THOST %0d stamped / dirty high bits", ethk); end
                ethk = ethk + 1; nh = nh + 1;
            end else if (fx[3:1] == 3'd4) begin
                if (etkk >= etkn || fx !== etk[etkk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H TKD %0d", etkk); end
                etkk = etkk + 1; nk = nk + 1;
            end else begin bad = bad + 1; $display("MISMATCH A->H unknown frame type %0d", fx[3:1]); end
            rk = rk + 1;
        end
        // H pair B receives (the copy-B peer)
        if (hiv[2]) begin r2[rn2] = hid[1106 +: 553]; rn2 = rn2 + 1; end
        if (hiv[3]) begin r3[rn3] = hid[1659 +: 553]; rn3 = rn3 + 1; end
        while (rkb < rn2 && rkb < rn3) begin
            fy = {r3[rkb][551:0], r2[rkb][551:0]};
            if (r2[rkb][552] !== r3[rkb][552]) begin bad = bad + 1; $display("MISMATCH A->H pair B parity %0d", rkb); end
            if (ebk >= ebn || fy !== eb[ebk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H pair B %0d (tag %b ring %b)", ebk, fy[TG], fy[0]); end
            ebk = ebk + 1; nb = nb + 1; rkb = rkb + 1;
        end
    end
    // ---------------- stimulus
    reg [1103:0] b; reg [11:0] stat; reg [513:0] hp; reg [52:0] kw; reg [63:0] td; integer gap_h, gap_k;
    integer wrem, wpre; reg [9:0] wu; reg [20:0] wp; reg f_main;
    function automatic [1103:0] tframe(input [2:0] ty, input [76:0] w);
        begin tframe = 1104'd0; tframe[3:1] = ty; tframe[4 +: 77] = w; end
    endfunction
    initial begin
        void'($urandom(SEED));
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        if (f_lf !== 4'b0101) lf_bad = lf_bad + 1;
        for (k = 0; k < N; k = k + 1) begin
            case ($urandom % 4)
                0: begin hp = rnd(0); hs[hn] = hfrm(3'd1, hp); hn = hn + 1; eh[ehn] = hp; ehn = ehn + 1; end
                1: begin kw = rnd(0); kw[52] = 1'b1; hs[hn] = hfrm(3'd2, {461'd0, kw}); hn = hn + 1; ek[ekn] = kw; ekn = ekn + 1; end
                default: begin b = rnd(0); b[0] = 1'b1; b[1103:TG] = 0; hs[hn] = b;   // MU endpoint: untagged beat (spare bits 0)
                     hn = hn + 1; er[ern] = b; ern = ern + 1; end
            endcase
        end
        stat = 12'h801; gap_h = 0; gap_k = 0; wrem = 0; wpre = 0;
        @(negedge clk); t_host = {stat, 1'b0, 64'd0};
        @(posedge clk); @(posedge clk); @(posedge clk);
        eth[ethn] = tframe(3'd3, {stat, 1'b0, 64'd0}); ethn = ethn + 1;
        for (k = 0; k < 3 * N; k = k + 1) begin
            @(negedge clk);
            a_ro = 0; a_mc = 0; t_host[64] = 1'b0; t_kd = 54'd0; gap_h = gap_h + 1; gap_k = gap_k + 1;
            if (wpre > 0) wpre = wpre - 1;                                   // window command lead (>= 2 cycles)
            else if (wrem > 0) begin                                         // inside a copy-B window: XB beats only
                if (($urandom % 100) < 40) begin
                    b = rnd(0); b[0] = 1'b1; b[3:1] = 3'd2; b[1103:TG] = 0; a_ro = b;
                    b[TG] = 1'b1; b[TG + 1] = 1'b0; b[TG + 11:TG + 2] = wu; b[TG + 32:TG + 12] = wp;
                    eb[ebn] = b; ebn = ebn + 1; wrem = wrem - 1;
                    if (ph_pending()) nhwin = nhwin + 1;
                end
            end else if (k % 211 == 100 && k < 3 * N - 2 * NB - 300) begin  // open a copy-B TX tag window
                wu = 10'd1 + 10'(nwin % 1000); wp = 21'($urandom);
                a_mc = {wp, wu, 1'b0, 1'b1, 1'b1}; wrem = NB; wpre = 3; nwin = nwin + 1;
            end else if (($urandom % 100) < 40) begin b = rnd(0); b[0] = 1'b1; a_ro = b; ea[ean] = b; ean = ean + 1; end
            if (k % 97 == 50 && gap_h > 16) begin
                stat = $urandom; t_host[76:65] = stat; gap_h = 0;
                eth[ethn] = tframe(3'd3, {stat, 1'b0, t_host[63:0]}); ethn = ethn + 1;
            end else if (gap_h > 16 && ($urandom % 8) == 0) begin
                td = {$urandom, $urandom}; t_host = {stat, 1'b1, td}; gap_h = 0;
                eth[ethn] = tframe(3'd3, {stat, 1'b1, td}); ethn = ethn + 1;
            end
            if (k % 23 == 7) begin
                t_kd = {1'b1, 21'($urandom), 32'd0}; gap_k = 0;
                etk[etkn] = tframe(3'd4, {23'd0, t_kd}); etkn = etkn + 1;
            end
        end
        while (wpre > 0 || wrem > 0) begin                                   // close an open window (XB beats only)
            @(negedge clk); a_ro = 0; a_mc = 0; t_host[64] = 1'b0; t_kd = 54'd0;
            if (wpre > 0) wpre = wpre - 1;
            else begin b = rnd(0); b[0] = 1'b1; b[3:1] = 3'd2; b[1103:TG] = 0; a_ro = b;
                b[TG] = 1'b1; b[TG + 1] = 1'b0; b[TG + 11:TG + 2] = wu; b[TG + 32:TG + 12] = wp; eb[ebn] = b; ebn = ebn + 1; wrem = wrem - 1; end
        end
        // merge case (as tb_s81sl_lep_host): 12 back-to-back ring beats; t_v at beat 2, status change at beat 4 -> ONE THOST
        for (k = 0; k < 12; k = k + 1) begin
            @(negedge clk);
            b = rnd(0); b[0] = 1'b1; a_ro = b; ea[ean] = b; ean = ean + 1;
            t_host[64] = 1'b0;
            if (k == 2) begin td = {$urandom, $urandom}; t_host = {stat, 1'b1, td}; end
            if (k == 4) begin stat = stat ^ 12'h5a5; t_host[76:65] = stat; end
        end
        @(negedge clk); a_ro = 0; t_host[64] = 1'b0;
        eth[ethn] = tframe(3'd3, {stat, 1'b1, td}); ethn = ethn + 1;
        repeat (4000) @(posedge clk);
        if (f_lf !== 4'b0101) lf_bad = lf_bad + 1;
        f_main = a_f;
        $display("LEPHAB_STATS H->A ring %0d/%0d host %0d/%0d ks %0d/%0d | A->H pairA %0d/%0d (ring %0d thost %0d tkd %0d) pairB %0d/%0d in %0d windows (host events inside windows %0d) | mismatches %0d f_lf %b bad %0d fault %0d",
            erk, ern, ehk, ehn, ekk, ekn, rk, ean + ethn + etkn, nr, nh, nk, nb, ebn, nwin, nhwin, bad, f_lf, lf_bad, a_f);
        // ---------------- phase F: a HOST frame on pair B must not reach f_host and must fault
        phase_f = 1; hp = rnd(0); fbf = hfrm(3'd1, hp);
        @(negedge clk); fb_go = 1;
        repeat (600) @(posedge clk);
        $display("LEPHAB_F host-on-pairB: f_host pulses %0d (want 0), fault %0d (want 1)", fh_f, a_f);
        if (bad == 0 && erk == ern && ehk == ehn && ekk == ekn && eak == ean && ethk == ethn && etkk == etkn && ebk == ebn &&
            nwin >= 3 && nhwin > 0 && lf_bad == 0 && !f_main && fh_f == 0 && a_f)
            $display("PASS lep_hab: H->A %0d ring + %0d HOST + %0d KS; A->H pair A %0d frames (%0d THOST incl. 1 merge, %0d TKD, unstamped), pair B %0d stamped beats in %0d windows (%0d with host frames pending); host-on-pair-B rejected + fault; P_PROD %0d",
                ern, ehn, ekn, rk, nh, nk, ebn, nwin, nhwin, P_PROD);
        else $display("FAIL lep_hab: mismatches %0d main-fault %0d f_host-in-F %0d fault-after-F %0d pairB %0d/%0d windows %0d", bad, f_main, fh_f, a_f, ebk, ebn, nwin);
        $finish;
    end
    // a host frame is pending while a window beat is pushed (coverage only: THOST / TKD events not yet seen at H)
    function automatic bit ph_pending(); ph_pending = (ethn > ethk) || (etkn > etkk); endfunction
    initial begin #(0.8333 * (WAIT + 80 * N + 40000)); $display("FAIL lep_hab: TIMEOUT"); $finish; end
endmodule
