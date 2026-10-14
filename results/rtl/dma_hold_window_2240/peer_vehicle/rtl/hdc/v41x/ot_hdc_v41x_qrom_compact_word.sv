`timescale 1ns/1ps
// Combinational QE ROM-port decode after the synchronous mask-ROM read.
// FP8 ROM: 16 lanes x {signed 16-bit exponent, 32 E4M3 codes} = 4352 bits.
// FP4 ROM: 16 lanes x {signed 16-bit exponent, 32 packed E2M1 nibbles}
//          = 2304 bits. One physical FP4 word yields the same 4352-bit
//          logical QE word as ot_hdc_qstream's HBM window expansion.
// The caller registers fp4 alongside its one-cycle ROM data. This module
// adds no read latency and does not imply that either source has a free port.
module ot_hdc_v41x_qrom_compact_word (
    input  wire          fp4,
    input  wire [4351:0] fp8_word,
    input  wire [2303:0] fp4_word,
    output reg  [4351:0] qe_word
);
    integer lane, code;
    always @(*) begin
        if (!fp4) qe_word=fp8_word;
        else begin
            qe_word='0;
            for (lane=0;lane<16;lane=lane+1) begin
                for (code=0;code<32;code=code+1)
                    qe_word[lane*272+8*code +: 4]=fp4_word[lane*144+4*code +: 4];
                qe_word[lane*272+256 +: 16]=fp4_word[lane*144+128 +: 16];
            end
        end
    end
endmodule
