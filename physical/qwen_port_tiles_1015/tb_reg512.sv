`timescale 1ns/1ps
module tb_reg512; parameter integer MUT=0;
 reg ck=0; always #1 ck=~ck; reg [511:0] d, prev; wire [511:0] q; integer c=0,e=0,k;
 qfd_slab_reg512 #(.MUT(MUT)) u(.ck(ck),.d(d),.q(q));
 // q must hold the value captured at the last rising edge after d changes at the falling edge
 always @(negedge ck) begin prev=d; for(k=0;k<16;k=k+1) d[32*k+:32]=$random; c=c+1; #0.25; if(c>2 && q!==prev) e=e+1;
   if(c==2000) begin $display("REG512 MUT=%0d checks=%0d mismatches=%0d %s",MUT,c-2,e,e==0?"PASS":"FAIL"); $finish; end end
endmodule
