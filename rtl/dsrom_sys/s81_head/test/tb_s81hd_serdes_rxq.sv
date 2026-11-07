`timescale 1ns/1ps
// DIE-HEAD-66 2026-11-05: bench of hd_serdes form RXQ (ot_s81hd_serdes_rxq.sv) against the shared RX.
// (1) am_ok: all 4096 AM patterns, gold u_syn.am_ok == RXQ u_syn.am_ok on the same edge.
// (2) Decoder lockstep, same clock, enc frames with random errors (0, 1 bit a word, heavy frames past t = 15, AM hits):
//     every RXQ output equals gold delayed by exactly 2 edges; lock equal on the same edge.  Non-vacuous: counts corrected
//     and uncorrectable frames.
// (3) Link, equal clocks: rx of ot_s81hd_pdie_q == ot_pdie_serdes delayed 3 edges (2 decoder + 1 read stage); pma_tx equal, no delay; status equal at the end.
// (4) Link, plesiochronous both ways: non-IDLE beat order at B equal to what A sent, fault 0.
module tb_s81hd_serdes_rxq;
    parameter integer NCYC = 12000, NB = 8000;
    reg c = 0; always #0.41667 c = ~c;
    reg rst = 0;
    // ---------------------------------------- (2) decoder
    reg  [511:0] tx = 512'd2; wire e_v; wire [543:0] e_d; wire e_f;
    ot_s81_kp4_enc u_enc (.clk(c), .rst_n(rst), .tx_v(rst), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_f));
    reg  [543:0] err = 0; reg am_sw = 0; reg [11:0] am_v = 0;
    wire [543:0] pd = am_sw ? {am_v, 532'd0} : (e_d ^ err);
    wire pv = am_sw ? 1'b1 : (e_v & rst);
    wire gv, gf, gu, gl; wire [511:0] gd; wire [4:0] gn; wire [7:0] gs; wire [31:0] gc, gun, gr;
    wire qv, qf, qu, ql; wire [511:0] qd; wire [4:0] qn; wire [7:0] qs; wire [31:0] qc, qun, qr;
    ot_s81_kp4_dec     g (.clk(c), .rst_n(rst), .p_v(pv), .p_d(pd), .q_v(gv), .q_d(gd), .q_first(gf), .q_unc(gu), .q_nerr(gn), .q_seq(gs), .lock(gl), .n_corr(gc), .n_unc(gun), .n_relock(gr));
    ot_s81hd_kp4_dec_q q (.clk(c), .rst_n(rst), .p_v(pv), .p_d(pd), .q_v(qv), .q_d(qd), .q_first(qf), .q_unc(qu), .q_nerr(qn), .q_seq(qs), .lock(ql), .n_corr(qc), .n_unc(qun), .n_relock(qr));
    reg [622:0] gh [0:2];  // gold outputs history
    wire [622:0] gnow = {gv, gf, gu, gn, gs, gc[31:0], gun[31:0], gd};
    wire [622:0] qnow = {qv, qf, qu, qn, qs, qc[31:0], qun[31:0], qd};
    // ---------------------------------------- (3) link equal clocks, (4) plesiochronous
    reg  [511:0] txl = 512'd2;
    reg  [511:0] grbh [0:2];
    wire [511:0] grx, qrx, grb, qrb; wire [1:0] gst, qst, gsb, qsb; wire [543:0] gpa, qpa, gpb, qpb; wire gta, qta, gtb, qtb;
    ot_pdie_serdes  g_a (.clk(c), .rst(rst), .tx(txl), .rx(grx), .st(gst), .pma_tx(gpa), .pma_tck(gta), .pma_rx(gpb), .pma_rck(gtb));
    ot_pdie_serdes  g_b (.clk(c), .rst(rst), .tx(512'd2), .rx(grb), .st(gsb), .pma_tx(gpb), .pma_tck(gtb), .pma_rx(gpa), .pma_rck(gta));
    ot_s81hd_pdie_q q_a (.clk(c), .rst(rst), .tx(txl), .rx(qrx), .st(qst), .pma_tx(qpa), .pma_tck(qta), .pma_rx(qpb), .pma_rck(qtb));
    ot_s81hd_pdie_q q_b (.clk(c), .rst(rst), .tx(512'd2), .rx(qrb), .st(qsb), .pma_tx(qpb), .pma_tck(qtb), .pma_rx(qpa), .pma_rck(qta));
    reg [511:0] grh [0:3];
    reg cb = 0; always #0.41679 cb = ~cb;
    wire [511:0] prb; wire [1:0] psa, psb; wire [543:0] ppa, ppb; wire pta, ptb; wire [511:0] prx;
    ot_s81hd_pdie_q p_a (.clk(c),  .rst(rst), .tx(txl), .rx(prx), .st(psa), .pma_tx(ppa), .pma_tck(pta), .pma_rx(ppb), .pma_rck(ptb));
    ot_s81hd_pdie_q p_b (.clk(cb), .rst(rst), .tx(512'd2), .rx(prb), .st(psb), .pma_tx(ppb), .pma_tck(ptb), .pma_rx(ppa), .pma_rck(pta));
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ ({64'h0, {448{n[0]}}} & ~512'h3);
    endfunction
    integer cyc = 0, i, bad_am = 0, bad_dec = 0, bad_lk = 0, bad_lock = 0, bad_tx = 0, sent = 0, frames = 0, corr_f = 0, unc_f = 0;
    integer gotb = 0, bad_order = 0, prst = 0, fi = 0; integer first_dec = -1, first_lk = -1;
    reg started = 0;
    function automatic is_idle(input [511:0] x); is_idle = x[1] && !x[0]; endfunction
    reg [511:0] want;
    initial begin
        // (1) all AM patterns; p_v high, reset released so am_ok runs
        rst = 0; repeat (4) @(negedge c); am_sw = 1;
        for (i = 0; i < 4096; i = i + 1) begin
            am_v = i[11:0] ^ 12'hA5C; @(negedge c); @(posedge c); #0.1;
            if (g.u_syn.am_ok !== q.u_syn.am_ok) bad_am = bad_am + 1;
        end
        am_sw = 0; rst = 0; repeat (8) @(negedge c);
        rst = 1; started = 1;
    end
    always @(negedge c) if (started) begin
        cyc = cyc + 1;
        if (cyc > 40 && sent < NB) begin
            if (cyc % 256 == 0) begin tx <= 512'd2; txl <= 512'd2; end
            else begin tx <= beat(sent); txl <= beat(sent); sent = sent + 1; end
        end else begin tx <= 512'd2; txl <= 512'd2; end
        // errors: frame modes change every 10 words: clean, 1 bit a word, heavy
        if (cyc % 10 == 0) fi = $urandom % 8;
        if (fi == 0) err <= 0;
        else if (fi <= 5) err <= ($urandom % 2) ? (544'd1 << ($urandom % 532)) : 544'd0;
        else if (fi == 6) err <= (544'd1 << ($urandom % 532)) ^ (544'd1 << ($urandom % 532)) ^ (544'd1 << ($urandom % 532)) ^ (544'd1 << ($urandom % 532));
        else err <= ($urandom % 16 == 0) ? (544'd1 << (532 + $urandom % 12)) : 544'd0;
        if (gv && gf) begin frames = frames + 1; if (gu) unc_f = unc_f + 1; else if (gn != 0) corr_f = corr_f + 1; end
        if (cyc > 3) begin
            if (qnow !== gh[1]) begin if (!(^gh[1] === 1'bx)) begin bad_dec = bad_dec + 1; if (first_dec < 0) first_dec = cyc; end end
            if (ql !== gl) bad_lock = bad_lock + 1;
            if (qrx !== grh[2]) begin if (!(^grh[2] === 1'bx)) begin bad_lk = bad_lk + 1; if (first_lk < 0) first_lk = cyc; end end
            if (qrb !== grbh[2]) begin if (!(^grbh[2] === 1'bx)) begin bad_lk = bad_lk + 1; if (first_lk < 0) first_lk = cyc; end end  // the side that carries the beats
            if (qpa !== gpa) bad_tx = bad_tx + 1;
        end
        gh[1] <= gh[0]; gh[0] <= gnow;
        grh[2] <= grh[1]; grh[1] <= grh[0]; grh[0] <= grx;
        grbh[2] <= grbh[1]; grbh[1] <= grbh[0]; grbh[0] <= grb;
        if (cyc == NCYC) begin
            $display("RXQ_STATS cycles=%0d am_bad=%0d dec_bad=%0d first=%0d lock_bad=%0d link_bad=%0d first=%0d tx_bad=%0d frames=%0d corrected=%0d unc=%0d beats_B=%0d order_bad=%0d st_p=%b/%b",
                cyc, bad_am, bad_dec, first_dec, bad_lock, bad_lk, first_lk, bad_tx, frames, corr_f, unc_f, gotb, bad_order, psa, psb);
            if (bad_am + bad_dec + bad_lock + bad_lk + bad_tx + bad_order != 0) $display("SERDES_RXQ FAIL mismatch");
            else if (qst !== gst) $display("SERDES_RXQ FAIL status at end %b vs %b", qst, gst);
            else if (frames < 300 || corr_f < 50 || unc_f < 5) $display("SERDES_RXQ FAIL vacuous decoder");
            else if (gotb < NB - 400) $display("SERDES_RXQ FAIL vacuous link: %0d beats", gotb);
            else if (p_a.u_rm.fault !== 1'b0 || p_b.u_rm.fault !== 1'b0) $display("SERDES_RXQ FAIL rate match fault");
            else $display("SERDES_RXQ PASS");
            $finish;
        end
    end
    // (4) B side of the plesiochronous pair: non-IDLE beats in the order sent, no gap inside what A sent
    integer nxt = 0;
    always @(negedge cb) if (started) begin
        if (!is_idle(prb) && prb !== 512'd0 && !(^prb === 1'bx)) begin
            want = beat(nxt);
            if (prb !== want) begin bad_order = bad_order + 1; end
            nxt = nxt + 1; gotb = gotb + 1;
        end
    end
endmodule
