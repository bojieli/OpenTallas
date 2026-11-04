`timescale 1ns/1ps
// DIE-S81-51/RF-H 11-03: ot_v41_bf_col (g48 parameters, BRNECUT 0) vs ot_v41_bf_col3 (3 hard cores, BRNECUT 1) on the
// same pins.  Scoreboard: the sequence of partials {pval, prow, pseg, pnseg, perr, ppos} on pv must be identical (latency
// may differ; free=0 gates the clock legally: closed only GATE_DRAIN=150 cycles after the last word); with ze_d = 1 (+free=1) every partial must also be exactly D cycles later (D = 3: 2 face + 1 RNE cut).
// qy_bkf: same final value and same number of rising edges.  Random ROM via maps (+OT_ROM_DIR, INSTANCE "tb").
module tb;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed, NC, burst = 0, idle = 0, ph = 0, cyc, k, errs = 0, n0 = 0, n1 = 0, nbf = 0, nfp = 0, free, kr0 = 0, kr1 = 0, nex = 0;
    reg ze_d, issue, i1_v, i1_bk, i1_bf; reg [13:0] a_ctr; reg [16:0] i1_t;
    reg [255:0] q0, q1; reg [9:0] e0, e1; reg [127:0] so_row; reg [39:0] so_idx, so_n;
    wire pv0, pv1, pe0, pe1, bk0, bk1; wire [31:0] pval0, pval1; wire [15:0] pr0, pr1; wire [4:0] ps0, ps1, pn0, pn1; wire [2:0] pp0, pp1;
`define BFP .NSEG(8), .NCH(16), .XF(8), .LV(5), .BF16(1), .NCHB(8), .NB(2), .MTP(1), .EARLY(1), .CG(1), .DRAIN(200), .FAST(1), .PP(1), .BP(0), \
    .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8), .QZ_NE(4), .QY(1), .QX(10), .QBF(2), \
    .QZE(1), .TCG(1), .GRADUAL_RNE(1), .BXST(2), .FXST(2), .RCG(1), .KEEP_XPOS(1), .INSTANCE("tb")
