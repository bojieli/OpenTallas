`timescale 1ns/1ps
module tb_hcoll_operand_column512;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,wv=0,rv=0;reg[5:0]wa,ra;reg[511:0]wd;
 wire dv;wire[511:0]dd;reg[511:0]gold[0:63],expected[0:3];reg[3:0]valid=0;
 integer checked=0,cycles=0;
 ot_hcoll_operand_column512 #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.w_v(wv),.w_addr(wa),.w_data(wd),.r_v(rv),.r_addr(ra),.rd_v(dv),.rd_data(dd));
 always @(posedge clk)begin
  cycles=cycles+1;valid<={valid[2:0],rv};if(rv)expected[0]<=gold[ra];
  for(integer d=1;d<4;d=d+1)expected[d]<=expected[d-1];
  if(cycles>16&&dv!==valid[3])$fatal(1,"OPERAND_COLUMN FAIL reply epoch");
  if(cycles>16&&dv)begin
   if(dd!==expected[3])$fatal(1,"OPERAND_COLUMN FAIL full512 data checked=%0d",checked);
   checked=checked+1;
  end
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  for(integer a=0;a<64;a=a+1)begin
   for(integer b=0;b<512;b=b+1)wd[b]=((a*17+b*31)^(a>>2)^(b>>3))&1;
   wa=a;wv=1;gold[a]=wd;@(negedge clk);
  end
  wv=0;repeat(4)@(negedge clk);
  for(integer n=0;n<256;n=n+1)begin rv=(n%7!=2);ra=(n*29+17)%64;@(negedge clk);end
  rv=0;repeat(6)@(negedge clk);
  if(checked!=219)$fatal(1,"OPERAND_COLUMN FAIL reply count=%0d",checked);
  $display("OPERAND_COLUMN PASS full512 replies=%0d cycles=%0d",checked,cycles);$finish;
 end
endmodule
