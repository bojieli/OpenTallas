`timescale 1ns/1ps
module tb_grouped;
 parameter integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg[1:0]we=0;reg[8:0]wa=0,ra=0;reg[8479:0]data=0;
 wire[8479:0]oldq,newq;
 reg[4239:0]gold[0:1][0:319];reg[8479:0]expected;
 reg[31:0]rng=32'haced1234;integer checks=0,cycle=0;
 ot_hdc_v41x_attn_staging #(.D(512),.NL(2),.TROWS(640),.SRAM_MACRO(1)) original(.clk(clk),.wr_en(we),.wr_addr(wa),.wr_data(data),.rd_addr(ra),.rd_data(oldq));
 ot_hbm_attn_staging_grouped #(.MUT(MUT)) candidate(.clk(clk),.wr_en(we),.wr_addr(wa),.wr_data(data),.rd_addr(ra),.rd_data(newq));
 task tick(input[1:0]w,input integer a,input integer r);
 begin
  @(negedge clk);we=w;wa=9'(a);ra=9'(r);
  for(integer k=0;k<265;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);data[k*32+:32]=rng;end
  expected={gold[1][r],gold[0][r]};
  @(posedge clk);#0.001;
  if(oldq!==expected)$fatal(1,"baseline scoreboard mismatch cycle%0d addr%0d",cycle,r);
  if(newq!==expected)$fatal(1,"grouped scoreboard mismatch cycle%0d addr%0d MUT%0d",cycle,r,MUT);
  checks=checks+8480;
  for(integer l=0;l<2;l=l+1)if(w[l])gold[l][a]=data[l*4240+:4240];
  cycle=cycle+1;
 end endtask
 initial begin
  for(integer l=0;l<2;l=l+1)for(integer a=0;a<320;a=a+1)gold[l][a]=0;
  // Every row, both lanes, flags/scale/code, and same-address old-data reads.
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   for(integer a=0;a<320;a=a+1)tick(3,a,a);
   for(integer a=319;a>=0;a=a-1)tick(0,0,a);
   // Independent lane masks and concurrent reads at a permuted address.
   for(integer a=0;a<320;a=a+1)tick((a%2)?1:2,a,(a*37)%320);
   for(integer a=0;a<320;a=a+1)tick(0,0,a);
  end
  $display("PASS grouped actual34SRAM baseline+flat scoreboard cycles=%0d bitchecks=%0d MUT=%0d",cycle,checks,MUT);$finish;
 end
endmodule
