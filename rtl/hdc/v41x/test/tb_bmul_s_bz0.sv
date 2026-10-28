`timescale 1ns/1ps
// LEC-FPREG-3 10-27: ot_hdc_v41x_attn_bmul_s BZ0 = 1 (mb[0] decoded as 1'b0) against BZ0 = 0 in lockstep on random
// operands whose b[0] = 0 (deq_b's bf16 LSB contract); every cycle y / flt must match.  -DOT_BZ0_MUT drives b[0]
// random (the contract broken): the run must report mismatches (negative control).
module tb_bmul_s_bz0;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [15:0] a, b;
    reg pad;
    wire [31:0] y0, y1;
    wire f0, f1;
    ot_hdc_v41x_attn_bmul_s #(.ML(6), .BZ0(0)) u0 (.clk(clk), .a(a), .b(b), .pad(pad), .y(y0), .flt(f0));
    ot_hdc_v41x_attn_bmul_s #(.ML(6), .BZ0(1)) u1 (.clk(clk), .a(a), .b(b), .pad(pad), .y(y1), .flt(f1));
    integer n, bad;
    initial begin
        bad = 0;
        for (n = 0; n < 200000; n = n + 1) begin
            a = $random; b = $random; pad = ($random % 16) == 0;
`ifndef OT_BZ0_MUT
            b[0] = 1'b0;
`endif
            if (n % 7 == 0) b[14:7] = 8'd0;          // subnormal operands
            if (n % 11 == 0) a[14:7] = 8'd0;
            @(posedge clk); #0.1;
            if (n > 8 && (y0 !== y1 || f0 !== f1)) bad = bad + 1;
        end
        $display("BZ0 lockstep cycles=%0d mismatches=%0d", n, bad);
        $finish;
    end
endmodule
