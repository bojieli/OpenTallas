`timescale 1ns/1ps
`ifndef META_D
`define META_D 146
`endif
module tb_col8_meta_sram;
 reg clk=0;always #5 clk=~clk;reg[24:0]d=25'h123456;wire[24:0]q;reg[24:0]refd[0:145];integer n=0,checks=0;
 ot_hidx_meta_sram146 #(.D(`META_D))dut(.clk(clk),.clk_mem(clk),.d(d),.q(q));
 always@(posedge clk)begin n<=n+1;d<={d[23:0],d[24]^d[21]^d[7]^d[0]};refd[0]<=d;for(integer i=1;i<146;i=i+1)refd[i]<=refd[i-1];end
 always@(negedge clk)if(n>146)begin
 if(q!==refd[145])$fatal(1,"COL8_META_SRAM_FAIL cycle=%0d",n);
 checks=checks+1;if(checks==600)begin $display("COL8_META_SRAM_PASS checks=%0d edges=146",checks);$finish;end end
endmodule
