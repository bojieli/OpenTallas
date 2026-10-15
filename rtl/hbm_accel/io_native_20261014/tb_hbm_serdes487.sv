`timescale 1ns/1ps
// tb_s81_pdie_link (s81-die-rtl-bind 2026-10-14, F10): two dies' link macros back to back over their pads, the two die
// clocks plesiochronous (B runs 300 ppm slow): die A's lane beats (a sequence-numbered data beat a cycle, one gearbox
// IDLE beat every 256) must arrive at die B's rx IN ORDER and EXACT (IDLE beats may be dropped / inserted by the rate
// matchers: the gearbox skips them).  SERDES 1: ot_pdie_serdes with random bit errors on the pads (<= 1 a PMA word:
// <= 10 symbols a codeword, inside t = 15) -- corrected by the KP4 FEC; SERDES 0: ot_pdie_ucie (no errors, no FEC).
// PASS: >= NB - 400 data beats received, all in order and exact, st live, no fault.  Mutant: DMUT 2 (FEC Forney) FAIL.
module tb_hbm_serdes487;
    parameter integer SERDES = 1, DMUT = 0, NB = 512;
    localparam integer PW = SERDES ? 544 : 513;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    reg [486:0] txa = 487'd2; wire [486:0] rxb,rxa; wire [1:0] sta, stb;
    wire [PW-1:0] pa, pb; wire tca, tcb; reg [PW-1:0] pa_e;
    wire pfa,pfb;
    hfd_serdes487 #(.DMUT(DMUT)) a(.clk(ca),.rst_n(rst),.tx(txa),.rx(rxa),.st(sta),.pma_tx(pa),.pma_tck(tca),.pma_rx(pb),.pma_rck(tcb),.padding_fault(pfa));
    hfd_serdes487 #(.DMUT(DMUT)) b(.clk(cb),.rst_n(rst),.tx(487'd2),.rx(rxb),.st(stb),.pma_tx(pb),.pma_tck(tcb),.pma_rx(pa_e),.pma_rck(tca),.padding_fault(pfb));
    // channel A -> B: one random bit error in about every second PMA word (SERDES only)
    always @* begin
        pa_e = pa;
        if (SERDES && err_on) pa_e[err_bit] = ~pa[err_bit];
    end
    reg err_on = 0; integer err_bit = 0;
    always @(posedge tca) begin err_on <= ($urandom % 2) == 0; err_bit <= $urandom % PW; end
    // A's beat stream: data beat k = {k, pattern}, bit 1 = 0; IDLE every 256 = 512'b10
    integer k = 0, sent = 0, cyc = 0;
    function automatic [486:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    always @(negedge ca) begin
        cyc = cyc + 1;
        if (cyc > 500 && sent < NB) begin
            if (cyc % 256 == 0) txa <= 512'd2;
            else begin txa <= beat(sent); sent = sent + 1; end
        end else txa <= 512'd2;
    end
    // B's received stream
    integer got = 0, bad = 0, idles = 0, first = -1;
    always @(posedge cb) if (rst) begin
        if (!stb[1] || (rxb[1] && !rxb[0])) idles = idles + 1;
        else begin
            if (first < 0) first = 0;
            if (rxb !== beat(got)) begin bad = bad + 1; if (bad < 4) $display("ERR beat %0d", got); end
            got = got + 1;
        end
    end
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        wait (sent == NB);
        repeat (400) @(posedge cb);
        $display("HBM_SERDES487 SERDES=%0d DMUT=%0d sent=%0d got=%0d bad=%0d idles_seen=%0d stA=%b stB=%b %s", SERDES, DMUT, sent, got,
                 bad, idles, sta, stb, (got == NB && bad == 0 && stb == 2'b10 && !pfa && !pfb) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
