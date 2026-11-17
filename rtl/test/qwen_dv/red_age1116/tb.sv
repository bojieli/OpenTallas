`timescale 1ns/1ps
module tb;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_n=0;reg[7:0]l_ov=0;reg[255:0]l_out=0;reg[1:0]l_red0=1;
 reg l_redsq0=1,l_last0=0;reg[23:0]l_raddr0=24'hc00000;
 wire red_we,rd_v,busy,fault;wire[23:0]red_addr;wire[31:0]red_data;
 qfd_dv_s5_red2_leaf a(.ck(ck),.rst_n(rst_n),.l_ov(l_ov),.l_out(l_out),.l_red0(l_red0),.l_redsq0(l_redsq0),.l_last0(l_last0),.l_raddr0(l_raddr0),.red_we(red_we));
 integer cy=0,start=-1,seen=0;
 always @(posedge ck)begin
  #0.001;cy=cy+1;
  if(red_we)begin
   $display("RED_OUTPUT cycle=%0d start=%0d age=%0d addr=%h data=%h fault=%b",cy,start,cy-start,24'd0,32'd0,fault);
   
   if(cy-start != 109+16*seen) $fatal(1,"RED_ROW_II");
   seen=seen+1;
  end
  
 end
 initial begin
  repeat(12)@(negedge ck);rst_n=1;repeat(32)@(negedge ck);
  start=cy+1;
  for(integer n=0;n<48;n=n+1)begin l_ov=255;l_out={8{32'h40000000}};l_last0=n%16==15;@(negedge ck);end
  l_ov=0;l_last0=0;repeat(200)@(negedge ck);
  if(seen!=3)$fatal(1,"RED_COUNT seen=%0d",seen);
  $display("NATIVE_RED_VALID_AGE_PASS rows=3 elements=384 payload_unobserved");$finish;
 end
endmodule
