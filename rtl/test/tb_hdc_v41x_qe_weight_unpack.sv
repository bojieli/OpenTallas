`timescale 1ns/1ps
module tb_hdc_v41x_qe_weight_unpack #(
    parameter integer FP4=0,
    parameter integer SW=FP4 ? 34 : 66
);
    localparam integer BL=64, QLB=272;
    reg [255:0] sectors [0:2*SW-1];
    reg [BL*QLB-1:0] expected [0:1];
    reg [BL*33*8-1:0] packed_word;
    wire [BL*QLB-1:0] qe_word;
    integer w,s;
    ot_hdc_v41x_qe_weight_unpack #(.BL(BL),.QLB(QLB)) dut (
        .fp4(FP4[0]),.packed_word(packed_word),.qe_word(qe_word));
    initial begin
        $readmemh("sectors.hex",sectors);
        $readmemh("qe_expected.hex",expected);
        for (w=0;w<2;w=w+1) begin
            packed_word='0;
            for (s=0;s<SW;s=s+1)
                packed_word[s*256 +: 256]=sectors[w*SW+s];
            #1;
            if (qe_word !== expected[w]) $fatal(1,"QE unpack mismatch word=%0d fp4=%0d",w,FP4);
        end
        $display("QE_WEIGHT_UNPACK_PASS fp4=%0d words=2 lanes=64",FP4);
        $finish;
    end
endmodule
