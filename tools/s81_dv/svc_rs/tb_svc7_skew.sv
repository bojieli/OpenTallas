`timescale 1ns/1ps
module svc7_skew_case #(parameter integer D=5)(
    input wire clk,rst_n,iv,input wire [20:0] i,
    output reg [31:0] checked=0,errors=0
);
    wire ov;wire [20:0] o;
    ot_s81svc7_skew_sram #(.D(D)) dut(.*);
    reg [20:0] data[0:D-1];
    reg [D-1:0] valid=0;
    integer j;
    always @(posedge clk) begin
        data[0]<=i;
        for(j=1;j<D;j=j+1)data[j]<=data[j-1];
        if(!dut.run_c)valid<=0;
        else begin valid[0]<=iv;for(j=1;j<D;j=j+1)valid[j]<=valid[j-1];end
    end
    integer cyc=0;
    always @(negedge clk) begin
        cyc=cyc+1;
        // Only the initial reset-landing edges precede the port contract.
        // Compare validity on EVERY subsequent edge, including in-flight reset.
        if(cyc>4)begin
            checked=checked+1;
            if(ov!==valid[D-1] || (ov && o!==data[D-1]))begin
                errors=errors+1;
                $display("SVC7_SKEW_MISMATCH D=%0d cyc=%0d v=%b/%b data=%h/%h",D,cyc,ov,valid[D-1],o,data[D-1]);
            end
        end
    end
endmodule

module tb_svc7_skew;
    reg clk=0;always #1 clk=~clk;
    reg rst_n=0,iv=0;reg [20:0] i=0;
    wire [31:0] checked[0:6],errors[0:6];
    genvar n;
    generate for(n=0;n<7;n=n+1)begin:g_case
        localparam integer D=n==0?3:5*n;
        svc7_skew_case #(.D(D)) u(.clk(clk),.rst_n(rst_n),.iv(iv),.i(i),.checked(checked[n]),.errors(errors[n]));
    end endgenerate
    integer cyc=0,j,total=0,checks=0;
    always @(negedge clk) begin
        rst_n=(cyc>=12 && !(cyc>=211 && cyc<217) && !(cyc>=803 && cyc<809));
        iv=rst_n && $urandom_range(0,3)!=0;i=$urandom;
        cyc=cyc+1;
        if(cyc==4000)begin
            for(j=0;j<7;j=j+1)begin total=total+errors[j];checks=checks+checked[j];end
            $display("SVC7_SKEW checks=%0d errors=%0d reset_pulses=3 verdict=%s",checks,total,total==0?"PASS":"FAIL");
            if(total!=0)$fatal(1,"SVC7_SKEW_FAIL");$finish;
        end
    end
endmodule
