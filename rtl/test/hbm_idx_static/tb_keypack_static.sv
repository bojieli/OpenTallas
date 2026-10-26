`timescale 1ns/1ps
module tb_keypack_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,block_v=0;reg[1:0]block_number=0,source=2;reg[13:0]local_key=0;reg[1023:0]kr_fp32=0;
 wire key_v;wire[543:0]key_data;wire[36:0]key_address;wire fault;
 ot_hbm_idx_keypack_static dut(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.*);
 reg[1023:0]x[0:127];reg[559:0]gold[0:31];integer checked=0,errors=0;
 reg[36:0]addr;
 always @(negedge clk)if(key_v)begin
  addr={2'((2720+checked)/2736),35'(19864223744+2*134217728+((2720+checked)%2736)*68)};
  if(key_data!=={gold[checked][543:512],gold[checked][511:0]}||key_address!==addr)errors++;
  checked++;
 end
 initial begin
  $readmemh("query.hex",x);$readmemh("gold.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer i=0;i<128;i=i+1)begin
   block_v=1;local_key=14'(2720+i/4);block_number=2'(i);kr_fp32=x[i];
   if(MUT==1&&i==34)kr_fp32=0;
   if(MUT==2&&i==127)block_number=2;
   if(MUT==3&&i>=64&&i<68)source=3;else source=2;
   @(negedge clk);
  end
  block_v=0;repeat(20)@(negedge clk);
  $display("IDX_KEYPACK_STATIC MUT%0d checked%0d errors%0d fault%0d",MUT,checked,errors,fault);
  if(errors||fault||checked!=32)$fatal(1,"canonical KR FP4 physicalkey/address mismatch");$finish;
 end
endmodule
