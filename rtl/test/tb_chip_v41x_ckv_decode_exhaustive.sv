`timescale 1ns/1ps
module tb_chip_v41x_ckv_decode_exhaustive;
    reg [3:0] code;
    reg [7:0] scale;
    wire [7:0] fp8;
    wire [31:0] fp32;
    wire poison;
    reg [39:0] expected [0:4095];
    integer s, c, errors, checked;
    ot_chip_v41x_ckv_fp4_decode dut (
        .code(code), .scale(scale), .fp8(fp8), .fp32(fp32), .poison(poison));
    initial begin
        $readmemh("tests/fixtures/v41_ckv_selected/decode_pairs.hex", expected);
        errors=0; checked=0;
        for (s=0;s<256;s=s+1) begin
            for (c=0;c<16;c=c+1) begin
                scale=8'(s); code=4'(c); #1;
                if ({fp32,fp8} !== expected[16*s+c] ||
                    poison !== ((scale[6:0]==7'h7f))) begin
                    if (errors<20) $display("BAD scale=%h code=%h got=%h/%h expected=%h",
                                             scale,code,fp32,fp8,expected[16*s+c]);
                    errors=errors+1;
                end else checked=checked+1;
            end
        end
        $display("DECODE_EXHAUSTIVE checked=%0d errors=%0d",checked,errors);
        if (errors==0 && checked==4096) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
