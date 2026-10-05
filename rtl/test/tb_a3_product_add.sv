`timescale 1ns/1ps
// Focused differential for the exact BF16-product/binary32-accumulator step.
// The image is generated directly from runtime.reference.formats using exact
// Fraction arithmetic: count, then (accumulator, lhs|rhs<<16, error, result).
module tb_a3_product_add;
    localparam integer MAX_CASES = 5460;
    reg [31:0] vectors [0:MAX_CASES * 4];
    reg [31:0] accumulator;
    reg [15:0] lhs;
    reg [15:0] rhs;
    wire [33:0] observed =
        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(
            accumulator, lhs, rhs
        );
    integer count;
    integer index;
    integer base;
    integer failures;

    initial begin
        $readmemh("product_add.hex", vectors);
        count = vectors[0];
        failures = 0;
        if ((count <= 0) || (count > MAX_CASES))
            $fatal(1, "invalid product-add vector count %0d", count);
        for (index = 0; index < count; index = index + 1) begin
            base = 1 + index * 4;
            accumulator = vectors[base];
            lhs = vectors[base + 1][15:0];
            rhs = vectors[base + 1][31:16];
            #1;
            if ((observed[33:32] !== vectors[base + 2][1:0]) ||
                ((vectors[base + 2] == 0) &&
                 (observed[31:0] !== vectors[base + 3]))) begin
                failures = failures + 1;
                if (failures < 20)
                    $display("FAIL product-add %0d acc=%08x lhs=%04x rhs=%04x got=%0d:%08x want=%0d:%08x",
                             index, accumulator, lhs, rhs, observed[33:32],
                             observed[31:0], vectors[base + 2],
                             vectors[base + 3]);
            end
        end
        if (failures != 0)
            $fatal(1, "product-add failures=%0d", failures);
        $display("PASS exact product-add differential cases=%0d", count);
        $finish;
    end
endmodule
