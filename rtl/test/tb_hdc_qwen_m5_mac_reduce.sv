`timescale 1ns/1ps
module tb_hdc_qwen_m5_mac_reduce;
    reg clk=0, rst_n=0, valid=0, first=0, last_k=0;
    always #5 clk=~clk;
    wire out_valid, fault;
    wire [639:0] result;
    integer s, seen=0;
    function automatic [31:0] fbits(input integer x);
        integer e, mantissa;
        begin
            e=0;
            while ((1 << (e+1)) <= x) e=e+1;
            mantissa=(x << (23-e)) - (1 << 23);
            fbits={1'b0, (8'd127 + e), mantissa[22:0]};
        end
    endfunction
    ot_hdc_qwen_m5_mac_reduce #(.G(2),.W(2),.IL(8)) dut (
        .clk(clk),.rst_n(rst_n),.valid(valid),.first(first),.last_k(last_k),
        .split_log2(2'd1),.weight_fp32({4{32'h3f800000}}),
        .activation_fp32({fbits(5),fbits(5),fbits(4),fbits(4),fbits(3),fbits(3),
                          fbits(2),fbits(2),fbits(1),fbits(1)}),
        .row_scale_bf16({16'h4000,16'h3f00,16'h4000,16'h3f00}),
        .out_valid(out_valid),.result(result),.fault(fault)
    );
    always @(posedge clk) if (out_valid) begin
        seen=seen+1;
        for (s=0;s<5;s=s+1)
            if (result[(s*4+0)*32 +: 32] !== fbits(2*(s+1)) ||
                result[(s*4+1)*32 +: 32] !== fbits(8*(s+1)))
                $fatal(1,"slot %0d MAC/reduce/scale mismatch %h %h",s,
                       result[(s*4+0)*32 +: 32],result[(s*4+1)*32 +: 32]);
    end
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        repeat (8) begin @(negedge clk); valid=1; first=1; end
        repeat (8) begin @(negedge clk); valid=1; first=0; last_k=1; end
        @(negedge clk); valid=0; last_k=0;
        repeat (40) @(negedge clk);
        if (fault || seen != 8) $fatal(1,"m5 full arithmetic failed fault=%b seen=%0d",fault,seen);
        $display("PASS Qwen m5 shared-issue MAC/reduce/scale: 5 slots, 8 exact result cycles");
        $finish;
    end
endmodule
