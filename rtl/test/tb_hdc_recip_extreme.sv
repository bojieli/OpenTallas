`timescale 1ns/1ps
// Finite denominators just beyond the bit-seed range must complete as +0.
module tb_hdc_recip_extreme;
    reg clk = 0, rst_n = 0, v = 0;
    reg [31:0] x = 0;
    always #0.5 clk = ~clk;
    wire [31:0] y, yq, yr;
    wire vo, voq, vor_, fault, faultq, faultr;
    integer got = 0, gotq = 0, gotr = 0, cycles = 0;

    ot_hdc_recip dut (clk, rst_n, v, x, y, vo, fault);
    ot_hdc_recip_q short_dut (clk, rst_n, v, x, yq, voq, faultq);
    ot_hdc_recip_ref ref_dut (clk, rst_n, v, x, yr, vor_, faultr);

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1;
        v = 1; x = 32'h7EF311C8;
        @(negedge clk) x = 32'h7F7FFFFF;
        @(negedge clk) v = 0;
    end

    always @(posedge clk) if (rst_n) begin
        cycles <= cycles + 1;
        if (vo) begin
            if (y !== 32'h00000000 || fault) $fatal(1, "full reciprocal y=%h fault=%b", y, fault);
            got <= got + 1;
        end
        if (voq) begin
            if (yq !== 32'h00000000 || faultq) $fatal(1, "short reciprocal y=%h fault=%b", yq, faultq);
            gotq <= gotq + 1;
        end
        if (vor_) begin
            if (yr !== 32'h00000000 || faultr) $fatal(1, "reference reciprocal y=%h fault=%b", yr, faultr);
            gotr <= gotr + 1;
        end
        if (got == 2 && gotq == 2 && gotr == 2) begin
            $display("RECIP_EXTREME full=%0d short=%0d reference=%0d", got, gotq, gotr);
            $display("PASS");
            $finish;
        end
        if (cycles > 120) $fatal(1, "reciprocal timeout full=%0d short=%0d reference=%0d", got, gotq, gotr);
    end
endmodule
