`timescale 1ns/1ps
// tb_s81_pdie_fanout_eq (FABLE-FIX-HEAD-SERDES 2026-11-16): the fanout-copy form of ot_pdie_serdes (DNGB 12, RMRPC 32: more
// kept load copies in the KP4 key-equation units, kept read-select copies in the rate matcher) against the default form,
// cycle exact.  The tb_s81_pdie_link scene (die A -> die B, plesiochronous clocks, random pad bit errors corrected by the
// FEC); die B exists twice (u_b default, u_c copies) on the SAME clocks, reset and pads: rx, st and pma_tx must be equal in
// every cycle after reset, and the link itself must pass.  Mutant RMRPC_MUT_STALE (one select copy stalls) must FAIL.
module tb_s81_pdie_fanout_eq;
    parameter integer NB = 3000, DNGB = 12, RMRPC = 32, DKREG = 0;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    reg [511:0] txa = 512'd2; wire [511:0] rxb, rxc, rxa; wire [1:0] sta, stb, stc;
    wire [543:0] pa, pb, pc; wire tca, tcb, tcc; reg [543:0] pa_e;
    ot_pdie_serdes u_a (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
    ot_pdie_serdes u_b (.clk(cb), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_e), .pma_rck(tca));
    ot_pdie_serdes #(.DNGB(DNGB), .RMRPC(RMRPC), .DKREG(DKREG)) u_c (.clk(cb), .rst(rst), .tx(512'd2), .rx(rxc), .st(stc), .pma_tx(pc), .pma_tck(tcc),
        .pma_rx(pa_e), .pma_rck(tca));
    reg err_on = 0; integer err_bit = 0;
    always @* begin pa_e = pa; if (err_on) pa_e[err_bit] = ~pa[err_bit]; end
    always @(posedge tca) begin err_on <= ($urandom % 2) == 0; err_bit <= $urandom % 544; end
    integer sent = 0, cyc = 0;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    always @(negedge ca) begin
        cyc = cyc + 1;
        if (cyc > 40 && sent < NB) begin
            if (cyc % 256 == 0) txa <= 512'd2;
            else begin txa <= beat(sent); sent = sent + 1; end
        end else txa <= 512'd2;
    end
    integer got = 0, bad = 0, neq = 0, ncmp = 0, gotc = 0, badc = 0;
    // DKREG != 0 (HEAD-SERDES-O 11-16): the copy decodes one pma_rck later, so rx / st are not cycle equal; u_c's rx must
    // carry the same beat stream (in order, none bad) and pma_tx (TX side, untouched) must stay cycle equal.
    always @(posedge cb) if (rst && DKREG != 0) begin
        if (!(rxc[1] && !rxc[0])) begin if (rxc !== beat(gotc)) badc = badc + 1; gotc = gotc + 1; end
    end
    always @(posedge cb) if (rst) begin
        ncmp = ncmp + 1;
        if ((DKREG == 0 && (rxb !== rxc || stb !== stc)) || pb !== pc) begin neq = neq + 1; if (neq < 4) $display("ERR differ at cb cycle %0d", ncmp); end
        if (!(rxb[1] && !rxb[0])) begin if (rxb !== beat(got)) bad = bad + 1; got = got + 1; end
    end
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        wait (sent == NB);
        repeat (400) @(posedge cb);
        $display("TB_S81_PDIE_FANOUT_EQ DNGB=%0d RMRPC=%0d DKREG=%0d sent=%0d got=%0d bad=%0d gotc=%0d badc=%0d compared=%0d differ=%0d st=%b stc=%b %s",
                 DNGB, RMRPC, DKREG, sent, got, bad, gotc, badc, ncmp, neq, stb, stc,
                 (got >= NB - 400 && bad == 0 && neq == 0 && stb == 2'b10 && ncmp > NB
                  && (DKREG == 0 || (gotc >= NB - 400 && badc == 0 && stc == 2'b10))) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
