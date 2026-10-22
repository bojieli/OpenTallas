`timescale 1ns/1ps
// tb_pdie_ucie_col (HBM-UCIE8 10-20): the landed HBM host UCIe column ot_pdie_ucie_col (wrapper ot_pdie_ucie_col_w) in a
// two-die link bench (same method as tb_s81_pdie_col): die B 300 ppm slow (pma_rck != clk, the CDC children are exercised:
// the rate matcher must delete IDLE beats), a stream of NB numbered data beats A -> B with an IDLE beat every 256 cycles.
// MODE 0: column <-> column; MODE 1: column A -> reference ot_pdie_ucie B; MODE 2: reference A -> column B (the column is
// wire-compatible with the reference: same pads {valid, beat}, only fixed latency differs).
// PASS: >= NB - 400 data beats at B, all in order and exact, st(B) = live, no fault.
// Mutants (forced on the receiving column die B, MODE 0 only): MUT 1 rate-matcher SRAM read address stuck at row 0;
// MUT 2 rate-matcher write valid stuck 0 (beats never stored); MUT 3 status receive flag input stuck 0 (live never seen);
// each must FAIL.
module tb_pdie_ucie_col;
    parameter integer MODE = 0, MUT = 0, NB = 6000;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    reg [511:0] txa = 512'd2; wire [511:0] rxb, rxa; wire [1:0] sta, stb;
    wire [512:0] pa, pb; wire tca, tcb;
    generate if (MODE == 2) begin : g_a_ref
        ot_pdie_ucie u_a (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
    end else begin : g_a_col
        ot_pdie_ucie_col_w u_a (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb), .pma_rck(tcb));
    end endgenerate
    generate if (MODE == 1) begin : g_b_ref
        ot_pdie_ucie u_b (.clk(cb), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa), .pma_rck(tca));
    end else begin : g_b_col
        ot_pdie_ucie_col_w u_b (.clk(cb), .rst(rst), .tx(512'd2), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa), .pma_rck(tca));
        if (MUT == 1) begin : g_m1
            initial force u_b.u_lp.u_rmm.r_addr_in = 4'd0;
        end
        if (MUT == 2) begin : g_m2
            initial force u_b.u_lp.u_rm.w_v = 1'b0;
        end
        if (MUT == 3) begin : g_m3
            initial force u_b.u_lp.u_sts.r_v = 1'b0;
        end
    end endgenerate
    integer k = 0, sent = 0, cyc = 0;
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
    integer got = 0, bad = 0, idles = 0;
    always @(posedge cb) if (rst) begin
        if (rxb[1] && !rxb[0]) idles = idles + 1;
        else begin
            if (rxb !== beat(got)) begin bad = bad + 1; if (bad < 4) $display("ERR beat %0d", got); end
            got = got + 1;
        end
    end
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        wait (sent == NB);
        repeat (500) @(posedge cb);
        $display("TB_PDIE_UCIE_COL MODE=%0d MUT=%0d sent=%0d got=%0d bad=%0d idles_seen=%0d stA=%b stB=%b", MODE, MUT, sent, got,
                 bad, idles, sta, stb);
        if (got >= NB - 400 && bad == 0 && stb == 2'b10) $display("TB_PDIE_UCIE_COL PASS"); else $display("TB_PDIE_UCIE_COL FAIL");
        $finish;
    end
endmodule
