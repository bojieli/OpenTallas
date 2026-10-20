`timescale 1ns/1ps
module tb_guarded_mux;
    parameter integer MUT = 0;
    localparam integer W = 148;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg [W-1:0] a=0,b=0;
    reg [1:0] sel=0;
    wire [W-1:0] y;
    ot_s81ph_native_guarded_mux #(.W(W), .MUT(MUT)) dut(.*);
    reg r0=0,r1=0;
    reg [1:0] ss0=0,ss1=0;
    reg [W-1:0] aa0,bb0,aa1,bb1,gold;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r0<=0;r1<=0;end
        else begin r0<=1;r1<=r0;end
    end
    always @(posedge clk or negedge r1) begin
        if (!r1) begin ss0<=0;ss1<=0;end
        else begin ss0<=sel;ss1<=ss0;end
    end
    always @(posedge clk) begin
        aa0<=a;bb0<=b;aa1<=aa0;bb1<=bb0;
        gold <= (aa1 & {W{ss1[0]}}) | (bb1 & {W{ss1[1]}});
    end
    integer cycle,k,checks=0;
    initial begin
        for(cycle=0;cycle<1400;cycle=cycle+1) begin
            @(negedge clk);
            rst_n = !(cycle<4 || cycle==300 || (cycle>=501 && cycle<504));
            for(k=0;k<W;k=k+1) begin a[k]=$urandom_range(0,1);b[k]=$urandom_range(0,1);end
            sel=cycle%4;
            @(posedge clk);#1;
            if(cycle>=3) begin
                if(y !== gold) begin
                    $display("GUARDED_MUX FAIL MUT=%0d cycle=%0d got=%h gold=%h",MUT,cycle,y,gold);
                    $fatal(1,"causal guarded mux mismatch");
                end
                checks=checks+1;
            end
        end
        $display("GUARDED_MUX PASS MUT=%0d checks=%0d",MUT,checks);
        $finish;
    end
endmodule
