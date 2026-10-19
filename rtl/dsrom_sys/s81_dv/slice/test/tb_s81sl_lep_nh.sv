`timescale 1ns/1ps
// S81-LEPV (2026-10-18): NO-HOST bench of the end-slice link port.  Die A = ot_s81sl_lep_nh (HOST_EN 0: the leaf of the
// three host-less endpoints s_0S / s_0N / s_7S, no host ports) + 2 x dsfd_coll_lane_w + 2 x ot_pdie_ucie.  Peer H =
// 2 x dsfd_coll_lane_e + 2 x ot_pdie_ucie + a behavioural frame codec on the lanes' core faces (as tb_s81sl_lep_host).
//   phase 1, both directions at once: H -> A ring beats (bit 0 = 1) must leave A's ri bit-exact in order; A -> H ring
//            beats on A's ro must arrive bit-exact in order, and A must send NO host-plane frame (THOST / TKD); A.fault 0.
//   phase 2: H sends one HOST frame, then (after a reset) one KS frame: a HOST_EN 0 endpoint has no host plane, so each
//            must raise A's sticky fault (an unknown frame type) and must not appear on ri.
// Verdict: "PASS lep_nh ..." or "FAIL lep_nh ...".
module tb_s81sl_lep_nh #(parameter integer N = 400, parameter integer SEED = 5, parameter integer WAIT = 8000);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_ro = 0; wire [1103:0] a_ri; wire a_f;
    wire a0v, a0r, a1v, a1r, ai0v, ai0r, ai1v, ai1r; wire [552:0] a0d, a1d, ai0d, ai1d; wire [2:0] af0, af1; wire [1:0] arxv;
    wire h0r, h1r, hi0v, hi1v; wire [552:0] hi0d, hi1d; wire [2:0] hf0, hf1;
    reg h0v = 0, h1v = 0; reg [552:0] h0d = 0, h1d = 0;
    wire [511:0] atx0, atx1, htx0, htx1, arx0, arx1, hrx0, hrx1; wire [1:0] ast0, ast1, hst0, hst1;
    wire [512:0] pa0, pa1, ph0, ph1; wire ta0, ta1, th0, th1;
    ot_s81sl_lep_nh la (.clk(clk), .rst_n(rst_n), .ro(a_ro), .ri(a_ri),
        .lo0_v(a0v), .lo0_r(a0r), .lo0_d(a0d), .lo1_v(a1v), .lo1_r(a1r), .lo1_d(a1d),
        .li0_v(ai0v), .li0_r(ai0r), .li0_d(ai0d), .li1_v(ai1v), .li1_r(ai1r), .li1_d(ai1d), .rxv(arxv),
        .sl_f(1'b0), .l0_f(af0), .l1_f(af1), .fault(a_f));
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
    reg [1103:0] hs [0:2047]; integer hn = 0, hp0 = 0, hp1 = 0;     // H -> A frames
    reg [1103:0] er [0:2047]; integer ern = 0, erk = 0;            // ring beats A.ri must show
    reg [1103:0] ea [0:4095]; integer ean = 0, eak = 0;            // A -> H ring beats
    reg [1103:0] fx;
    reg [552:0] r0 [0:4095]; reg [552:0] r1 [0:4095]; integer rn0 = 0, rn1 = 0, rk = 0;
    integer bad = 0, nhf = 0, k, cyc = 0;
    always @(negedge clk) begin
        h0v <= hp0 < hn; h0d <= {hp0[0], hs[hp0][551:0]};
        h1v <= hp1 < hn; h1d <= {hp1[0], hs[hp1][1103:552]};
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (h0v && h0r) hp0 = hp0 + 1;
        if (h1v && h1r) hp1 = hp1 + 1;
        if (a_ri[0]) begin
            if (erk >= ern || a_ri !== er[erk]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH ring H->A %0d", erk); end
            erk = erk + 1;
        end
        if (hi0v) begin r0[rn0] = hi0d; rn0 = rn0 + 1; end
        if (hi1v) begin r1[rn1] = hi1d; rn1 = rn1 + 1; end
        while (rk < rn0 && rk < rn1) begin
            fx = {r1[rk][551:0], r0[rk][551:0]};
            if (r0[rk][552] !== r1[rk][552]) begin bad = bad + 1; $display("MISMATCH A->H parity %0d", rk); end
            if (fx[0]) begin
                if (eak >= ean || fx !== ea[eak]) begin bad = bad + 1; if (bad < 8) $display("MISMATCH A->H ring %0d", eak); end
                eak = eak + 1;
            end else begin nhf = nhf + 1; bad = bad + 1; $display("MISMATCH A->H host-plane frame type %0d from a HOST_EN 0 endpoint", fx[3:1]); end
            rk = rk + 1;
        end
    end
    reg [1103:0] b; integer f1, f_host_frame, f_ks_frame, ri_leak;
    task automatic send_frame(input [2:0] ty);
        begin b = rnd(0); b[0] = 1'b0; b[3:1] = ty; hs[hn] = b; hn = hn + 1; end
    endtask
    initial begin
        void'($urandom(SEED));
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        for (k = 0; k < N; k = k + 1) begin b = rnd(0); b[0] = 1'b1; hs[hn] = b; hn = hn + 1; er[ern] = b; ern = ern + 1; end
        for (k = 0; k < 3 * N; k = k + 1) begin
            @(negedge clk);
            a_ro = 0;
            if (($urandom % 100) < 40) begin b = rnd(0); b[0] = 1'b1; a_ro = b; ea[ean] = b; ean = ean + 1; end
        end
        @(negedge clk); a_ro = 0;
        repeat (4000) @(posedge clk);
        f1 = a_f;
        // phase 2a: one HOST frame
        ri_leak = erk;
        send_frame(3'd1);
        repeat (2000) @(posedge clk);
        f_host_frame = a_f;
        // phase 2b: reset both ends, one KS frame (start bit set)
        @(negedge clk); rst_n = 0; hn = 0; hp0 = 0; hp1 = 0; rn0 = 0; rn1 = 0; rk = 0;
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        b = rnd(0); b[0] = 1'b0; b[3:1] = 3'd2; b[4 + 52] = 1'b1; hs[hn] = b; hn = hn + 1;
        repeat (2000) @(posedge clk);
        f_ks_frame = a_f;
        if (erk != ri_leak) bad = bad + 1;
        $display("LEPNH_STATS H->A ring %0d/%0d | A->H ring %0d/%0d host-plane frames %0d | mismatches %0d fault ring %0d HOST %0d KS %0d",
            erk, ern, eak, ean, nhf, bad, f1, f_host_frame, f_ks_frame);
        if (bad == 0 && erk == ern && eak == ean && nhf == 0 && !f1 && f_host_frame && f_ks_frame)
            $display("PASS lep_nh: H->A %0d + A->H %0d ring beats bit-exact in order, no host-plane frame sent; HOST and KS frames into the HOST_EN 0 endpoint flagged (fault), not delivered",
                ern, ean);
        else $display("FAIL lep_nh: mismatches %0d fault ring %0d HOST %0d KS %0d", bad, f1, f_host_frame, f_ks_frame);
        $finish;
    end
    initial begin #(0.8333 * (3 * WAIT + 60 * N + 30000)); $display("FAIL lep_nh: TIMEOUT"); $finish; end
endmodule
