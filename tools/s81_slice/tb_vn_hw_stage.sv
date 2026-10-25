`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg re=0,we=0;reg[6:0] ra=0,wa=0;reg[255:0] wd=0;
wire [255:0] refq,memq,q,md;wire mw;wire[6:0]ma;
ot_s81sl_hw_write_stage st(clk,re,ra,we,wa,wd,memq,mw,ma,md,q);
ot_sram_1r1w_128x256_m1_r2c2 refm(clk,re,ra,refq,we,wa,wd,{256{1'b1}},2'd0,14'd0,2'd0,16'd0);
ot_sram_1r1w_128x256_m1_r2c2 dutm(clk,re,ra,memq,mw,ma,md,{256{1'b1}},2'd0,14'd0,2'd0,16'd0);
integer cycle=0,checks=0,seed=12345;reg[6:0]lastwa=0;reg lastwe=0;
initial begin
 if($value$plusargs("SEED=%d",seed))begin end
 repeat(4) @(negedge clk);
 for(cycle=0;cycle<40000;cycle=cycle+1)begin
  @(negedge clk);
  if(cycle>1)begin checks=checks+1;if(q!==refq)$fatal(1,"DIFF cycle%0d q%h ref%h",cycle,q,refq);end
  re=($random(seed)&3)!=0;we=($random(seed)&3)!=0;wa=$random(seed)&127;
  // Directed immediate read-after-write, same-address write collisions,
  // repeated addresses and read-enable gaps among random full-word writes.
  ra=(cycle%3==0)?lastwa:((cycle%3==1)?wa:($random(seed)&127));
  if(cycle%11<4)wa=7'd3;
  for(integer j=0;j<8;j=j+1)wd[32*j+:32]=$random(seed);
  lastwa=wa;lastwe=we;
 end
 @(negedge clk);if(q!==refq)$fatal(1,"DIFF final");
 $display("PASS HW_STAGE exact %0d every-cycle reads",checks);$finish;
end
endmodule
