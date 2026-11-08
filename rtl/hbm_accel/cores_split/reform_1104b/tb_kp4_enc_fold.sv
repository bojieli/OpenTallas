`timescale 1ns/1ps
// DIE-HEAD-85/TXF 2026-11-07: ot_s81_kp4_enc_la FOLD = 1 vs FOLD = 0 (same LA = 2, FF = 1, CH_STAGE = CHS) on one random
// beat stream, lock-step: p_v / p_d / fault must be equal on EVERY cycle (FOLD adds no cycle).  Optional one-cycle
// stall (+STALL=c) and a mid-stream reset (+RESET_AT=c).  +DUMP=<file> writes every valid DUT word (hex) for the
// rs544 frame check (tools/s81_link/check_kp4_dump.py). MUT 1/4/5/6 must FAIL;
// MUT 2 is equivalent under FOLD. RELAY=1 compares to the exact reference delayed
// one edge. CMUT 7 corrupts one regional capture; CMUT 8 bypasses one relay.
// Prints TB_KP4_ENC_FOLD PASS|FAIL <mismatches> <compared words> <parity words> <epochs>.
module tb_kp4_enc_fold;
    parameter integer MUT = 0;
    parameter integer CHS = 1;
    parameter integer REG4 = 0;
    parameter integer CMUT = 0;
    parameter integer RELAY = 0;
    reg clk = 0, rst_n = 0, tx_v = 0;
    reg [511:0] tx_d = 0;
    wire rv, dv, rf, df;
    wire [543:0] rd, dd;
    reg rv_delay = 0, rf_delay = 0;
    reg [543:0] rd_delay = 0;
    always @(posedge clk) begin rv_delay <= rv; rf_delay <= rf; rd_delay <= rd; end
    wire cv = RELAY ? rv_delay : rv;
    wire cf = RELAY ? rf_delay : rf;
    wire [543:0] cd = RELAY ? rd_delay : rd;
    ot_s81_kp4_enc_la #(.MUT(0), .LA(2), .FF(1), .CH_STAGE(CHS), .FOLD(0)) u_ref
        (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(rv), .p_d(rd), .fault(rf));
    ot_s81_kp4_enc_la #(.MUT(MUT), .LA(2), .FF(1), .CH_STAGE(CHS), .FOLD(1), .CH_REGION4(REG4), .CH_MUT(CMUT), .CH_RELAY1(RELAY)) u_dut
        (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(dv), .p_d(dd), .fault(df));
    always #1 clk = ~clk;
    integer cyc = 0, bad = 0, cmp = 0, par = 0, frame_word = 0, epochs = 0, fd = 0;
    integer ncyc = 4000, stall = -1, reset_at = -1, seed = 1, k, warm = 0;
    reg was_valid = 0;
    reg [1023:0] dump;
    initial begin
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        if (!$value$plusargs("STALL=%d", stall)) stall = -1;
        if (!$value$plusargs("RESET_AT=%d", reset_at)) reset_at = -1;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if ($value$plusargs("DUMP=%s", dump)) fd = $fopen(dump, "w");
        k = $urandom(seed);
    end
    always @(negedge clk) begin
        cyc = cyc + 1;
        rst_n = (cyc >= 5) && !(reset_at >= 0 && cyc >= reset_at && cyc < reset_at + 6);
        tx_v = rst_n && cyc >= 13 && !(reset_at >= 0 && cyc < reset_at + 18 && cyc >= reset_at) && cyc != stall;
        for (k = 0; k < 16; k = k + 1) tx_d[32 * k +: 32] = $urandom;
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            warm = 0; was_valid = 0; frame_word = 0;
        end else begin
            warm = warm + 1;
            if (warm > 8) begin
                if (dv !== cv || (cv && dd !== cd) || df !== cf) begin
                    bad = bad + 1;
                    if (bad <= 5) $display("ERR cyc=%0d valid=%b/%b fault=%b/%b data_xor=%h", cyc, dv, cv, df, cf, dd ^ cd);
                end
                if (dv && fd != 0) $fwrite(fd, "%0d %h\n", epochs + (was_valid ? 0 : 1), dd);
                if (cv) begin
                    cmp = cmp + 1;
                    if (!was_valid) begin epochs = epochs + 1; frame_word = 0; end
                    if (frame_word == 9) par = par + 1;
                    frame_word = (frame_word == 9) ? 0 : frame_word + 1;
                end
                was_valid = cv;
            end
        end
        if (cyc >= ncyc) begin
            $display("TB_KP4_ENC_FOLD %s MUT=%0d CHS=%0d mismatches=%0d compared_words=%0d parity_words=%0d epochs=%0d extra_edges=%0d CMUT=%0d REG4=%0d",
                     (bad == 0 && cmp > 100 && par > 10) ? "PASS" : "FAIL", MUT, CHS, bad, cmp, par, epochs, RELAY, CMUT, REG4);
            if (fd != 0) $fclose(fd);
            if (bad != 0 || cmp <= 100 || par <= 10) $fatal(1, "fold stream refinement failed");
            $finish;
        end
    end
endmodule
