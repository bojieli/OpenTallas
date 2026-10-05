`timescale 1ns/1ps
module tb_hdc_qwen_int8_arith;
    localparam integer N = 1024;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    reg pv = 0, sv = 0;
    reg [7:0] code = 0;
    reg [15:0] x = 0, scale = 0;
    reg [31:0] sum = 0;
    wire pvo, svo, pf, sf;
    wire [31:0] product, scaled;
    ot_hdc_qwen_int8_arith dut (
        .clk(clk), .rst_n(rst_n), .product_valid(pv),
        .code_lo(code[3:0]), .code_hi(code[7:4]), .x_bf16(x),
        .product_out_valid(pvo), .product(product), .product_fault(pf),
        .scale_valid(sv), .completed_sum(sum), .row_scale_bf16(scale),
        .scaled_out_valid(svo), .scaled_result(scaled), .scale_fault(sf)
    );
    reg [135:0] vectors [0:N-1];
    reg [31:0] expected_p [0:4], expected_s [0:4];
    reg expected_v [0:4];
    integer i, j, checked = 0, errors = 0;
    reg [135:0] word;
    initial begin
        $readmemh("vectors.mem", vectors);
        for (j = 0; j < 5; j = j + 1) begin
            expected_v[j] = 0; expected_p[j] = 0; expected_s[j] = 0;
        end
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (i = 0; i < N + 7; i = i + 1) begin
            if (i < N) begin
                word = vectors[i];
                {code, x, expected_p[0], sum, scale, expected_s[0]} = word;
                pv = 1; sv = 1; expected_v[0] = 1;
            end else begin
                pv = 0; sv = 0; expected_v[0] = 0;
            end
            @(posedge clk);
            #1;
            if (pvo !== expected_v[4] || svo !== expected_v[4]) begin
                $display("valid mismatch index=%0d product=%b scale=%b expected=%b", i, pvo, svo, expected_v[4]);
                errors = errors + 1;
            end
            if (expected_v[4]) begin
                checked = checked + 1;
                if (product !== expected_p[4] || scaled !== expected_s[4] || pf || sf) begin
                    if (errors < 10)
                        $display("mismatch index=%0d product=%h expected=%h scaled=%h expected=%h faults=%b%b",
                                 i - 4, product, expected_p[4], scaled, expected_s[4], pf, sf);
                    errors = errors + 1;
                end
            end
            for (j = 4; j > 0; j = j - 1) begin
                expected_v[j] = expected_v[j-1];
                expected_p[j] = expected_p[j-1];
                expected_s[j] = expected_s[j-1];
            end
            @(negedge clk);
        end
        $display("QWEN_INT8 checked=%0d errors=%0d", checked, errors);
        if (checked != N || errors != 0) $fatal(1, "Qwen INT8 arithmetic failed");
        $display("PASS");
        $finish;
    end
endmodule
