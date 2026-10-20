`timescale 1ns/1ps
module tb_hbm_parent_station32;
    parameter integer W = 328;
    localparam integer G = (W+23)/24;
    reg ck=0, rst_n=1;
    reg [W-1:0] i;
    wire [W-1:0] o;
    wire [G-1:0] ready;
    wire ck_o;
    integer age=0, checks=0, epoch, cycle, j;
    reg [W-1:0] before_o;
    ot_hbm_parent_station32 #(.W(W)) dut(.*);
    task tick;
        begin
            before_o=o;
            for(j=0;j<W;j=j+1) i[j]=$random;
            #2;
            if(o!==before_o) $fatal(1,"causality: data changed without clock");
            if(ck_o!==0) $fatal(1,"forwarded low clock");
            ck=1; #1;
            if(ck_o!==1) $fatal(1,"forwarded high clock");
            age=age+1;
            if(age<3) begin
                if(o!=={W{1'b0}} || ready!=={G{1'b0}}) $fatal(1,"early reset release age%0d",age);
            end else begin
                if(o!==i || ready!=={G{1'b1}}) $fatal(1,"one-hop/first-valid age%0d",age);
            end
            ck=0; #1;
            if(ck_o!==0) $fatal(1,"forwarded falling clock");
            checks=checks+1;
        end
    endtask
    initial begin
        i={W{1'b1}};
        // No initial-state assumption. A real asynchronous assertion must clear
        // every data and ready state before any clock edge can occur.
        for(epoch=0;epoch<50;epoch=epoch+1) begin
            #1; rst_n=0; age=0; #1;
            if(o!=={W{1'b0}} || ready!=={G{1'b0}}) $fatal(1,"async reset epoch%0d",epoch);
            // Hold arbitrary input changes under reset, without clock edges.
            i=~i; #1;
            if(o!=={W{1'b0}}) $fatal(1,"reset did not mask data");
            rst_n=1;
            for(cycle=0;cycle<5+(epoch%31);cycle=cycle+1) tick;
            // In-flight reset while source clock is high, not only at a safe edge.
            ck=1; #1; rst_n=0; #1;
            if(o!=={W{1'b0}} || ready!=={G{1'b0}}) $fatal(1,"inflight async cancellation");
            ck=0; #1;
        end
        $display("PASS W=%0d epochs=%0d checks=%0d first-valid3 steady-hop1 causal/reset/forward-clock",W,epoch,checks);
        $finish;
    end
endmodule
