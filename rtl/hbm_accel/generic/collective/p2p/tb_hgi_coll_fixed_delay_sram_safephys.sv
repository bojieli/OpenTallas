`timescale 1ns/1ps
module tb_hgi_coll_fixed_delay_sram_safephys;
 parameter integer MUT=0;
 reg clk=0;always #0.416 clk=~clk;
 reg rst_n=0;reg[139:0]a;reg[23:0]s;reg[67:0]i;
 wire[139:0] ao;wire[23:0] so,sl;wire[67:0]io;
 reg[139:0]ar[0:82];reg[23:0]sr[0:73],lr[0:8];reg[67:0]ir[0:11];
 integer checks=0,errors=0,age=0;
 ot_hgi_coll_fixed_delay_sram_safephys #(.W(140),.D(83),.MUT_SLOT(MUT==1),.MUT_RESET(MUT==2)) u_a(clk,rst_n,a,ao);
 ot_hgi_coll_fixed_delay_sram_safephys #(.W(24),.D(74),.MUT_SLOT(MUT==3)) u_s(clk,rst_n,s,so);
 ot_hgi_coll_fixed_delay_sram_safephys #(.W(24),.D(9)) u_l(clk,rst_n,so,sl);
 ot_hgi_coll_fixed_delay_sram_safephys #(.W(68),.D(12),.MUT_SLOT(MUT==4)) u_i(clk,rst_n,i,io);
 initial begin
 a=0;s=0;i=0;
 for(integer n=0;n<10000;n=n+1)begin
  @(negedge clk);rst_n=(n>3 && n%997>3);
  a={$random,$random,$random,$random,$random};s=$random;i={$random,$random,$random};
  if(!rst_n)begin age=0;for(integer k=0;k<83;k=k+1)ar[k]=0;for(integer k=0;k<74;k=k+1)sr[k]=0;for(integer k=0;k<9;k=k+1)lr[k]=0;for(integer k=0;k<12;k=k+1)ir[k]=0;end
  @(posedge clk);
  // Cascade samples previous early output, exactly like original select pipe.
  for(integer k=8;k>0;k=k-1)lr[k]=lr[k-1];lr[0]=so;
  for(integer k=82;k>0;k=k-1)ar[k]=ar[k-1];ar[0]=a;
  for(integer k=73;k>0;k=k-1)sr[k]=sr[k-1];sr[0]=s;
  for(integer k=11;k>0;k=k-1)ir[k]=ir[k-1];ir[0]=i;
  #0.01;
  if(rst_n)begin
   age=age+1;
   if(ao!==(age>=83?ar[82]:140'b0))errors=errors+1;
   if(so!==(age>=74?sr[73]:24'b0))errors=errors+1;
   if(io!==(age>=12?ir[11]:68'b0))errors=errors+1;
   if(age>=83 && sl!==lr[8])errors=errors+1;
   checks=checks+4;
  end
 end
 if(errors)$fatal(1,"FAIL fixed_delay checks=%0d errors=%0d",checks,errors);
 $display("PASS fixed_delay checks=%0d cycles=10000 II=1 reset_bursts=11",checks);$finish;
 end
endmodule
