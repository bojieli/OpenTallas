`timescale 1ns/1ps
// HBM-GAPS-3 2026-11-05: ot_pdie_serdes_tx #(.ELA(2)) : pma_tx == ELA 1 delayed one edge, e_flt_o equal (the fault is on the input side).
module tb_pdie_tx_ela;
    parameter integer MUT = 0;
    reg clk = 0, rst = 0; reg [511:0] tx = 512'd2;
    wire [543:0] a, b; wire fa, fb;
    ot_pdie_serdes_tx #(.ELA(1)) u_a (.clk(clk), .rst(rst), .tx(tx), .pma_tx(a), .e_flt_o(fa));
    ot_pdie_serdes_tx #(.ELA(2), .EMUT(MUT)) u_b (.clk(clk), .rst(rst), .tx(tx), .pma_tx(b), .e_flt_o(fb));
    always #1 clk = ~clk;
    reg [543:0] aq; reg faq; integer cyc = 0, bad = 0, nz = 0, k;
    always @(posedge clk) begin
        cyc <= cyc + 1; aq <= a; faq <= fa;
        if (cyc == 3) rst <= 1;
        for (k = 0; k < 16; k = k + 1) tx[32 * k +: 32] <= $urandom;
        if (cyc > 6 && (^aq) !== 1'bx) begin   // from the first defined reference word (the PMA model has no reset)
            if (b !== aq || fb !== fa) begin bad = bad + 1; if (bad < 3) $display("ERR %0d a=%h b=%h fa=%b fb=%b", cyc, aq[15:0], b[15:0], fa, fb); end
            if (aq != 0) nz = nz + 1;
        end
        if (cyc == 600) begin $display("TB_PDIE_TX_ELA %s MUT=%0d mismatches %0d nonzero %0d", (bad == 0 && nz > 400) ? "PASS" : "FAIL", MUT, bad, nz); $finish; end
    end
endmodule
