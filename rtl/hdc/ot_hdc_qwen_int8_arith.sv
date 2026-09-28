`timescale 1ns/1ps
// Qwen O4 weight arithmetic. Two four-bit ROM select cells hold one signed
// INT8 code (low nibble first). Decode it exactly to BF16 before the existing
// five-cycle lane multiplier. The scale path consumes the *completed* FP32
// K-split tree result; callers must place it before writeback, argmax, norm
// multiplication and TP fold. Both paths accept one item every cycle.
module ot_hdc_qwen_int8_arith (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        product_valid,
    input  wire [3:0]  code_lo,
    input  wire [3:0]  code_hi,
    input  wire [15:0] x_bf16,
    output wire        product_out_valid,
    output wire [31:0] product,
    output wire        product_fault,
    input  wire        scale_valid,
    input  wire [31:0] completed_sum,
    input  wire [15:0] row_scale_bf16,
    output wire        scaled_out_valid,
    output wire [31:0] scaled_result,
    output wire        scale_fault
);
    wire [7:0] code = {code_hi, code_lo};
    wire sign = code[7];
    wire [7:0] magnitude = sign ? (~code + 8'd1) : code;
    reg [2:0] msb;
    integer bit_index;
    always @* begin
        msb = 3'd0;
        for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
            if (magnitude[bit_index]) msb = bit_index[2:0];
    end
    wire [7:0] normalized = magnitude << (3'd7 - msb);
    wire [15:0] code_bf16 = (magnitude == 8'd0) ? 16'd0 :
                            {sign, (8'd127 + {5'd0, msb}), normalized[6:0]};
    reg [4:0] pv, sv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pv <= 0; sv <= 0; end
        else begin
            pv <= {pv[3:0], product_valid};
            sv <= {sv[3:0], scale_valid};
        end
    end
    assign product_out_valid = pv[4];
    assign scaled_out_valid = sv[4];
    ot_hdc_bmul u_product (
        .clk(clk), .rst_n(rst_n), .v(product_valid),
        .a({code_bf16, 16'd0}), .b({x_bf16, 16'd0}),
        .y(product), .fault(product_fault)
    );
    ot_hdc_fmul u_scale (
        .clk(clk), .rst_n(rst_n), .v(scale_valid),
        .a(completed_sum), .b({row_scale_bf16, 16'd0}),
        .y(scaled_result), .fault(scale_fault)
    );
endmodule
