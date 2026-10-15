`timescale 1ns/1ps
module tb_hbm_p_reduce_ports_static;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,fill_slot=0,source_read=0,publish_slot=0,scalar_valid=0;
 reg[3:0]fill_burst=0;
 reg[2055:0]rr=0;
 reg[9:0]source_word=0;
 wire source_valid;wire[31:0]source_fp32;wire ingress_fault,publish_fault;
 reg[31:0]expected_tag=0,scalar_tag=0,scalar_fp32=0;
 reg[15:0]publish_sector=0;reg[2:0]publish_word=0;
 wire[2247:0]wq;
 ot_hbm_p_reduce_ingress_static ingress(clk,rst_n,fill_slot,fill_burst,rr,
 source_read,source_word,source_valid,source_fp32,ingress_fault);
 ot_hbm_p_scalar_publish_static publisher(clk,rst_n,publish_slot,expected_tag,
 publish_sector,publish_word,scalar_valid,scalar_tag,scalar_fp32,wq,publish_fault);
 function automatic[31:0]value(input integer k);
  value=32'h3e800000^(32'(k)*32'h00012021);
 endfunction
 integer n,word_index,checks=0,mutant;
 initial begin
  mutant=$test$plusargs("MUTANT_TAG");
  repeat(3)@(negedge clk);rst_n=1;
  // Native eight-bank VM fill: ten bursts contain exactly one T640 head.
  for(n=0;n<10;n=n+1)begin
   fill_slot=1;fill_burst=4'(n);
   for(integer b=0;b<8;b=b+1)begin
    rr[b*257+256]=1;
    for(integer w=0;w<8;w=w+1)rr[b*257+w*32+:32]=value(n*64+b*8+w);
   end
   @(negedge clk);
  end
  fill_slot=0;rr=0;
  // MAX is contiguous. SUM follows the literal golden chunk8 order:
  // sample-major reads across all80chunks, followed by actual tree arithmetic.
  for(integer mode=0;mode<2;mode=mode+1)
   for(n=0;n<640;n=n+1)begin
    word_index=mode==0?n:(n%80)*8+n/80;
    source_read=1;source_word=10'(word_index);
    @(posedge clk);#1;
    if(!source_valid||source_fp32!==value(word_index))$fatal(1,"native source word %0d",word_index);
    checks=checks+1;@(negedge clk);
   end
  source_read=0;
  // All words and bank positions; masked writes carry actual FP32 scalar bits.
  for(n=0;n<128;n=n+1)begin
   publish_slot=1;scalar_valid=1;expected_tag=32'(n);scalar_tag=32'(n)^32'(mutant);
   scalar_fp32=value(n);publish_sector=16'(320+n/8);publish_word=3'(n%8);
   @(posedge clk);#1;
   for(integer b=0;b<8;b=b+1)begin
    if(wq[b*281+280]!=(b==publish_sector[2:0]))$fatal(1,"scalar bank");
    if(b==publish_sector[2:0]&&wq[b*281+:281]!==
     {1'b1,publish_sector,{8{scalar_fp32}},8'b1<<publish_word})$fatal(1,"scalar mask/data");
   end
   checks=checks+1;@(negedge clk);
  end
  publish_slot=0;scalar_valid=0;@(posedge clk);#1;
  if(ingress_fault||publish_fault)$fatal(1,"native source/publish fault");
  $display("PASS native P source/publish %0d checks, 8 actual SRAM; full P composition remains open",checks);
  $finish;
 end
endmodule
