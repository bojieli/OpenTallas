`timescale 1ns/1ps
// DH58-RFRTL 2026-11-03: lockstep of the hd_serdes split (ot_s81hd_serdes_split_ref = serdes_tx + serdes_rx) against
// the unsplit ot_s81hd_serdes_link.  Two worlds, same stimulus (tb_s81_pdie_link traffic: A sends NB beats + IDLE every
// 256 to peer B over plesiochronous clocks, one random bit error in about every second PMA word A -> B and B -> A):
//   R: A = ot_s81hd_serdes_link, B = ot_s81hd_serdes_link;  S: A = split_ref, B = ot_s81hd_serdes_link.
// Checked on every edge: A.pma_tx, A.coll_o0[512:0] (rx + live) and all B outputs equal in both worlds; at FE the
// encoder fault is forced in A of both worlds: S.A fault bit (coll_o0[512]) must rise exactly 2 ck edges after R.A's.
module tb_s81hd_serdes_split_lockstep;
    parameter integer SPLIT_MUT = 0, NB = 6000, FE = 7600, NCYC = 8000;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    reg [511:0] txa = 512'd2;
    wire [513:0] r_oa, r_ob, s_oa, s_ob;
    wire [543:0] r_pa, r_pb, s_pa, s_pb; wire r_ta, r_tb, s_ta, s_tb;
    reg  [543:0] e_ab, e_ba;
    ot_s81hd_serdes_link r_a (.ck(ca), .rst_n(rst), .coll_i0(txa), .coll_o0(r_oa), .pma_tx(r_pa), .pma_tck(r_ta), .pma_rx(r_pb ^ e_ba), .pma_rck(r_tb));
    ot_s81hd_serdes_link r_b (.ck(cb), .rst_n(rst), .coll_i0(512'd2), .coll_o0(r_ob), .pma_tx(r_pb), .pma_tck(r_tb), .pma_rx(r_pa ^ e_ab), .pma_rck(r_ta));
    ot_s81hd_serdes_split_ref #(.SPLIT_MUT(SPLIT_MUT)) s_a (.ck(ca), .rst_n(rst), .coll_i0(txa), .coll_o0(s_oa), .pma_tx(s_pa),
        .pma_tck(s_ta), .pma_rx(s_pb ^ e_ba), .pma_rck(s_tb));
    ot_s81hd_serdes_link s_b (.ck(cb), .rst_n(rst), .coll_i0(512'd2), .coll_o0(s_ob), .pma_tx(s_pb), .pma_tck(s_tb), .pma_rx(s_pa ^ e_ab), .pma_rck(s_ta));
    always @(posedge ca) begin e_ab <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0; end
    always @(posedge cb) begin e_ba <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0; end
    initial begin e_ab = 0; e_ba = 0; end
    integer k = 0, sent = 0, cyc = 0, ma = 0, mb = 0, first = -1, rf = -1, sf = -1, got = 0;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    always @(negedge ca) begin
        cyc = cyc + 1;
        if (cyc > 40 && sent < NB) begin
            if (cyc % 256 == 0) txa <= 512'd2;
            else begin txa <= beat(sent); sent = sent + 1; end
        end else txa <= 512'd2;
        if (cyc == FE) begin force r_a.u_link.u_enc.flt = 1'b1; force s_a.u_tx.u_enc.flt = 1'b1; end
        if (s_pa !== r_pa || s_oa[511:0] !== r_oa[511:0] || s_oa[513] !== r_oa[513]) begin ma = ma + 1; if (first < 0) first = cyc; end
        if (cyc < FE && s_oa[512] !== r_oa[512]) begin ma = ma + 1; if (first < 0) first = cyc; end
        if (rf < 0 && r_oa[512]) rf = cyc;
        if (sf < 0 && s_oa[512]) sf = cyc;
        if (cyc == NCYC) begin
            $display("SERDES_SPLIT_STATS cycles=%0d mismatchA=%0d mismatchB=%0d first=%0d beats_rx_B=%0d fault_edge R=%0d S=%0d live A=%b/%b",
                cyc, ma, mb, first, got, rf, sf, r_oa[513], s_oa[513]);
            if (ma + mb != 0) $display("SERDES_SPLIT FAIL lockstep mismatch (first at A edge %0d)", first);
            else if (got < NB - 400) $display("SERDES_SPLIT FAIL vacuous: B received %0d beats", got);
            else if (rf < 0 || sf != rf + 2) $display("SERDES_SPLIT FAIL fault latency R %0d S %0d (want S = R + 2)", rf, sf);
            else $display("SERDES_SPLIT PASS split == unsplit for %0d A edges (%0d beats over FEC), fault +2 edges", cyc, got);
            $finish;
        end
    end
    always @(negedge cb) if (rst) begin
        if (s_ob !== r_ob || s_pb !== r_pb) begin mb = mb + 1; if (first < 0) first = cyc; end
        if (!(r_ob[1] && !r_ob[0]) && r_ob[511:0] === beat(got)) got = got + 1;
    end
    initial begin repeat (8) @(posedge ca); rst = 1; end
endmodule