`define BFC (.clk(clk), .rst_n_pin(rst_n), .ze_d(ze_d), .issue(issue), .a_ctr(a_ctr), .i1_v(i1_v), .i1_bk(i1_bk), .i1_bf(i1_bf), .i1_t(i1_t), \
    .i2x_q0(q0), .i2x_e0(e0), .i2x_q1(q1), .i2x_e1(e1), .so_row(so_row), .so_idx(so_idx), .so_n(so_n)
    ot_v41_bf_col  #(`BFP, .BRNECUT(0)) old `BFC, .pv(pv0), .pval(pval0), .prow(pr0), .pseg(ps0), .pnseg(pn0), .perr(pe0), .ppos(pp0), .qy_bkf(bk0));
    ot_v41_bf_col3 #(`BFP, .BRNECUT(1)) dut `BFC, .pv(pv1), .pval(pval1), .prow(pr1), .pseg(ps1), .pnseg(pn1), .perr(pe1), .ppos(pp1), .qy_bkf(bk1));
    localparam integer D = 3, QN = 1 << 16;
    reg [64:0] q_old [0:QN-1]; integer t_old [0:QN-1];
    reg pb0, pb1;
    function automatic [15:0] bf(input integer dummy);
        reg [15:0] r; begin r = $random(seed); if (r[0]) r[14:7] = 8'd1 + ($unsigned($random(seed)) % 70); else r[14:7] = 8'd100 + ($unsigned($random(seed)) % 50); bf = r; end
    endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", NC)) NC = 100000;
        if (!$value$plusargs("free=%d", free)) free = 1;
        ze_d = 1; issue = 0; i1_v = 0; i1_bk = 0; i1_bf = 0; a_ctr = 0; i1_t = 0; q0 = 0; q1 = 0; e0 = 0; e1 = 0;
        for (k = 0; k < 8; k = k + 1) begin so_row[16*k +: 16] = $random(seed); so_row[16*k + 15] = (k == 5); end
        so_idx = {$random(seed), $random(seed)}; so_n = {$random(seed), $random(seed)};
        pb0 = 0; pb1 = 0;
        repeat (6) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < NC; cyc = cyc + 1) begin
            @(posedge clk); #0.1;
            // scoreboard
            if (pv0) begin q_old[n0 % QN] = {pval0, pr0, ps0, pn0, pe0, pp0, 3'd0}; t_old[n0 % QN] = cyc; n0 = n0 + 1; end
            if (pv1) begin
                if (n1 >= n0) begin errs = errs + 1; if (errs < 6) $display("EXTRA partial cyc %0d", cyc); end
                else begin
                    if (q_old[n1 % QN] !== {pval1, pr1, ps1, pn1, pe1, pp1, 3'd0}) begin errs = errs + 1;
                        if (errs < 6) $display("MISMATCH #%0d cyc %0d %h vs %h", n1, cyc, {pval1, pr1, ps1, pn1, pe1, pp1, 3'd0}, q_old[n1 % QN]); end
                    if (free != 0 && cyc != t_old[n1 % QN] + D) begin nex = nex + 1; if (nex < 4) $display("LATENCY #%0d %0d vs %0d+%0d", n1, cyc, t_old[n1 % QN], D); end
                end
                n1 = n1 + 1;
            end
            if (bk0 && !pb0) kr0 = kr0 + 1; if (bk1 && !pb1) kr1 = kr1 + 1; pb0 = bk0; pb1 = bk1;
            if (old.mi2_v && old.mi2_bf) nbf = nbf + 1; else if (old.mi2_v) nfp = nfp + 1;
            // stimulus: random issues, BF and FP words interleaved at random spacing
            // free=0: legal element gating (ot_v41_rom_elem_qx_w10 QZE: ze_d = go || drain window): words come in bursts,
            // the gate stays open GATE_DRAIN cycles after the last word, then closes for a random gap
            if (ph == 0 && burst == 0) begin burst = 20 + ($unsigned($random(seed)) % 400); ph = 1; end
            if (ph == 1) begin burst = burst - 1; if (burst == 0) begin ph = 2; idle = 0; end end
            else if (ph == 2) begin idle = idle + 1; if (idle > 150 + ($unsigned($random(seed)) % 300)) ph = 0; end
            ze_d = free != 0 ? 1'b1 : (ph == 1 || (ph == 2 && idle <= 150));
            issue = (free != 0 || ph == 1) && (($unsigned($random(seed)) % 3) != 0); a_ctr = $random(seed);
            i1_v = (free != 0 || ph == 1) && (($unsigned($random(seed)) % 3) != 0); i1_bk = $random(seed); i1_bf = $random(seed); i1_t = $random(seed);
            for (k = 0; k < 16; k = k + 1) begin q0[16*k +: 16] = bf(0); q1[16*k +: 16] = bf(0); end
            e0 = $random(seed); e1 = $random(seed);
        end
        repeat (400) begin @(posedge clk); #0.1;
            ze_d = 1; issue = 0; i1_v = 0;
            if (pv0) begin q_old[n0 % QN] = {pval0, pr0, ps0, pn0, pe0, pp0, 3'd0}; t_old[n0 % QN] = cyc; n0 = n0 + 1; end
            if (pv1) begin if (n1 < n0 && q_old[n1 % QN] !== {pval1, pr1, ps1, pn1, pe1, pp1, 3'd0}) errs = errs + 1; n1 = n1 + 1; end
            if (bk0 && !pb0) kr0 = kr0 + 1; if (bk1 && !pb1) kr1 = kr1 + 1; pb0 = bk0; pb1 = bk1; cyc = cyc + 1;
        end
        if (n0 != n1) begin errs = errs + 1; $display("COUNT old %0d new %0d", n0, n1); end
        if (bk0 !== bk1 || kr0 != kr1) begin errs = errs + 1; $display("QY_BKF old %b/%0d new %b/%0d", bk0, kr0, bk1, kr1); end
        if (errs == 0 && nex == 0 && n0 > 0 && nbf > 0 && nfp > 0)
            $display("COL3 PASS cycles=%0d partials=%0d bf_words=%0d fp_words=%0d qy_bkf_rises=%0d free=%0d errors=0", NC, n0, nbf, nfp, kr0, free);
        else $display("COL3 FAIL errors=%0d latency_off=%0d partials=%0d/%0d bf_words=%0d fp_words=%0d", errs, nex, n0, n1, nbf, nfp);
        $finish;
    end
endmodule
