`timescale 1ns/1ps
module tb;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_n=0;reg[7:0]l_ov=0;reg[255:0]l_out=0;reg[1:0]l_red0=1;
 reg l_redsq0=1,l_last0=0;reg[23:0]l_raddr0=24'hc00000;
 wire red_we,rd_v,busy,fault;wire[23:0]red_addr;wire[31:0]red_data;
 qfd_dv_s5_red2_leaf a(.*);
 integer cy=0,start=-1,seen=0;
 always @(posedge ck)begin
  #0.001;cy=cy+1;
  if(red_we)begin
   $display("RED_OUTPUT cycle=%0d start=%0d age=%0d addr=%h data=%h fault=%b",cy,start,cy-start,red_addr,red_data,fault);
   if(red_data!==32'h44000000 || red_addr!==24'hc00000) $fatal(1,"RED_VALUE");
   seen=seen+1;
  end
  if(rst_n&&cy>32&&fault)$fatal(1,"RED_FAULT");
 end
 initial begin
  repeat(12)@(negedge ck);rst_n=1;repeat(32)@(negedge ck);
  start=cy+1;
  for(integer n=0;n<16;n=n+1)begin l_ov=255;l_out={8{32'h40000000}};l_last0=n==15;@(negedge ck);end
  l_ov=0;l_last0=0;repeat(200)@(negedge ck);
  if(seen!=1)$fatal(1,"RED_COUNT seen=%0d",seen);
  $display("NATIVE_RED_AGE_PASS rows=1 elements=128 value=512");$finish;
 end
endmodule
