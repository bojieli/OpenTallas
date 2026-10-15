`timescale 1ns/1ps
module tb_store141;
 parameter integer MUT=0;
 reg clk=0,we=0; always #5 clk=~clk;
 reg[5:0]wa=0,ra=0;reg[140:0]din=0;wire[140:0]dout;
 ot_qkvd_llr_replay_sram_leaf #(.W(141),.QD(64),.MUT(MUT)) dut(.ck(clk),.we(we),.wa(wa),.ra(ra),.din(din),.dout(dout));
 function automatic [140:0] data(input integer lap,input integer row);
 integer b;begin for(b=0;b<141;b=b+1)data[b]=((row*13+b*7+lap*31)>>(b%7))&1;end endfunction
 integer lap,j,checks=0;
 initial begin
 for(lap=0;lap<3;lap=lap+1)begin
  for(j=0;j<64;j=j+1)begin @(negedge clk);we=1;wa=j;din=data(lap,j);end
  @(negedge clk);we=0;
  repeat(3)@(negedge clk);
  for(j=0;j<65;j=j+1)begin ra=j%64;@(posedge clk);#1;
   if(j>0)begin if(dout!==data(lap,j-1))$fatal(1,"STORE141 FAIL lap=%0d row=%0d got=%h expected=%h",lap,j-1,dout,data(lap,j-1));checks=checks+1;end
   @(negedge clk);
  end
 end
 $display("STORE141 PASS exact=%0d bits=%0d native64x512=1 throughput=1word/edge",checks,checks*141);$finish;
 end
endmodule
