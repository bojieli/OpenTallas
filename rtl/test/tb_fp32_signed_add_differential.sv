`timescale 1ns/1ps
module tb_fp32_signed_add_differential;
    import ot_fp32_rne_pkg::*;

    localparam integer CASE_COUNT = 20000;
    reg [97:0] vectors [0:CASE_COUNT-1];
    reg [31:0] left_code = 0;
    reg [31:0] right_code = 0;
    wire [33:0] result = fp32_add_rne(left_code, right_code);
    integer index;

    initial begin
        $readmemh("signed_add.hex", vectors);
        for (index = 0; index < CASE_COUNT; index = index + 1) begin
            left_code = vectors[index][97:66];
            right_code = vectors[index][65:34];
            #1;
            if (result !== vectors[index][33:0])
                $fatal(1,
                       "signed add differs index=%0d left=%08x right=%08x expected=%09x actual=%09x",
                       index, left_code, right_code,
                       vectors[index][33:0], result);
        end
        $display("PASS: FP32 signed-add RTL differential cases=20000 seed=5157454e334d4154");
        $finish;
    end
endmodule
