`timescale 1ns/1ps
module tb_psel;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,step=0,oddstep=0;reg[1023:0]banks;
 reg[8:0]pr;wire[8:0]pn=pr+(oddstep?9'd1:9'd2);wire[8:0]pa=step?pn:pr;
 always@(posedge clk or negedge rst_n)if(!rst_n)pr<=0;else if(step)pr<=pn;
 wire[511:0]w0[4],w1[4];reg[3:0]os;
 always@(posedge clk)begin os[0]<=pa[0];os[1]<=~pa[0];os[2]<=pr[0];os[3]<=0;end
 for(genvar g=0;g<4;g++)begin:G
  dsdv_svc_pword_pick_n32 #(.PMEM(g==3?0:1),.MUT(g==1?4:(g==2?5:0)))dut(.clk(clk),.rst_n(rst_n),.step(step),.oddstep(oddstep),.banks(banks),.word0(w0[g]),.word1(w1[g]));
  for(genvar c=0;c<3;c++)begin:PC
   always@(negedge clk)if($time>20&&dut.g_cohort[c].p!==pr[0])$fatal(1,"actual parity mismatch");
  end
 end
 integer checks=0,errors=0,negative=0;reg[31:0]rng=32'h218f;
 initial begin
  for(integer epoch=0;epoch<4;epoch++)begin
   rst_n=0;repeat(3)@(negedge clk);rst_n=1;
   for(integer k=0;k<2500;k++)begin
    rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);step=(k<10)?1:rng[0];oddstep=(k<10)?1:rng[1];
    for(integer b=0;b<32;b++)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);banks[32*b+:32]=(k==0)?0:((k==1)?32'hffffffff:rng);end
    @(posedge clk);#1;
    for(integer g=0;g<4;g++)begin checks++;if({w0[g],w1[g]}!== (os[g]?{banks[1023:512],banks[511:0]}:{banks[511:0],banks[1023:512]}))errors++;end
    if({w0[0],w1[0]}!=={w0[2],w1[2]})negative++;
    @(negedge clk);
   end
  end
  $display("PSEL_RESULT checks=%0d errors=%0d missingprefetch_mismatches=%0d",checks,errors,negative);
  if(checks!=40000||errors||negative<1000)$fatal(1,"P selector failure");$finish;
 end
endmodule
