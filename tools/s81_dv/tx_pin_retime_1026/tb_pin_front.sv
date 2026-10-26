`timescale 1ns/1ps
module tb_pin_front;
 reg ck=0;always #5 ck=~ck;
 reg r0=0,r2=0,r3=0,r6=0;
 reg[275:0]vi=0,vo=0;
 reg[287:0]rv,ro;
 wire[692:0]o[0:2];
 genvar i;
 generate for(i=0;i<3;i=i+1)begin:g
  dsdv_tx_pin_front #(.RETIME(i==0?0:1),.MUT(i==2?1:0))u(
   .ck(ck),.r0(r0),.r2(r2),.r3(r3),.r6(r6),.vi(vi),.vo(vo),
   .vi_r(o[i][0+:276]),.vo_r(o[i][276+:276]),.hsw(o[i][552+:64]),.shs(o[i][616+:32]),
   .scl_m(o[i][648+:4]),.scl_w(o[i][652+:4]),.eph(o[i][656+:16]),.okk(o[i][672+:18]),
   .ct_tick_pred(o[i][690]),.ct_delay_hi(o[i][691]),.ct_tick_lo(o[i][692]));
 end endgenerate
 integer checks=0,mutants=0,cycle=0;
 always @(posedge ck)begin
  #1;cycle=cycle+1;
  if(o[0]!==o[1])begin $display("PIN_FRONT_MISMATCH cycle=%0d xor=%h",cycle,o[0]^o[1]);$fatal(1);end
  checks=checks+693;
  if(o[0]!==o[2])mutants=mutants+1;
 end
 initial begin
  for(integer n=0;n<30000;n=n+1)begin
   @(negedge ck);
   for(integer b=0;b<288;b=b+32)begin rv[b+:32]=$urandom;ro[b+:32]=$urandom;end
   vi=rv[275:0];vo=ro[275:0];
   vi[0]=1;vi[3:1]=4;vi[6]=0;vi[7]=0;
   vo[0]=1;vo[3:1]=(n%3==0)?5:0;vo[28:21]=8'h5c;vo[31:29]=2;vo[6]=0;
   r0=(n%31)>=3;r2=(n%37)>=4;r3=(n%41)>=5;r6=(n%43)>=6;
   #1;if(n>0&&o[0]!==o[2])mutants=mutants+1;
   if(n>0&&o[0]!==o[1])begin $display("PIN_FRONT_ASYNC_MISMATCH n=%0d",n);$fatal(1);end
  end
  @(negedge ck);
  $display("PIN_FRONT_PASS cycles=%0d bitchecks=%0d mutant_edges=%0d",cycle,checks,mutants);
  if(mutants<100)$fatal(1,"MUTANT_NOT_CAUGHT");
  $finish;
 end
endmodule
