`timescale 1ns/1ps
// Cycle equivalence of rtl/hdc/v41/ot_hdc_fsqrt.sv (rebalanced) against the
// qualified rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv: on one stimulus of +N
// edge-biased arguments with random bubbles, the rebalanced pipe's valid, code
// and refusal equal the qualified pipe's exactly ONE cycle later, every cycle.
module tb_hdc_fsqrt_equiv (input wire clk);
    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] a = 0;
    wire        rv;
    wire [31:0] ry;
    wire [1:0]  re;
    ot_a3_engram_fp32_sqrt_rne_pipe ref_u (.clk(clk), .rst_n(rst_n), .in_valid(v), .argument_code(a),
                                           .out_valid(rv), .result_code(ry), .result_error(re));
    wire        dv, df;
    wire [31:0] dy;
    ot_hdc_fsqrt dut_u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .y(dy), .vo(dv), .fault(df));
    // the qualified pipe's result, one cycle later
    reg        rv1 = 1'b0;
    reg [31:0] ry1 = 0;
    reg [1:0]  re1 = 0;
    always @(posedge clk) begin rv1 <= rv; ry1 <= ry; re1 <= re; end

    integer n = 1000000, cyc = 0, sent = 0, checked = 0, bad = 0, refused = 0, quiet = 0;
    reg [31:0] seed = 32'h2545_F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [31:0] operand(input [31:0] r1, input [31:0] r2);
        begin
            case (r1[2:0])
                3'd0: operand = r2;                                              // anything
                3'd1: operand = {1'b0, 8'd0, r2[22:0] >> r1[7:3]};              // subnormal / zero
                3'd2: operand = {r2[31], 31'd0};                                  // +-0
                3'd3: operand = {1'b0, 8'hFF, r2[22:0] & {23{r1[8]}}};         // inf / NaN
                3'd4: operand = {1'b0, 8'd1 + {3'd0, r2[27:23]}, r2[22:0]};      // tiny normal
                3'd5: operand = {1'b0, 8'd224 + {3'd0, r2[27:23]}, r2[22:0]};    // huge normal
                3'd6: operand = {1'b0, r2[30:23], r2[22:12], 12'd0};             // short significand
                default: operand = {1'b0, r2[30:0]};                              // nonnegative
            endcase
        end
    endfunction
    initial if (!$value$plusargs("N=%d", n)) n = 1000000;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            seed = xs(seed);
            v <= (seed[3:0] != 0) && (sent < n);
            if ((seed[3:0] != 0) && (sent < n)) sent <= sent + 1;
            seed = xs(seed);
            a <= operand(seed, xs(seed ^ 32'h9E3779B9));
            if (dv !== rv1 || (dv && (dy !== ry1 || df !== (re1 != 2'd0)))) begin
                if (bad < 10) $display("MISMATCH cyc=%0d ref=%h/%0d dut=%h/%0d", cyc, ry1, re1, dy, df);
                bad = bad + 1;
            end
            if (dv) begin checked = checked + 1; if (df) refused = refused + 1; end
            quiet = (sent >= n) ? quiet + 1 : 0;
            if (quiet > 40) begin
                $display("SQRTEQ checked=%0d refused=%0d mismatches=%0d", checked, refused, bad);
                if (bad == 0 && checked == n) $display("PASS"); else $display("FAIL");
                $finish;
            end
        end
    end
endmodule
