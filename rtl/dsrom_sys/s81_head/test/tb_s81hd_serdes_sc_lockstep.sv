`timescale 1ns/1ps
// DIE-HEAD-76-SERDESRF 2026-11-06: lockstep of the hd_serdes SC form (ot_s81hd_pdie_sc: hard children u_tx, u_bm0..2,
// u_chn) against the RXQ form (ot_s81hd_pdie_q).  One peer B = ot_s81hd_serdes_link (unchanged main form) on a
// plesiochronous clock; B sends NB beats (IDLE every 256), A_r (RXQ) sends NB beats to B.  A_r and A_s get the SAME
// pma_rx / pma_rck (B's stream with one random bit error in about every second PMA word) and the same coll_i0.
// Checked on every A edge: A_s {st, rx} == A_r {st, rx}; A_s.pma_tx == A_r.pma_tx delayed by exactly 2 ck edges
// (encoder LA 2 + FF 1).  At FE the encoder fault is forced in both: st[0] must rise on the same edge (e_flt unchanged).
// Non-vacuous: B decodes >= NB - 400 of A_r's beats and A_r decodes >= NB - 400 of B's beats.
module tb_s81hd_serdes_sc_lockstep;
    parameter integer NB = 6000, FE = 7600, NCYC = 8000;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    reg  [511:0] txa = 512'd2, txb = 512'd2;
    wire [511:0] r_rx, s_rx; wire [1:0] r_st, s_st;
    wire [543:0] r_pa, s_pa, pb; wire r_ta, s_ta, tb_;
    wire [513:0] ob;
    reg  [543:0] e_ab, e_ba;
    ot_s81hd_pdie_q  a_r (.clk(ca), .rst(rst), .tx(txa), .rx(r_rx), .st(r_st), .pma_tx(r_pa), .pma_tck(r_ta), .pma_rx(pb ^ e_ba), .pma_rck(tb_));
    ot_s81hd_pdie_sc a_s (.clk(ca), .rst(rst), .tx(txa), .rx(s_rx), .st(s_st), .pma_tx(s_pa), .pma_tck(s_ta), .pma_rx(pb ^ e_ba), .pma_rck(tb_));
    ot_s81hd_serdes_link b (.ck(cb), .rst_n(rst), .coll_i0(txb), .coll_o0(ob), .pma_tx(pb), .pma_tck(tb_), .pma_rx(r_pa ^ e_ab), .pma_rck(r_ta));
    always @(posedge ca) begin e_ab <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0; end
    always @(posedge cb) begin e_ba <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0; end
    initial begin e_ab = 0; e_ba = 0; end
    reg [543:0] r_pa1 = 0, r_pa2 = 0;
    always @(posedge ca) begin r_pa1 <= r_pa; r_pa2 <= r_pa1; end
    integer sent = 0, sentb = 0, cyc = 0, cycb = 0, mrx = 0, mtx = 0, first = -1, rf = -1, sf = -1, gotb = 0, gota = 0;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    function automatic [511:0] beatb(input integer n);
        beatb = {32'(n * 13 + 1), 32'(n ^ 32'h3C3C), 416'h0, 30'(n), 2'b00} ^ {96'h0, {416{n[1]}}} & ~512'h3;
    endfunction
    always @(negedge ca) begin
        cyc = cyc + 1;
        if (cyc > 40 && sent < NB) begin
            if (cyc % 256 == 0) txa <= 512'd2;
            else begin txa <= beat(sent); sent = sent + 1; end
        end else txa <= 512'd2;
        if (cyc == FE) begin force a_r.u_enc.flt = 1'b1; force a_s.u_tx.u_enc.flt = 1'b1; end
        if (s_rx !== r_rx || s_st !== r_st) begin mrx = mrx + 1; if (first < 0) first = cyc; end
        if (cyc > 2 && s_pa !== r_pa2) begin mtx = mtx + 1; if (first < 0) first = cyc; end
        if (rf < 0 && r_st[0]) rf = cyc;
        if (sf < 0 && s_st[0]) sf = cyc;
        if (!(r_rx[1] && !r_rx[0]) && r_rx === beatb(gota)) gota = gota + 1;
        if (cyc == NCYC) begin
            $display("SC_STATS cycles=%0d mismatch_rx=%0d mismatch_tx=%0d first=%0d B_got=%0d A_got=%0d fault_edge R=%0d S=%0d live=%b/%b",
                cyc, mrx, mtx, first, gotb, gota, rf, sf, r_st[1], s_st[1]);
            if (mrx + mtx != 0) $display("SERDES_SC FAIL lockstep mismatch (first at A edge %0d)", first);
            else if (gotb < NB - 400 || gota < NB - 400) $display("SERDES_SC FAIL vacuous: B got %0d, A got %0d beats", gotb, gota);
            else if (rf < 0 || sf != rf) $display("SERDES_SC FAIL fault edge R %0d S %0d (want equal)", rf, sf);
            else $display("SERDES_SC PASS SC == RXQ for %0d A edges (rx/st exact, pma_tx +2 ck edges, %0d + %0d beats over FEC)", cyc, gotb, gota);
            $finish;
        end
    end
    always @(negedge cb) begin
        cycb = cycb + 1;
        if (cycb > 40 && sentb < NB) begin
            if (cycb % 256 == 0) txb <= 512'd2;
            else begin txb <= beatb(sentb); sentb = sentb + 1; end
        end else txb <= 512'd2;
        if (rst && !(ob[1] && !ob[0]) && ob[511:0] === beat(gotb)) gotb = gotb + 1;
    end
    initial begin repeat (8) @(posedge ca); rst = 1; end
endmodule
