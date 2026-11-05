`timescale 1ns/1ps
// HBM-REFORM-B d44v part 20: lockstep of the ot_pdie_serdes split against the gold, each under a face shell model.
// Source link P -> errors -> both worlds.
// MODE 0, one clock, the form the HBM kit builds (one core clock, face_shell.apply).  Checked every edge after reset:
//   pma_tx exact; st[1] exact; rx = gold delayed 2 edges; st[0] rises exactly 2 edges after gold.
// MODE 1 / 2, two plesiochronous clocks (COORD 23:2x: the CDC stays proved in simulation), recovered clock slower / faster.
//   The face model here clocks the recovered-domain pins on rck (fsp shells), which is NOT what the one-clock kit shell
//   builds.  Checked: pma_tx exact; st[1] exact; non-IDLE rx beats equal in order; st[0] rises within 6 edges after gold.
module tb_pdie_p20;
    parameter integer SMUT = 0, NCYC = 9000, FT = 1, FE = 7600, MODE = 0;
    reg c = 0, rc2 = 0, rst = 0;
    always #0.41667 c = ~c;
    always #((MODE == 2) ? 0.41655 : 0.41679) rc2 = ~rc2;
    wire rc = (MODE == 0) ? c : rc2;
    reg [511:0] txa = 512'd2, txp = 512'd2;
    wire [543:0] p_tx, g_tx, s_tx; wire p_ck, g_ck, s_ck;
    wire [511:0] g_rx, s_rx, p_rx; wire [1:0] g_st, s_st, p_st;
    reg [543:0] err = 0;
    wire [543:0] line = p_tx ^ err;
    ot_pdie_serdes u_p (.clk(rc), .rst(rst), .tx(txp), .rx(p_rx), .st(p_st), .pma_tx(p_tx), .pma_tck(p_ck), .pma_rx(544'd0), .pma_rck(rc));
    ot_pdie_serdes__fs u_g (.clk(c), .rst(rst), .tx(txa), .rx(g_rx), .st(g_st), .pma_tx(g_tx), .pma_tck(g_ck), .pma_rx(line), .pma_rck(rc));
    ot_pdie_serdes__p20fs #(.SMUT(SMUT)) u_s (.clk(c), .rst(rst), .tx(txa), .rx(s_rx), .st(s_st), .pma_tx(s_tx), .pma_tck(s_ck), .pma_rx(line), .pma_rck(rc));
    function automatic [511:0] beat(input integer n, input integer salt);
        beat = {32'(n), 32'(n * 7 + salt), 32'(n ^ 32'h5A5A), 384'h0, 30'(n + salt), 2'b00} ^ ({64'h0, {448{n[0]}}} & ~512'h3);
    endfunction
    integer cyc = 0, rcyc = 0, mm_tx = 0, mm_rx = 0, mm_lk = 0, first = -1, sent = 0, beats = 0, gf = -1, sf = -1;
    integer gn = 0, sn = 0;
    reg [511:0] gq [0:32767];
    reg [511:0] g1 = 0, g2 = 0;
    always @(negedge rc) begin
        rcyc = rcyc + 1;
        if (rcyc > 40 && rcyc % 256 != 0) begin txp <= beat(sent, 3); sent = sent + 1; end
        else txp <= 512'd2;
        // single-bit errors in about half the words, a heavy burst when FT = 1
        err <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0;
        if (FT == 1 && rcyc >= FE && rcyc < FE + 12) err <= {17{32'hA5C3_0F96}};
    end
    wire g_idle = g_rx[1] && !g_rx[0], s_idle = s_rx[1] && !s_rx[0];
    always @(negedge c) begin
        cyc = cyc + 1;
        txa <= (cyc > 40 && cyc % 256 != 0) ? beat(cyc, 11) : 512'd2;
        if (FT == 2 && cyc == FE) begin force u_g.u_fcore.u_enc.flt = 1'b1; force u_s.u_tx.u_fcore.u_enc.flt = 1'b1; end
        if (rst && cyc > 40) begin
            if (s_tx !== g_tx) begin mm_tx = mm_tx + 1; if (first < 0) first = cyc; end
            if (s_st[1] !== g_st[1]) begin mm_lk = mm_lk + 1; if (first < 0) first = cyc; end
            if (MODE == 0 && cyc > 60 && s_rx !== g2) begin mm_rx = mm_rx + 1; if (first < 0) first = cyc; end
            if (gf < 0 && g_st[0] === 1'b1) gf = cyc;
            if (sf < 0 && s_st[0] === 1'b1) sf = cyc;
            if (g_st[1] === 1'b1 && !g_idle) begin gq[gn] = g_rx; gn = gn + 1; end
            if (s_st[1] === 1'b1 && !s_idle) begin
                if (sn < gn && s_rx !== gq[sn]) begin mm_rx = mm_rx + 1; if (first < 0) first = cyc; end
                if (sn >= gn && MODE == 0) begin mm_rx = mm_rx + 1; if (first < 0) first = cyc; end
                sn = sn + 1;
            end
        end
        g2 = g1; g1 = g_rx;
        if (cyc == NCYC) begin
            $display("P20_STATS smut=%0d ft=%0d mode=%0d cycles=%0d mm_tx=%0d mm_rx=%0d mm_lock=%0d first=%0d beats gold=%0d split=%0d fault gold=%0d split=%0d live=%b/%b",
                SMUT, FT, MODE, cyc, mm_tx, mm_rx, mm_lk, first, gn, sn, gf, sf, g_st[1], s_st[1]);
            if (mm_tx + mm_rx + mm_lk != 0) $display("P20_EQ FAIL lockstep mismatch, first at %0d", first);
            else if (gn < 4000) $display("P20_EQ FAIL vacuous: %0d beats", gn);
            else if (gn - sn > 8 || sn > gn) $display("P20_EQ FAIL beat count gold %0d split %0d", gn, sn);
            else if (gf < 0 || (MODE == 0 ? (sf != gf + 2) : (sf < gf || sf > gf + 6))) $display("P20_EQ FAIL fault edge gold %0d split %0d", gf, sf);
            else $display("P20_EQ PASS split == gold for %0d edges, %0d beats, mode %0d, fault gold %0d split %0d", cyc, gn, MODE, gf, sf);
            $finish;
        end
    end
    initial begin repeat (8) @(posedge c); rst = 1; end
endmodule
