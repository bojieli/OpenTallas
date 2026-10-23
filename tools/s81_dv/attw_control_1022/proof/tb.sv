`timescale 1ns/1ps
module INVx1_ASAP7_75t_R(input wire A,output wire Y);assign Y=~A;endmodule
module ot_sram_1r1w_32x128_m1(input wire clk,r_ce_in,input wire[4:0]r_addr_in,output reg[127:0]rd_out,input wire w_ce_in,input wire[4:0]w_addr_in,input wire[127:0]wd_in,w_mask_in);
 reg[127:0]mem[0:31];
 always @(posedge clk) begin if(r_ce_in)rd_out<=mem[r_addr_in];if(w_ce_in)mem[w_addr_in]<=wd_in;end
endmodule
module tb;
 localparam integer W=2120;
 reg clk=0;always #5 clk=~clk;
 reg we;reg[4:0]wa,ra;reg[W-1:0]wd;wire[W-1:0]a,b;
 fmem_ref #(.W(W))u_ref(.clk(clk),.we(we),.wa(wa),.wd(wd),.ra(ra),.rd(a));
 fmem_dut #(.W(W))u_dut(.clk(clk),.we(we),.wa(wa),.wd(wd),.ra(ra),.rd(b));
 integer collisions=0,checks=0;
 initial begin
 we=0;wa=0;ra=0;wd=0;
 for(integer c=0;c<20000;c=c+1)begin
 @(negedge clk);we=(c<64)||($urandom_range(0,3)!=0);wa=5'(c<64?c:$urandom_range(0,31));ra=(c%3==0)?wa:5'($urandom_range(0,31));
 for(integer k=0;k<W;k=k+32)begin
  for(integer j=0;j<32 && k+j<W;j=j+1)wd[k+j]=1'($urandom);
 end
 if(we && wa==ra)collisions=collisions+1;
 @(posedge clk);#1;if(c>=64)begin checks=checks+1;if(a!==b)$fatal(1,"FMEM_R4_MISMATCH cycle=%0d",c);end
 end
 $display("FMEM_R4_EQ_PASS width=%0d checks=%0d collisions=%0d",W,checks,collisions);$finish;
 end
endmodule
