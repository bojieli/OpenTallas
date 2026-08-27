`timescale 1ns/1ps
// Small, synthesizable decoder used at the numeric boundary.  The public
// reference exposes exact classification and a fixed-point DV representation;
// target-format macro implementations may replace the arithmetic behind this
// contract without changing exceptional-value policy.
module ot_format_decode (
    input  wire [3:0]  mode,       // 0 INT_DV, 1 MXFP4, 2 FP8, 3 BF16
    input  wire [15:0] code,
    output reg         finite,
    output reg         zero,
    output reg         nan,
    output reg         infinity,
    output reg         negative,
    output reg signed [31:0] value_q16,
    output reg signed [15:0] mantissa,
    output reg signed [8:0]  exponent
);
    reg [7:0] fp8;
    reg [7:0] bf8;
    reg [2:0] frac3;
    reg [3:0] exp4;
    reg [7:0] mag_q2;
    integer unbiased;

    always @* begin
        finite = 1'b0;
        zero = 1'b0;
        nan = 1'b0;
        infinity = 1'b0;
        negative = 1'b0;
        value_q16 = 32'sd0;
        mantissa = 16'sd0;
        exponent = 9'sd0;
        fp8 = code[7:0];
        bf8 = code[14:7];
        frac3 = fp8[2:0];
        exp4 = fp8[6:3];
        mag_q2 = 8'd0;
        unbiased = 0;
        case (mode)
            4'd0: begin // signed integer DV value in low byte
                finite = 1'b1;
                negative = code[7];
                value_q16 = $signed({{24{code[7]}},code[7:0]}) <<< 16;
                mantissa = $signed({{8{code[7]}},code[7:0]});
                exponent = 0;
                zero = (code[7:0] == 8'h00);
            end
            4'd1: begin // E2M1 nibble, represented exactly in Q2
                finite = 1'b1;
                negative = code[3];
                case (code[2:0])
                    3'b000: mag_q2 = 8'd0;
                    3'b001: mag_q2 = 8'd2;  // 0.5
                    3'b010: mag_q2 = 8'd4;  // 1
                    3'b011: mag_q2 = 8'd6;  // 1.5
                    3'b100: mag_q2 = 8'd8;  // 2
                    3'b101: mag_q2 = 8'd12; // 3
                    3'b110: mag_q2 = 8'd16; // 4
                    default: mag_q2 = 8'd24; // 6
                endcase
                if (mag_q2 == 0) begin
                    zero = 1'b1;
                    negative = 1'b0; // canonicalize negative zero
                end
                if (negative) begin
                    value_q16 = -($signed({23'b0,1'b0,mag_q2}) <<< 14);
                    mantissa = -$signed({7'b0,1'b0,mag_q2});
                end else begin
                    value_q16 = $signed({23'b0,1'b0,mag_q2}) <<< 14;
                    mantissa = $signed({7'b0,1'b0,mag_q2});
                end
                exponent = -2;
            end
            4'd2: begin // FP8 E4M3FN (finite-only)
                negative = fp8[7];
                if (exp4 == 0) begin
                    if (frac3 == 0) begin
                        finite = 1'b1;
                        zero = 1'b1;
                        negative = 1'b0;
                    end else begin
                        finite = 1'b1;
                        // subnormal: frac * 2^-9, represented by mantissa
                        // and exponent rather than a lossy integer conversion.
                        mantissa = negative ? -$signed({12'b0,1'b0,frac3}) :
                                              $signed({12'b0,1'b0,frac3});
                        exponent = -9;
                    end
                end else if (exp4 == 4'hf && frac3 >= 3'b110) begin
                    nan = 1'b1;
                end else begin
                    finite = 1'b1;
                    unbiased = $signed({27'b0,1'b0,exp4}) - 32'sd7;
                    mantissa = negative ? -$signed({12'b0,1'b1,frac3}) :
                                          $signed({12'b0,1'b1,frac3});
                    // The hidden bit is scaled as 1.frac = (8+frac)/8.
                    exponent = $signed(unbiased[8:0]) - 9'sd3;
                end
            end
            4'd3: begin // BF16 classification; code[15:0] is BF16
                negative = code[15];
                if (code[14:7] == 8'hff) begin
                    if (code[6:0] == 0)
                        infinity = 1'b1;
                    else
                        nan = 1'b1;
                end else begin
                    finite = 1'b1;
                    zero = (code[14:0] == 0);
                    if (zero)
                        negative = 1'b0;
                    // Preserve the canonical BF16 bits for a vector macro.
                    value_q16 = {code,16'b0};
                    mantissa = $signed({8'b0,1'b0,code[6:0]});
                    exponent = $signed({1'b0,code[14:7]}) - 9'sd127;
                end
            end
            default: begin
                nan = 1'b1; // reserved profile is an illegal numeric value
            end
        endcase
    end
endmodule
