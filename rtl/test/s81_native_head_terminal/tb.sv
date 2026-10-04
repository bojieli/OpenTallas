`timescale 1ns/1ps
module tb;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,start=0,cancel=0,in_valid=0,logit_ready=0,done_ready=0;
    reg [1:0] rank=2;
    reg [46:0] start_owner=47'h1234,in_owner=47'h1234;
    reg [16:0] in_row;
    reg [31:0] root4096=32'h3f000000,root1024=32'h3f000000;
    wire ready,in_ready,logit_valid,logit_poison,done_valid,token_valid,fault;
    wire [46:0] logit_owner,done_owner;
    wire [16:0] logit_row,best_row;
    wire [31:0] logit_bits,best_bits;
    s81_native_head_terminal #(.OPT_NATIVE_HEAD(1)) dut(.*);
    integer got=0,n,edges=0;
    // Finite protocol bound: full row loop consumes2 edges/row; stalls60,
    // four terminals/control suffixes fit200. This is not a wall/build cap.
    always @(posedge clk) begin
        edges=edges+1;
        if(edges>3*32320+200) $fatal(1,"finite source protocol progress");
    end
    reg scoreboard=1;
    always @(posedge clk) if(logit_valid && logit_ready) begin
        if(logit_owner!=47'h1234) $fatal(1,"owner mismatch");
        if(scoreboard) begin
            if(logit_row!=64640+got || logit_poison) $fatal(1,"row/poison");
            if(logit_bits!=((got==17||got==32319)?32'h40000000:32'h3f800000)) $fatal(1,"native arithmetic");
        end
        got=got+1;
    end
    task begin_op;
        begin @(negedge clk);start=1;@(negedge clk);start=0;end
    endtask
    task send_row(input integer r,input [31:0] a,input [31:0] b);
        begin @(negedge clk);in_valid=1;in_row=r;root4096=a;root1024=b;
            @(posedge clk);while(!in_ready) @(posedge clk);
            @(negedge clk);in_valid=0;
        end
    endtask
    task retire;
        begin wait(done_valid);@(negedge clk);done_ready=1;@(negedge clk);done_ready=0;
            if(!ready) $fatal(1,"terminal retirement");end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;begin_op();
        // Held ACK fills all16 seats, then actual credit release admits suffix.
        fork
            begin for(n=0;n<32320;n=n+1)
                send_row(64640+n,32'h3f000000,(n==17||n==32319)?32'h3fc00000:32'h3f000000);end
            begin repeat(60) @(negedge clk);
                if(dut.owned!=16 || in_ready) $fatal(1,"finite seat hold");
                logit_ready=1;end
        join
        wait(done_valid);#1;
        if(got!=32320 || !token_valid || best_row!=64657 || best_bits!=32'h40000000 || fault)
            $fatal(1,"full native row/tie terminal");
        repeat(3) @(negedge clk);if(!done_valid) $fatal(1,"held terminal");retire();
        // Wrong owner is rejected; it cannot manufacture a row or a token.
        scoreboard=0;begin_op();@(negedge clk);in_valid=1;in_owner=47'h1235;in_row=64640;
        #1;if(in_ready) $fatal(1,"stale identity");
        @(negedge clk);in_valid=0;in_owner=47'h1234;
        wait(done_valid);if(!fault || token_valid || dut.accepted!=0) $fatal(1,"stale identity");retire();
        // Native nonfinite fault drains accepted ownership without a token.
        begin_op();send_row(64640,32'h7f800000,32'd0);
        wait(fault);wait(logit_valid);wait(done_valid);
        if(token_valid || dut.owned!=0) $fatal(1,"nonfinite ownership");retire();
        // Cancel must hold the accepted seat until a real logit ACK.
        begin_op();logit_ready=0;send_row(64640,32'h80000000,32'd0);
        @(negedge clk);cancel=1;@(negedge clk);cancel=0;
        repeat(15) @(negedge clk);
        if(done_valid || dut.owned!=1 || !logit_valid || logit_bits!=0) $fatal(1,"cancel/zero/ACK");
        logit_ready=1;wait(done_valid);if(token_valid) $fatal(1,"cancel token");retire();
        $display("PASS_NATIVE_HEAD_TERMINAL_FULL32320_TIES_HOLD_STALE_NONFINITE_CANCEL");$finish;
    end
endmodule
