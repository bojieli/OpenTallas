`timescale 1ns/1ps
module tb_hgi_coll_tkm_buffer;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,wv=0,rv=0;reg[9:0]wa,ra;reg[339:0]wd;
 wire dv;wire[339:0]dd;
 reg[339:0]gold[0:1023],expect0,expect1,expect2;reg[2:0]vpipe=0;
 integer i,j,checked=0,cycles=0;
 ot_hgi_coll_tkm_buffer #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.w_v(wv),.w_addr(wa),.w_data(wd),.r_v(rv),.r_addr(ra),.rd_v(dv),.rd_data(dd));
 always @(posedge clk)begin
  cycles=cycles+1;vpipe<={vpipe[1:0],rv};
  if(rv)expect0<=gold[ra];expect1<=expect0;expect2<=expect1;
  if(cycles>16&&dv!==vpipe[2])$fatal(1,"BUFFER FAIL valid alignment");
  if(cycles>16&&dv)begin
   if(dd!==expect2)$fatal(1,"BUFFER FAIL full340 data checked=%0d",checked);
   checked=checked+1;
  end
  if(cycles>3000)$fatal(1,"BUFFER FAIL timeout");
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  for(i=0;i<1024;i=i+1)begin
   for(j=0;j<340;j=j+1)wd[j]=((i*17+j*31)^(i>>3)^(j>>4))&1;
   gold[i]=wd;wv=1;wa=i;@(negedge clk);
  end
  wv=0;repeat(4)@(negedge clk);
  for(i=0;i<1024;i=i+1)begin rv=1;ra=(i*317+77)%1024;@(negedge clk);end
  rv=0;repeat(5)@(negedge clk);
  if(checked!=1024)$fatal(1,"BUFFER FAIL response count");
  $display("BUFFER PASS checked=1024 fullbits=348160 cycles=%0d",cycles);$finish;
 end
endmodule
