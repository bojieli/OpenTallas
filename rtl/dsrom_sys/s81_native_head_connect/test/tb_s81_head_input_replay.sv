`timescale 1ns/1ps
module tb_s81_head_input_replay;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,begin_load=0,lv=0,go=0;reg[46:0]owner=0;reg[63:0]seq=0;
 reg[6:0]li=0;reg[2047:0]ld=0;
 wire[255:0]xa,xb;wire active,fault;
 ot_s81_head_input_replay dut(clk,rst_n,begin_load,lv,go,owner,seq,li,ld,xa,xb,active,fault);
 integer mut=0,bad=0,n=0,j,m,k,c;
 function automatic[15:0] value(input integer user,input integer element);
  value=16'h3f00 ^ 16'(element*17+user*73);
 endfunction
 initial begin
  if($value$plusargs("MUT=%d",mut))begin end
  if(mut==4)force dut.select_q=2'd0;
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(k=0;k<2;k=k+1)begin
   owner=47'h12300000000+k;seq=64'habcdef0100000000+64'(k*256);
   begin_load=1;@(negedge clk);begin_load=0;
   for(m=0;m<80;m=m+1)begin
    lv=1;li=7'(m);if(mut==1&&m==37)li=7'd38;
    for(j=0;j<64;j=j+1)ld[32*j+:32]={value(k,64*m+j),16'b0};
    if(mut==2&&m==20)ld[0]=1;
    @(negedge clk);
   end
   lv=0;repeat(2)@(negedge clk);
   if(mut==3)seq=seq+1;
   go=1;@(negedge clk);go=0;
   // DUT launches on the edge after go was asserted. Its registered first
   // word is visible at G+4, and is sampled by the native head at G+5.
   for(c=1;c<8300;c=c+1)begin
    if(c>=5&&c<8274)begin
     for(j=0;j<16;j=j+1)begin
      if(xa[16*j+:16]!==value(k,16*((c-5)%256)+j))bad=bad+1;
      if(xb[16*j+:16]!==value(k,4096+16*((c-5)%64)+j))bad=bad+1;
     end
     n=n+1;
    end
    @(negedge clk);
   end
   if(fault)bad=bad+1;
  end
  $display("HEAD_INPUT_REPLAY %s mut=%0d words=%0d bad=%0d fault=%0d",bad==0?"PASS":"FAIL",mut,n,bad,fault);$finish;
 end
endmodule
