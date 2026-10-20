`timescale 1ns/1ps
// LEAD2-S81/TOK 10-19: ot_s81sl_cap_ed bench.  Random 66-bit words (valid ~50 %) for 400 edges after reset; every
// output edge is compared with the input exactly DX edges earlier (DX = the calendar's E delay, 23); no valid word may
// appear before the line is primed; >= 150 valid words must be checked (a bench that checks nothing FAILS).
// RTL mutant: DUT built with DM != DX (wrong delay) must FAIL.
module tb_s81sl_cap_ed;
    parameter integer DX = 24;
    parameter integer DM = 24;
    reg clk = 0, rst_n = 0;
    always #0.417 clk = ~clk;
    reg iv, ie, ifl; reg [31:0] it, id;
    wire ov, oe, of; wire [31:0] ot, od;
    ot_s81sl_cap_ed #(.D(DM)) dut (.clk(clk), .rst_n(rst_n), .i_v(iv), .i_t(it), .i_d(id), .i_e(ie), .i_f(ifl),
        .o_v(ov), .o_t(ot), .o_d(od), .o_e(oe), .o_f(of));
    reg [65:0] hist [0:4095];
    integer cyc = 0, checks = 0, errs = 0, seed = 7, rel = 0;
    initial begin
        iv = 0; ie = 0; ifl = 0; it = 0; id = 0;
        repeat (5) @(posedge clk); rst_n = 1;
    end
    always @(posedge clk) if (rst_n) begin
        // at edge rel the DUT captures the inputs now presented (hist[rel]); the output read here (pre-update) is the
        // word captured DX edges earlier (an N-register line read at edge j shows the input captured at edge j-N)
        hist[rel] = {ie, id, it, iv};
        if (rel > DX + 4) begin
            if (ov !== hist[rel - DX][0] || (ov && {oe, od, ot} !== hist[rel - DX][65:1])) begin
                errs = errs + 1;
                if (errs < 5) $display("MISMATCH rel %0d got v%0d t%h exp v%0d t%h", rel, ov, ot, hist[rel - DX][0], hist[rel - DX][32:1]);
            end else if (ov) checks = checks + 1;
        end else if (ov === 1'b1 && rel <= DX) begin
            errs = errs + 1; $display("EARLY_VALID rel %0d", rel);
        end
        iv <= ($random(seed) & 1) && rel > 1 && rel < 380; it <= $random(seed); id <= $random(seed); ie <= $random(seed) & 1;
        rel = rel + 1;
        if (rel == 420) begin
            if (checks >= 150 && errs == 0) $display("TB_CAP_ED PASS checks %0d D %0d", checks, DX);
            else $display("TB_CAP_ED FAIL checks %0d errs %0d D %0d DUT %0d", checks, errs, DX, DM);
            $finish;
        end
    end
endmodule
