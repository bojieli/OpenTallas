`timescale 1ns/1ps
module tb_smh_static_stage256;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg [255:0] d=0;
 wire [255:0] q,reference_q;
 ot_smh_static_stage256 #(.MUT(MUT)) dut(.*);
 ot_hbm_accel_smh_kreg #(.W(256)) original(.clk(clk),.rst_n(1'b1),.en(1'b1),.d(d),.q(reference_q));
 integer i,k;
 initial begin
   for(i=0;i<4096;i=i+1)begin
     @(negedge clk);
     for(k=0;k<8;k=k+1)d[32*k+:32]=32'(i*997+k*5437);
     if(i<256)d=256'd1<<i;
     @(posedge clk);#1;
     if(q!==reference_q)$fatal(1,"STATIC STAGE256 original register bit/cycle mismatch %0d",i);
   end
   $display("STATIC STAGE256 EXACT PASS 4096 II1 onecaptureedge originalRTL all256bits");$finish;
 end
endmodule
