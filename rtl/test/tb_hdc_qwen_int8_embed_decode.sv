`timescale 1ns/1ps
module tb_hdc_qwen_int8_embed_decode;
    reg [7:0] code;
    reg [15:0] scale;
    wire [31:0] value;
    wire fault;
    reg [56:0] vectors [0:2047];
    reg [1023:0] path;
    integer n, i, mismatches;
    ot_hdc_qwen_int8_embed_decode dut (.code(code), .scale(scale), .value(value), .fault(fault));
    initial begin
        if (!$value$plusargs("VEC=%s", path)) $fatal(1, "missing VEC");
        if (!$value$plusargs("N=%d", n)) $fatal(1, "missing N");
        $readmemh(path, vectors, 0, n - 1);
        mismatches = 0;
        for (i = 0; i < n; i = i + 1) begin
            {code, scale} = vectors[i][23:0];
            #1;
            if (value !== vectors[i][55:24] || fault !== vectors[i][56]) begin
                mismatches = mismatches + 1;
                if (mismatches < 10)
                    $display("MISMATCH i=%0d code=%02x scale=%04x got=%08x/%0d expected=%08x/%0d",
                             i, code, scale, value, fault, vectors[i][55:24], vectors[i][56]);
            end
        end
        $display("INT8_EMBED_DECODE vectors=%0d mismatches=%0d", n, mismatches);
        if (mismatches) $fatal(1, "decode mismatch");
        $finish;
    end
endmodule
