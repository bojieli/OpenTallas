`timescale 1ns/1ps
// ot_hbm_accel_bmul (bubble `kill`, split significand product) against ot_hdc_bmul with the original bubble gate
// (a forced to +0): random BF16 operands biased to edge exponents (0, 1, 254, 255) and random bubbles; y and fault
// must agree every cycle (both LATENCY 5).
module tb_hbm_accel_bmul_equiv;
    parameter integer N = 2000000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg v = 0, kill = 0; reg [15:0] a = 0, b = 0;
    wire [31:0] y0, y1; wire f0, f1;
    ot_hdc_bmul u0 (.clk(clk), .rst_n(rst_n), .v(v), .a({kill ? 16'd0 : a, 16'd0}), .b({b, 16'd0}), .y(y0), .fault(f0));
    ot_hbm_accel_bmul u1 (.clk(clk), .rst_n(rst_n), .v(v), .kill(kill), .a({a, 16'hdead}), .b({b, 16'hbeef}),
                          .y(y1), .fault(f1));
    integer i, mism = 0;
    function [15:0] rb(input integer r);
        reg [7:0] e;
        begin
            case (r[2:0])
                3'd0: e = 8'd0; 3'd1: e = 8'd1; 3'd2: e = 8'd254; 3'd3: e = 8'd255;
                default: e = r[15:8];
            endcase
            rb = {r[16], e, r[23:17]};
        end
    endfunction
    always @(posedge clk) if (rst_n && (y0 !== y1 || f0 !== f1)) mism = mism + 1;
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            v = ($urandom % 8) != 0; kill = !v || (($urandom % 16) == 0 ? 1'b0 : 1'b0);
            a = rb($urandom); b = rb($urandom);
        end
        repeat (8) @(negedge clk);
        $display("BMUL_EQUIV vectors %0d mismatches %0d", N, mism);
        $display(mism == 0 ? "PASS" : "FAIL");
        if (mism != 0) $fatal(1, "EQUIVALENCE_TERMINAL_FAIL");
        $finish;
    end
endmodule
