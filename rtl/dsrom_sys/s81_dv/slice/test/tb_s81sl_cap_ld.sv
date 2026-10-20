`timescale 1ns/1ps
// LEAD2-S81/TOK2 10-19: ot_s81sl_cap_ld bench.  Random 70-bit lane words (bit 0 valid ~50 %) for 400 edges after reset;
// every output edge equals the input exactly DX edges earlier (DX = 16, the QF calendar's W lane-3 delay); no valid word
// before the line is primed; >= 150 valid words must be checked.  RTL mutant: DUT built with DM != DX must FAIL.
module tb_s81sl_cap_ld;
    parameter integer DX = 16;
    parameter integer DM = 16;
    reg clk = 0, rst_n = 0;
    always #0.417 clk = ~clk;
    reg [69:0] iw; wire [69:0] ow;
    ot_s81sl_cap_ld #(.D(DM)) dut (.clk(clk), .rst_n(rst_n), .i_w(iw), .o_w(ow));
    reg [69:0] hist [0:4095];
    integer checks = 0, errs = 0, seed = 11, rel = 0;
    initial begin iw = 0; repeat (5) @(posedge clk); rst_n = 1; end
    always @(posedge clk) if (rst_n) begin
        hist[rel] = iw;
        if (rel > DX + 4) begin
            if (ow[0] !== hist[rel - DX][0] || (ow[0] && ow !== hist[rel - DX])) begin
                errs = errs + 1;
                if (errs < 5) $display("MISMATCH rel %0d got %h exp %h", rel, ow, hist[rel - DX]);
            end else if (ow[0]) checks = checks + 1;
        end else if (ow[0] === 1'b1 && rel <= DX) begin
            errs = errs + 1; $display("EARLY_VALID rel %0d", rel);
        end
        iw <= {$random(seed), $random(seed), $random(seed)} & {69'h1fffffffffffffffff, 1'b1};
        iw[0] <= ($random(seed) & 1) && rel > 1 && rel < 380;
        rel = rel + 1;
        if (rel == 420) begin
            if (checks >= 150 && errs == 0) $display("TB_CAP_LD PASS checks %0d D %0d", checks, DX);
            else $display("TB_CAP_LD FAIL checks %0d errs %0d D %0d DUT %0d", checks, errs, DX, DM);
            $finish;
        end
    end
endmodule
