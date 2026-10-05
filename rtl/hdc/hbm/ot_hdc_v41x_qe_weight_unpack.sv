`timescale 1ns/1ps
// Unpack the shipped full-shape QE HBM image to the existing QE weight port.
// HBM words are address-major, then 64 bank lanes: FP8 has 32 E4M3 code
// bytes + one UE8M0 scale byte per lane; FP4 has 16 packed E2M1-code bytes
// + one UE8M0 scale byte per lane. The QE accepts 32 code *byte slots* and a
// 10-bit exponent field per 272-bit lane; upper scale bits and lane padding
// are zero. No arithmetic, rounding or scale change occurs here.
module ot_hdc_v41x_qe_weight_unpack #(
    parameter integer BL = 64,
    parameter integer QLB = 272
) (
    input  wire                    fp4,
    input  wire [BL*33*8-1:0]      packed_word,
    output wire [BL*QLB-1:0]      qe_word
);
    genvar l,c;
    generate for (l=0; l<BL; l=l+1) begin : g_lane
        if (QLB < 266) begin : g_bad_width
            assign qe_word[l*QLB +: QLB] = '0;
        end else begin : g_format
            for (c=0; c<32; c=c+1) begin : g_code
                wire [7:0] f8 = packed_word[(l*33+c)*8 +: 8];
                wire [3:0] f4 = packed_word[(l*17+c/2)*8 + (c%2)*4 +: 4];
                assign qe_word[l*QLB+c*8 +: 8] = fp4 ? {4'b0000,f4} : f8;
            end
            assign qe_word[l*QLB+256 +: 10] = fp4 ?
                {2'b00,packed_word[(l*17+16)*8 +: 8]} :
                {2'b00,packed_word[(l*33+32)*8 +: 8]};
            assign qe_word[l*QLB+266 +: QLB-266] = '0;
        end
    end endgenerate
endmodule
