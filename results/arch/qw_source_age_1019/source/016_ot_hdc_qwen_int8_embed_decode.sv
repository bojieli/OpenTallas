`timescale 1ns/1ps
// Exact FP32 value of a signed INT8 embedding code times a normal BF16 row
// scale. The product has at most 15 significant bits, so no rounding is
// needed in the deployed range. Invalid or overflowing scales fail closed.
module ot_hdc_qwen_int8_embed_decode (
    input  wire [7:0]  code,
    input  wire [15:0] scale,
    output reg  [31:0] value,
    output reg         fault
);
    reg [7:0] mag;
    reg [15:0] product;
    reg [4:0] msb;
    reg [31:0] normalized;
    reg [9:0] exponent;
    integer i;
    always @* begin
        mag = code[7] ? (~code + 8'd1) : code;
        product = mag * {1'b1, scale[6:0]};
        msb = 0;
        for (i = 0; i < 16; i = i + 1)
            if (product[i]) msb = i[4:0];
        normalized = {16'd0, product} << (23 - msb);
        exponent = {2'd0, scale[14:7]} + {5'd0, msb} - 10'd7;
        fault = (scale[14:7] == 0 || scale[14:7] == 8'hff ||
                 (mag != 0 && exponent > 10'd254));
        value = (mag == 0 || fault) ? 32'd0 :
                {code[7] ^ scale[15], exponent[7:0], normalized[22:0]};
    end
endmodule
