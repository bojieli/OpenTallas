`timescale 1ns/1ps
module tb_hdc_qwen_m5_result_tokens;
    reg clk=0, rst_n=0, arm=0, result_valid=0, result_last=0;
    always #5 clk=~clk;
    reg [639:0] result=0;
    reg [15:0] row_base=0;
    wire tok_valid, done, fault, busy;
    wire [2:0] tok_slot;
    wire [15:0] tok;
    integer s, seen=0;
    ot_hdc_qwen_m5_result_tokens #(.G(2),.W(2),.NW(16)) dut (
        .clk(clk),.rst_n(rst_n),.arm(arm),.result_valid(result_valid),
        .result_last(result_last),.result(result),.row_base(row_base),
        .tok_valid(tok_valid),.tok_slot(tok_slot),.tok(tok),.done(done),
        .fault(fault),.busy(busy));
    always @(posedge clk) if (tok_valid) begin
        if (tok_slot!==seen || tok!==(seen==0 ? 16'd202 : 16'd101))
            $fatal(1,"running max mismatch slot=%0d token=%0d beat=%0d",tok_slot,tok,seen);
        seen<=seen+1;
    end
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        @(negedge clk); arm=1;
        @(negedge clk); arm=0;
        // Early chunk is best for slots 1..4. Slot 0 improves in chunk 2.
        result=0; row_base=100;
        for (s=0;s<5;s=s+1) result[(s*4+1)*32 +:32]=32'h40a00000; // 5
        result_valid=1;
        @(negedge clk);
        result=0; row_base=200;
        result[(0*4+2)*32 +:32]=32'h41300000; // 11
        for (s=1;s<5;s=s+1) result[(s*4+2)*32 +:32]=32'h40400000; // 3
        @(negedge clk);
        result=0; row_base=300;
        for (s=0;s<5;s=s+1) result[(s*4+0)*32 +:32]=32'h40800000; // 4
        for (s=1;s<5;s=s+1) result[(s*4+1)*32 +:32]=32'h40a00000; // equal 5, later row loses
        result_last=1;
        @(negedge clk); result_valid=0; result_last=0;
        wait(done);
        @(negedge clk);
        if (fault || seen!=5 || busy) $fatal(1,"retirement failed fault=%b seen=%0d busy=%b",fault,seen,busy);
        $display("PASS Qwen m5 running argmax: 3 vocabulary chunks, five exact slot winners, lower-row tie rule");
        $finish;
    end
    initial begin #2000; $fatal(1,"running argmax timeout"); end
endmodule
