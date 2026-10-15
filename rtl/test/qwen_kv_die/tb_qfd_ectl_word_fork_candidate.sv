`timescale 1ns/1ps
module tb_qfd_ectl_word_fork_candidate;
    parameter integer MUT = 0;
    reg ck = 0;
    reg rst_n = 0;
    reg [511:0] row_a, row_b;
    reg [15:0] cl, e0, e1;
    reg [518:0] q;
    wire [1558:0] t0, t1;
    wire [15:0] eo0, eo1;
    reg [1558:0] expected;
    integer i,j;
    qfd_ectl_word_fork_candidate #(.MUT_ROW_SWAP(MUT)) dut (.*);
    always #5 ck = ~ck;
    initial begin
        row_a=0;row_b=0;cl=0;q=0;e0=0;e1=0;
        @(posedge ck); #1;
        if ({t0,t1,eo0,eo1} !== 0) $fatal(1,"RESET_FAIL");
        for(i=0;i<257;i=i+1) begin
            @(negedge ck);
            rst_n=(i!=128);
            for(j=0;j<16;j=j+1) begin
                row_a[j*32+:32]=$random;
                row_b[j*32+:32]=$random;
                q[j*32+:32]=$random;
            end
            q[518:512]=$random;cl=$random;e0=$random;e1=$random;
            expected=rst_n ? {q,cl[15:4],row_b,row_a,cl[3:0]} : 1559'd0;
            @(posedge ck); #1;
            if(t0 !== expected || t1 !== expected || eo0 !== (rst_n?e0:16'd0) || eo1 !== (rst_n?e1:16'd0)) begin
                $display("ECTL_FORK_MUTANT_DETECTED cycle=%0d MUT=%0d",i,MUT);
                $fatal(1,"FORK_EDGE_MISMATCH");
            end
        end
        $display("ECTL_FORK_CANDIDATE_PASS 257 edges including reset, two copies and exact t/e packing");
        $finish;
    end
endmodule
