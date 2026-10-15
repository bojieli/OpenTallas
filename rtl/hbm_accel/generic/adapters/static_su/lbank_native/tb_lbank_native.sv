`timescale 1ns/1ps
module tb_lbank_native;
 parameter integer RB=9;
 reg clk=0; always #5 clk=~clk;
 reg re=0,we=0; reg[RB-1:0]ra=0,wa=0;reg[31:0]wd=0;wire[31:0]rd;
 reg mutant=0;wire[RB-1:0]physical_wa=mutant?(wa & RB'(255)):wa;
 ot_hgi_su_lbank #(.RB(RB),.MACRO(1))dut(.clk(clk),.re(re),.ra(ra),.rd(rd),.we(we),.wa(physical_wa),.wd(wd));
 reg[31:0]reference[0:511];integer checks=0,errors=0,i;
 task automatic edge_access(input bit ren,input integer raddr,input bit wen,input integer waddr,input[31:0]data);
  reg[31:0]expected;
  begin
   @(negedge clk);re=ren;ra=RB'(raddr);we=wen;wa=RB'(waddr);wd=data;expected=reference[raddr];
   @(posedge clk);#1;
   if(ren)begin checks=checks+1;if(rd!==expected)begin
    if(errors<4)$display("MISMATCH address=%0d expected=%h got=%h",raddr,expected,rd);errors=errors+1;
   end end
   if(wen)reference[waddr]=data;
  end
 endtask
 initial begin
  mutant=$test$plusargs("MUT_ADDR");
  for(i=0;i<512;i=i+1)reference[i]=0;
  for(i=0;i<512;i=i+1)edge_access(0,0,1,i,32'h91a20000 ^ (32'(i)*32'h10201));
  for(i=0;i<512;i=i+1)edge_access(1,i,0,0,0);
  // Read/write the same SRAM word: read must see pre-edge contents.
  // Updating each word separately also checks the other seven columns retain their data.
  for(i=0;i<512;i=i+1)edge_access(1,i,1,i,32'h57cd0000 ^ (32'(i)*32'h70103));
  for(i=511;i>=0;i=i-1)edge_access(1,i,0,0,0);
  // Independent read/write addresses including opposite ends of the store.
  for(i=0;i<512;i=i+1)edge_access(1,511-i,1,i,32'h38690000 ^ 32'(i));
  for(i=0;i<512;i=i+1)edge_access(1,i,0,0,0);
  if(errors)$fatal(1,"LBANK_NATIVE FAIL checks=%0d errors=%0d",checks,errors);
  $display("LBANK_NATIVE PASS checks=%0d words=512 real_macro=128x256 used_rows=64",checks);$finish;
 end
endmodule
