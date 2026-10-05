`timescale 1ns/1ps
// ot_a3_fp32_sqrt_rne against the reference's own correctly-rounded square root.
//
// tools/build_a3_fp32_sqrt_vectors.py calls ``_binary32_sqrt_rne`` from
// runtime/reference/sqrt_softplus.py, which settles the last bit by an exact
// midpoint comparison on exact rationals -- so the expectations here are
// correctly rounded by construction, not by agreement with a library.
module tb_a3_fp32_sqrt;
    reg clk = 0, rst_n = 0, iv = 0;
    reg [31:0] a = 0;
    wire [31:0] y;
    wire invalid, ov, busy;

    ot_a3_fp32_sqrt_rne dut (.clk(clk), .rst_n(rst_n), .valid_in(iv),
                             .a(a), .y(y), .invalid(invalid),
                             .valid_out(ov), .busy(busy));
    always #1 clk = ~clk;

    reg [31:0] vin  [0:65535];
    reg [31:0] vout [0:65535];
    integer i, n, errors = 0, shown = 0, fh, code;
    integer exact = 0, rounded_up = 0;

    initial begin
        fh = $fopen("sqrt_count.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open sqrt_count.txt"); $finish; end
        code = $fscanf(fh, "%d\n", n);
        $fclose(fh);
        $readmemh("sqrt_in.hex", vin);
        $readmemh("sqrt_out.hex", vout);

        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;
        for (i = 0; i < n; i = i + 1) begin
            @(negedge clk); a = vin[i]; iv = 1;
            @(negedge clk); iv = 0;
            wait (ov); @(negedge clk);
            if (invalid !== 1'b0) begin
                if (shown < 10) begin
                    $display("FAIL %08h refused, expected %08h", vin[i], vout[i]);
                    shown = shown + 1;
                end
                errors = errors + 1;
            end else if (y !== vout[i]) begin
                if (shown < 10) begin
                    $display("FAIL sqrt(%08h) got %08h expected %08h",
                             vin[i], y, vout[i]);
                    shown = shown + 1;
                end
                errors = errors + 1;
            end
        end

        //: A negative operand and a nonfinite one must fail closed: the
        //: reference RAISES on both rather than returning a value, and the
        //: softplus that feeds this cannot produce either.
        @(negedge clk); a = 32'hbf80_0000; iv = 1; @(negedge clk); iv = 0;
        wait (ov); @(negedge clk);
        if (invalid !== 1'b1) begin
            $display("FAIL -1.0 was not refused"); errors = errors + 1;
        end
        @(negedge clk); a = 32'h7f80_0000; iv = 1; @(negedge clk); iv = 0;
        wait (ov); @(negedge clk);
        if (invalid !== 1'b1) begin
            $display("FAIL +inf was not refused"); errors = errors + 1;
        end
        //: Negative zero is sqrt(+-0) = +0, not a refusal: the reference returns
        //: code 0 for a zero of either sign, and a flushed softplus can produce
        //: the negative one.
        @(negedge clk); a = 32'h8000_0000; iv = 1; @(negedge clk); iv = 0;
        wait (ov); @(negedge clk);
        if ((invalid !== 1'b0) || (y !== 32'd0)) begin
            $display("FAIL sqrt(-0) gave invalid=%0b y=%08h", invalid, y);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_fp32_sqrt: %0d cases correctly rounded against _binary32_sqrt_rne, and a negative or nonfinite operand fails closed", n);
        else
            $display("FAIL a3_fp32_sqrt: %0d errors of %0d", errors, n);
        $finish;
    end
endmodule
