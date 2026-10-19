`timescale 1ns/1ps
// Equivalence: ot_hgi_coll_aq_scale13r (rebalanced stage 4) vs the closed ot_hbm_xp_aq_scale13, both coefficients
// (1/448, 1/6), every exponent field 0..255 of a x NPER significands (random + edge patterns), both signs; a new
// operand every edge; y and fault compared on every edge whose input was valid 5 edges earlier.
module tb_aq_scale13r_eq;
    parameter integer NPER = 4096;
    reg clk = 0, rst_n = 0, v = 0; reg [31:0] a = 0, b = 32'h3b124925;
    always #0.5 clk = ~clk;
    wire [31:0] yo, yn; wire fo, fn;
    ot_hbm_xp_aq_scale13 ref0(.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yo), .fault(fo));
    ot_hgi_coll_aq_scale13r dut(.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yn), .fault(fn));
    reg [4:0] vp = 0; longint checks = 0, errs = 0, subs = 0;
    always @(posedge clk) vp <= {vp[3:0], v};
    always @(negedge clk) if (rst_n && vp[4]) begin
        checks++;
        if (yo[30:23] == 8'd0 && yo[22:0] != 0) subs++;
        if (yo !== yn || fo !== fn) begin
            errs++;
            if (errs < 10) $display("SCALE13R MISMATCH y %h/%h f %b/%b", yo, yn, fo, fn);
        end
    end
    integer seed = 1;
    initial begin
        repeat (5) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
        for (integer c = 0; c < 2; c++) begin
            b = c ? 32'h3e2aaaab : 32'h3b124925;
            for (integer e = 0; e < 256; e++)
                for (integer n = 0; n < NPER; n++) begin
                    reg [22:0] m;
                    m = 23'($random(seed));
                    case (n % 8) 0: m = 0; 1: m = 23'h7fffff; 2: m = 23'(n); 3: m = 23'h7fffff - 23'(n); default: ; endcase
                    a = {1'(n >> 3), 8'(e), m};
                    v = 1; @(negedge clk);
                end
        end
        v = 0; repeat (8) @(negedge clk);
        if (errs == 0 && checks == 2 * 256 * NPER)
            $display("SCALE13R_EQ PASS checks=%0d subnormal_results=%0d", checks, subs);
        else $display("SCALE13R_EQ FAIL errors=%0d checks=%0d", errs, checks);
        $finish;
    end
endmodule
