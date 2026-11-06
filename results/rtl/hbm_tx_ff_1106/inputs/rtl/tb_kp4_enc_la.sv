`timescale 1ns/1ps
// HBM-GAPS-3 2026-11-05: ot_s81_kp4_enc_la vs the unchanged ot_s81_kp4_enc on the same random beat stream.
//   LA = 1: p_v / p_d equal cycle for cycle.  LA = 2: equal to the reference delayed by exactly one cycle.
//   Optional stall (+STALL=c): tx_v drops for one cycle at cycle c, so the fault path and the restart are compared too.
// Prints TB_KP4_ENC_LA PASS|FAIL <mismatches> <compared words> <parity-carrying words compared>.
module tb_kp4_enc_la;
    parameter integer LA = 2;
    parameter integer MUT = 0;
    reg clk = 0, rst_n = 0, tx_v = 0;
    reg [511:0] tx_d = 0;
    wire rv, dv, rf, df;
    wire [543:0] rd, dd;
    ot_s81_kp4_enc #(.MUT(0)) u_ref (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(rv), .p_d(rd), .fault(rf));
    ot_s81_kp4_enc_la #(.MUT(MUT), .LA(LA)) u_dut (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(dv), .p_d(dd), .fault(df));
    always #1 clk = ~clk;
    reg [543:0] rd_q; reg rv_q, rf_q;
    integer cyc = 0, bad = 0, cmp = 0, par = 0, ncyc = 400, stall = -1, seed = 1, k;
    initial begin
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 400;
        if (!$value$plusargs("STALL=%d", stall)) stall = -1;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        k = $urandom(seed);
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        rd_q <= rd; rv_q <= rv; rf_q <= rf;
        if (cyc == 4) rst_n <= 1;
        if (cyc >= 12) begin
            tx_v <= (cyc != stall);
            for (k = 0; k < 16; k = k + 1) tx_d[32 * k +: 32] <= $urandom;
        end
        if (cyc > 8) begin
            if (LA == 1 ? (dv !== rv || (rv && dd !== rd) || df !== rf)
                        : (dv !== rv_q || (rv_q && dd !== rd_q) || df !== rf)) begin
                bad = bad + 1;
                if (bad <= 3) $display("ERR cyc %0d dv %b rv %b fault %b/%b", cyc, dv, LA == 1 ? rv : rv_q, df, rf);
            end
            if (LA == 1 ? rv : rv_q) begin cmp = cmp + 1; end
        end
        if (cyc == ncyc) begin
            $display("TB_KP4_ENC_LA %s LA=%0d MUT=%0d mismatches %0d compared_words %0d", (bad == 0 && cmp > 100) ? "PASS" : "FAIL",
                     LA, MUT, bad, cmp);
            $finish;
        end
    end
endmodule
