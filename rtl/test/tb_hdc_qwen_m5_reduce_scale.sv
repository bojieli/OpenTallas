`timescale 1ns/1ps
module tb_hdc_qwen_m5_reduce_scale;
    reg clk=0, rst_n=0, valid=0;
    always #5 clk=~clk;
    reg [1:0] split_log2=1;
    reg [639:0] partial_sum=0;
    wire [639:0] result;
    wire out_valid, fault;
    integer s,l, seen=0;
    function automatic [31:0] fbits(input integer x);
        integer e, mantissa;
        begin
            e=0;
            while ((1 << (e+1)) <= x) e=e+1;
            mantissa=(x << (23-e)) - (1 << 23);
            fbits={1'b0, (8'd127 + e), mantissa[22:0]};
        end
    endfunction
    ot_hdc_qwen_m5_reduce_scale #(.G(2),.W(2)) dut (
        .clk(clk), .rst_n(rst_n), .valid(valid), .split_log2(split_log2),
        .partial_sum(partial_sum), .row_scale_bf16({16'h4040,16'h4000,16'h4040,16'h4000}),
        .out_valid(out_valid), .result(result), .fault(fault)
    );
    always @(posedge clk) if (out_valid) begin
        seen=seen+1;
        for (s=0;s<5;s=s+1) begin
            if (result[(s*4+0)*32 +: 32] !== fbits(6*(s+1)) ||
                result[(s*4+1)*32 +: 32] !== fbits(9*(s+1)))
                $fatal(1,"slot %0d reduction/scale mismatch: %h %h", s,
                       result[(s*4+0)*32 +: 32],result[(s*4+1)*32 +: 32]);
        end
    end
    initial begin
        for (s=0;s<5;s=s+1)
            for (l=0;l<2;l=l+1) begin
                partial_sum[(s*4+l)*32 +: 32]=fbits(s+1);
                partial_sum[(s*4+2+l)*32 +: 32]=fbits(2*(s+1));
            end
        repeat (3) @(negedge clk); rst_n=1;
        @(negedge clk); valid=1;
        @(negedge clk); valid=0;
        repeat (20) @(negedge clk);
        if (fault || seen != 1) $fatal(1,"m5 reduction failed: fault=%b seen=%0d",fault,seen);
        $display("PASS Qwen m5 five-way reduction and post-sum row scale: 5 slots, 0 mismatches");
        $finish;
    end
endmodule
