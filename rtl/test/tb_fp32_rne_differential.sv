`timescale 1ns/1ps
module tb_fp32_rne_differential;
    import ot_fp32_rne_pkg::*;

    localparam integer ADD_COUNT = 5000;
    localparam integer MUL_COUNT = 5000;
    localparam integer BF16_COUNT = 5000;
    localparam integer RSQRT_COUNT = 2000;

    reg [97:0] add_vectors [0:ADD_COUNT-1];
    reg [97:0] mul_vectors [0:MUL_COUNT-1];
    reg [50:0] bf16_vectors [0:BF16_COUNT-1];
    reg [65:0] rsqrt_vectors [0:RSQRT_COUNT-1];
    reg [31:0] left_code = 0;
    reg [31:0] right_code = 0;
    wire [33:0] add_result = fp32_add_positive_rne(
        left_code, right_code
    );
    wire [33:0] mul_result = fp32_mul_rne(left_code, right_code);
    wire [18:0] bf16_result = fp32_to_bf16_rne(left_code);

    reg clk = 0;
    reg rst_n = 0;
    reg rsqrt_in_valid = 0;
    wire rsqrt_in_ready;
    reg [31:0] argument_code = 0;
    wire rsqrt_out_valid;
    reg rsqrt_out_ready = 0;
    wire [31:0] rsqrt_result_code;
    wire [1:0] rsqrt_result_error;
    integer index;
    integer cycles;

    always #5 clk = ~clk;

    ot_fp32_rsqrt_rne rsqrt (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(rsqrt_in_valid),
        .in_ready(rsqrt_in_ready),
        .argument_code(argument_code),
        .out_valid(rsqrt_out_valid),
        .out_ready(rsqrt_out_ready),
        .result_code(rsqrt_result_code),
        .result_error(rsqrt_result_error)
    );

    initial begin
        $readmemh("arithmetic_add.hex", add_vectors);
        $readmemh("arithmetic_mul.hex", mul_vectors);
        $readmemh("arithmetic_bf16.hex", bf16_vectors);
        $readmemh("arithmetic_rsqrt.hex", rsqrt_vectors);

        for (index = 0; index < ADD_COUNT; index = index + 1) begin
            left_code = add_vectors[index][97:66];
            right_code = add_vectors[index][65:34];
            #1;
            if (add_result !== add_vectors[index][33:0])
                $fatal(1, "add differs index=%0d left=%08x right=%08x",
                       index, left_code, right_code);
        end
        for (index = 0; index < MUL_COUNT; index = index + 1) begin
            left_code = mul_vectors[index][97:66];
            right_code = mul_vectors[index][65:34];
            #1;
            if (mul_result !== mul_vectors[index][33:0])
                $fatal(1, "multiply differs index=%0d left=%08x right=%08x",
                       index, left_code, right_code);
        end
        for (index = 0; index < BF16_COUNT; index = index + 1) begin
            left_code = bf16_vectors[index][50:19];
            #1;
            if (bf16_result !== bf16_vectors[index][18:0])
                $fatal(1, "BF16 conversion differs index=%0d input=%08x",
                       index, left_code);
        end

        repeat (3) @(negedge clk);
        rst_n = 1;
        @(negedge clk);
        rsqrt_out_ready = 1;
        for (index = 0; index < RSQRT_COUNT; index = index + 1) begin
            while (!rsqrt_in_ready) @(negedge clk);
            argument_code = rsqrt_vectors[index][65:34];
            rsqrt_in_valid = 1;
            @(negedge clk);
            rsqrt_in_valid = 0;
            cycles = 0;
            while (!rsqrt_out_valid) begin
                @(negedge clk);
                cycles = cycles + 1;
                if (cycles > 40)
                    $fatal(1, "reciprocal-square-root timeout index=%0d",
                           index);
            end
            if ({rsqrt_result_error, rsqrt_result_code} !==
                rsqrt_vectors[index][33:0])
                $fatal(1, "reciprocal square root differs index=%0d input=%08x",
                       index, argument_code);
            @(negedge clk);
        end
        $display("PASS: FP32 RTL differential add=5000 multiply=5000 bf16=5000 rsqrt=2000 seed=5157454e33524d53");
        $finish;
    end
endmodule
