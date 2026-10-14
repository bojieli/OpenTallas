`timescale 1ns/1ps
module tb_s81_startup_barrier;
    parameter integer MUT=0;
    reg clk=0, reset_n=0;
    reg [2:0] released=0;
    wire ready;
    always #0.416667 clk=~clk;
    ot_s81_startup_barrier #(.N(3), .MUT_EARLY(MUT)) dut (.*);
    task automatic expect_low;
        #0.01;
        if (ready) $fatal(1,"STARTUP_EARLY ack mask=%b",released);
    endtask
    task automatic release_and_check;
        integer i;
        begin
            @(negedge clk); released=3'b111;
            for(i=1;i<=4;i=i+1) begin
                @(posedge clk); #0.01;
                if(ready !== (i==4)) $fatal(1,"STARTUP_COUNT edge=%0d ready=%b",i,ready);
            end
        end
    endtask
    initial begin
        expect_low();
        @(negedge clk); reset_n=1; expect_low();
        repeat(7) @(posedge clk);
        @(negedge clk); released=3'b001; expect_low();
        repeat(9) @(posedge clk);
        @(negedge clk); released=3'b011; expect_low();
        release_and_check();
        // A sub-cycle child reset must kill ready and start a fresh four-edge epoch.
        @(negedge clk); #0.05; released[1]=0; expect_low();
        #0.05; released[1]=1; expect_low();
        for(integer i=1;i<=4;i=i+1) begin
            @(posedge clk); #0.01;
            if(ready !== (i==4)) $fatal(1,"STARTUP_REARM edge=%0d",i);
        end
        @(negedge clk); #0.05; reset_n=0; expect_low();
        released=0;
        @(negedge clk); reset_n=1; expect_low();
        release_and_check();
        $display("STARTUP_BARRIER PASS staggered_ack epoch_rearm async_assert four_edges");
        $finish;
    end
    initial begin #1000; $fatal(1,"STARTUP_TIMEOUT"); end
endmodule
