`timescale 1ns/1ps
// tb_kp4_enc_la (DIE-S81-85 11-09): lock-step bench of ot_s81_kp4_enc with OT_S81_KP4_ENC_LA (dut) against the
// define-off module (ref = ot_s81_kp4_enc.sv of origin/main renamed ot_s81_kp4_enc_ref by the run script).
// Declared extra latency LAT = 0: p_v / p_d / fault must be equal on every cycle.  Stimulus: random 512-b beats,
// back-to-back frames, beat gaps (fault path), random synchronous resets mid-frame, idle starts.
// Run: tools/s81_link/run_kp4_enc_la_bench.sh (Verilator; -G PPCYC / MUT / PIN_FAULT / SEED / NCYC).
module tb_kp4_enc_la #(parameter integer PPCYC = 1, parameter integer MUT = 0, parameter integer PIN_FAULT = 1,
    parameter integer SEED = 1, parameter integer NCYC = 30000, parameter integer GAPS = 1);
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg tx_v = 1'b0;
    reg [511:0] tx_d = 512'd0;
    wire r_v, d_v, r_f, d_f;
    wire [543:0] r_d, d_d;
    ot_s81_kp4_enc_ref #(.MUT(MUT), .PIN_FAULT(PIN_FAULT), .H0_SEQ_ONLY(1), .PPCYC(PPCYC)) u_ref (
        .clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(r_v), .p_d(r_d), .fault(r_f));
    ot_s81_kp4_enc #(.MUT(MUT), .PIN_FAULT(PIN_FAULT), .H0_SEQ_ONLY(1), .PPCYC(PPCYC)) u_dut (
        .clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(d_v), .p_d(d_d), .fault(d_f));
    integer cyc = 0, nerr = 0, nv = 0, npar = 0, nrst = 0, ngap = 0, k, seed;
    integer rst_left = 8, idle_left = 0;
    reg [31:0] r;
    always #0.5 clk = ~clk;
    initial begin
        seed = SEED;
        r = $urandom(seed);
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > 12) begin
            if ({r_v, r_d, r_f} !== {d_v, d_d, d_f}) begin
                nerr = nerr + 1;
                if (nerr <= 5) $display("MISMATCH cyc %0d p_v %b/%b fault %b/%b p_d xor %h", cyc, r_v, d_v, r_f,
                                        d_f, r_d ^ d_d);
            end
            if (r_v) nv = nv + 1;
            if (r_v && r_d[299:0] != 300'd0) npar = npar + 1;
        end
    end
    // stimulus on the falling edge
    always @(negedge clk) begin
        for (k = 0; k < 16; k = k + 1) tx_d[32 * k +: 32] <= $urandom;
        if (rst_left > 0) begin
            rst_left = rst_left - 1; rst_n <= 1'b0; tx_v <= 1'b0;
            if (rst_left == 0) idle_left = $urandom % 40;
        end else begin
            rst_n <= 1'b1;
            if ($urandom % 2500 == 0) begin rst_left = 1 + $urandom % 6; nrst = nrst + 1; end
            if (idle_left > 0) begin idle_left = idle_left - 1; tx_v <= 1'b0; end
            else if (GAPS != 0 && $urandom % 300 == 0) begin tx_v <= 1'b0; ngap = ngap + 1; end
            else tx_v <= 1'b1;
        end
        if (cyc == NCYC) begin
            $display("KP4_ENC_LA %s PPCYC=%0d MUT=%0d PIN_FAULT=%0d SEED=%0d LAT=0 cycles=%0d p_v=%0d words_tail_nz=%0d resets=%0d gaps=%0d mismatches=%0d",
                     (nerr == 0 && nv > 1000) ? "PASS" : "FAIL", PPCYC, MUT, PIN_FAULT, SEED, cyc, nv, npar, nrst,
                     ngap, nerr);
            $finish;
        end
    end
endmodule
