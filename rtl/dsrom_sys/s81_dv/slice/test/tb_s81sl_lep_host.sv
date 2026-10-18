`timescale 1ns/1ps
// RTL-BUILD-S81 (2026-10-18): HOST-PLANE bench of the end-slice link port.  Die A = ot_s81sl_lep + 2 x dsfd_coll_lane_w
// + 2 x ot_pdie_ucie (the accelerator end slice, seq_host ports on the lep).  Peer H = 2 x dsfd_coll_lane_e + 2 x
// ot_pdie_ucie + a behavioural host-side frame codec on the lanes' core faces (the off-die host endpoint model).
// Traffic, all at once, both directions:
//   H -> A  ring beats (bit 0 = 1) + HOST frames {h_cls 2, h_d 512} + KS frames {start, user, tok, pos}: A's ri,
//           f_host and f_ks must reproduce them bit-exact and in order;
//   A -> H  ring beats on A's ro + seq_host t_host events (t_v words, status changes) + t_kd done words: H must receive
//           the ring beats and exactly one THOST / TKD frame per event, bit-exact, in order; plus one merge case (a status
//           change while a t_v frame is still pending behind back-to-back ring beats -> ONE frame {new status, t_v, t_d}).
//   f_lf = {fault, live} x 2 must read 4'b0101 once the lanes are live; A.fault must stay 0.
// Verdict: "PASS lep_host ..." or "FAIL lep_host ...".
module tb_s81sl_lep_host #(parameter integer N = 400, parameter integer SEED = 3, parameter integer WAIT = 8000);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_ro = 0; wire [1103:0] a_ri; wire a_f;
    reg [76:0] t_host = 0; reg [53:0] t_kd = 0; wire [514:0] f_host; wire [3:0] f_lf; wire [52:0] f_ks;
    wire a0v, a0r, a1v, a1r, ai0v, ai0r, ai1v, ai1r; wire [552:0] a0d, a1d, ai0d, ai1d; wire [2:0] af0, af1; wire [1:0] arxv;
    wire h0r, h1r, hi0v, hi1v; wire [552:0] hi0d, hi1d; wire [2:0] hf0, hf1;
    reg h0v = 0, h1v = 0; reg [552:0] h0d = 0, h1d = 0;
    wire [511:0] atx0, atx1, htx0, htx1, arx0, arx1, hrx0, hrx1; wire [1:0] ast0, ast1, hst0, hst1;
    wire [512:0] pa0, pa1, ph0, ph1; wire ta0, ta1, th0, th1;
    ot_s81sl_lep la (.clk(clk), .rst_n(rst_n), .ro(a_ro), .ri(a_ri),
        .lo0_v(a0v), .lo0_r(a0r), .lo0_d(a0d), .lo1_v(a1v), .lo1_r(a1r), .lo1_d(a1d),
        .li0_v(ai0v), .li0_r(ai0r), .li0_d(ai0d), .li1_v(ai1v), .li1_r(ai1r), .li1_d(ai1d), .rxv(arxv),
        .sl_f(1'b0), .l0_f(af0), .l1_f(af1), .l0_st(ast0), .l1_st(ast1),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .fault(a_f));
    dsfd_coll_lane_w #(.LCR(1)) a_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast0[0], ast0[1], arx0, arxv[0]}), .tx(atx0), .tf(),
        .lo_v(a0v), .lo_r(a0r), .lo_d(a0d), .li_v(ai0v), .li_r(ai0r), .li_d(ai0d), .flt(af0));
    dsfd_coll_lane_w #(.LCR(1)) a_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({ast1[0], ast1[1], arx1, arxv[1]}), .tx(atx1), .tf(),
        .lo_v(a1v), .lo_r(a1r), .lo_d(a1d), .li_v(ai1v), .li_r(ai1r), .li_d(ai1d), .flt(af1));
    dsfd_coll_lane_e h_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst0[0], hst0[1], hrx0, rst_n}), .tx(htx0), .tf(),
        .lo_v(h0v), .lo_r(h0r), .lo_d(h0d), .li_v(hi0v), .li_r(1'b1), .li_d(hi0d), .flt(hf0));
    dsfd_coll_lane_e h_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({hst1[0], hst1[1], hrx1, rst_n}), .tx(htx1), .tf(),
        .lo_v(h1v), .lo_r(h1r), .lo_d(h1d), .li_v(hi1v), .li_r(1'b1), .li_d(hi1d), .flt(hf1));
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(ast0), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(ph0), .pma_rck(th0));
    ot_pdie_ucie #(.PMA_LAT(2)) uh0 (.clk(clk), .rst(rst_n), .tx(htx0), .rx(hrx0), .st(hst0), .pma_tx(ph0), .pma_tck(th0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(6)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(ast1), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(ph1), .pma_rck(th1));
    ot_pdie_ucie #(.PMA_LAT(6)) uh1 (.clk(clk), .rst(rst_n), .tx(htx1), .rx(hrx1), .st(hst1), .pma_tx(ph1), .pma_tck(th1), .pma_rx(pa1), .pma_rck(ta1));

    function automatic [1103:0] rnd(input integer dummy);
        integer i; reg [1103:0] b;
        begin for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom; rnd = b; end
    endfunction
    // ---------------- H -> A: frames to send (1104 b), and what A must deliver
    reg [1103:0] hs [0:2047]; integer hn = 0, hp0 = 0, hp1 = 0;
    reg [1103:0] er [0:2047]; integer ern = 0, erk = 0;      // ring beats A.ri must show
    reg [513:0]  eh [0:511];  integer ehn = 0, ehk = 0;      // HOST payloads A.f_host must show
    reg [52:0]   ek [0:511];  integer ekn = 0, ekk = 0;      // KS words A.f_ks must show
    // ---------------- A -> H: what H must receive (frames, 1104 b)
    // per class (the lep may send a host-plane frame after ring beats presented later: order is kept per class)
    reg [1103:0] ea [0:4095]; integer ean = 0; reg [1103:0] eth [0:1023]; integer ethn = 0, ethk = 0;
    reg [1103:0] etk [0:1023]; integer etkn = 0, etkk = 0; integer eak = 0;
    reg [1103:0] fx;
    reg [552:0] r0 [0:4095]; reg [552:0] r1 [0:4095]; integer rn0 = 0, rn1 = 0, rk = 0;
    integer bad = 0, cyc = 0, k, lf_bad = 0, nh = 0, nk = 0, nr = 0;
    function automatic [1103:0] hfrm(input [2:0] ty, input [513:0] pay);
        begin hfrm = 1104'd0; hfrm[3:1] = ty; hfrm[4 +: 514] = pay; end
    endfunction
    // H transmit (flit parity = frame index parity on both lanes)
    always @(negedge clk) begin
        h0v <= hp0 < hn; h0d <= {hp0[0], hs[hp0][551:0]};
        h1v <= hp1 < hn; h1d <= {hp1[0], hs[hp1][1103:552]};
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (h0v && h0r) hp0 = hp0 + 1;
        if (h1v && h1r) hp1 = hp1 + 1;
        // A delivers
        if (a_ri[0]) begin
            if (erk >= ern || a_ri !== er[erk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH ring H->A %0d", erk); end
            erk = erk + 1;
        end
        if (f_host[0]) begin
            if (ehk >= ehn || f_host[514:1] !== eh[ehk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH f_host %0d", ehk); end
            ehk = ehk + 1;
        end
        if (f_ks[52]) begin
            if (ekk >= ekn || f_ks !== ek[ekk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH f_ks %0d got %h exp %h", ekk, f_ks, ek[ekk]); end
            ekk = ekk + 1;
        end
        // H receives
        if (hi0v) begin r0[rn0] = hi0d; rn0 = rn0 + 1; end
        if (hi1v) begin r1[rn1] = hi1d; rn1 = rn1 + 1; end
        while (rk < rn0 && rk < rn1) begin
            fx = {r1[rk][551:0], r0[rk][551:0]};
            if (r0[rk][552] !== r1[rk][552]) begin bad = bad + 1; $display("MISMATCH A->H parity %0d", rk); end
            if (fx[0]) begin
                if (eak >= ean || fx !== ea[eak]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H ring %0d", eak); end
                eak = eak + 1; nr = nr + 1;
            end else if (fx[3:1] == 3'd3) begin
                if (ethk >= ethn || fx !== eth[ethk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H THOST %0d got %h exp %h", ethk, fx[80:4], eth[ethk][80:4]); end
                ethk = ethk + 1; nh = nh + 1;
            end else if (fx[3:1] == 3'd4) begin
                if (etkk >= etkn || fx !== etk[etkk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H TKD %0d", etkk); end
                etkk = etkk + 1; nk = nk + 1;
            end else begin bad = bad + 1; $display("MISMATCH A->H unknown frame type %0d", fx[3:1]); end
            rk = rk + 1;
        end
    end
    // ---------------- stimulus
    reg [1103:0] b; reg [11:0] stat; reg [513:0] hp; reg [52:0] kw; reg [63:0] td; integer gap_h, gap_k;
    function automatic [1103:0] tframe(input [2:0] ty, input [76:0] w);
        begin tframe = 1104'd0; tframe[3:1] = ty; tframe[4 +: 77] = w; end
    endfunction
    initial begin
        void'($urandom(SEED));
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        if (f_lf !== 4'b0101) lf_bad = lf_bad + 1;
        // H -> A frame list: ring beats, HOST and KS frames interleaved
        for (k = 0; k < N; k = k + 1) begin
            case ($urandom % 4)
                0: begin hp = rnd(0); hs[hn] = hfrm(3'd1, hp); hn = hn + 1; eh[ehn] = hp; ehn = ehn + 1; end
                1: begin kw = rnd(0); kw[52] = 1'b1; hs[hn] = hfrm(3'd2, {461'd0, kw}); hn = hn + 1; ek[ekn] = kw; ekn = ekn + 1; end
                default: begin b = rnd(0); b[0] = 1'b1; hs[hn] = b; hn = hn + 1; er[ern] = b; ern = ern + 1; end
            endcase
        end
        // A -> H: ring beats at 0.4, t_v events every >= 16 cycles, status change every 97 cycles, done every 23
        stat = 12'h801; gap_h = 0; gap_k = 0;
        @(negedge clk); t_host = {stat, 1'b0, 64'd0};
        @(posedge clk); @(posedge clk); @(posedge clk);
        eth[ethn] = tframe(3'd3, {stat, 1'b0, 64'd0}); ethn = ethn + 1;            // the first status word
        for (k = 0; k < 3 * N; k = k + 1) begin
            @(negedge clk);
            a_ro = 0; t_host[64] = 1'b0; t_kd = 54'd0; gap_h = gap_h + 1; gap_k = gap_k + 1;
            if (($urandom % 100) < 40) begin b = rnd(0); b[0] = 1'b1; a_ro = b; ea[ean] = b; ean = ean + 1; end
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
        // merge case: 12 back-to-back ring beats; t_v at beat 2, status change at beat 4 -> one THOST {new status, t_v, t_d}
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
        $display("LEPH_STATS H->A ring %0d/%0d host %0d/%0d ks %0d/%0d | A->H frames %0d/%0d (ring %0d thost %0d tkd %0d) | mismatches %0d f_lf %b bad %0d fault %0d",
            erk, ern, ehk, ehn, ekk, ekn, rk, ean + ethn + etkn, nr, nh, nk, bad, f_lf, lf_bad, a_f);
        if (bad == 0 && erk == ern && ehk == ehn && ekk == ekn && eak == ean && ethk == ethn && etkk == etkn && lf_bad == 0 && !a_f)
            $display("PASS lep_host: H->A %0d ring + %0d HOST + %0d KS, A->H %0d frames (%0d THOST incl. 1 merge, %0d TKD) bit-exact in order; f_lf live",
                ern, ehn, ekn, rk, nh, nk);
        else $display("FAIL lep_host: mismatches %0d", bad);
        $finish;
    end
    initial begin #(0.8333 * (WAIT + 60 * N + 30000)); $display("FAIL lep_host: TIMEOUT"); $finish; end
endmodule
