`timescale 1ns/1ps
module tb_head_nr_mem;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,we=0,re=0;reg[8:0]wa0=0,ra0=0;reg[127:0]wd=0;
 wire[127:0]q,nq,mq;wire[35:0]wa={4{wa0}},ra={4{ra0}};
 ot_sram_oldread_wreg #(.W(128),.AW(9),.SB(8),.GA(4))gold(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(q),.we_group(4'd0),.re_group(4'd0));
 ot_sram_oldread_wreg_nr #(.W(128),.AW(9),.SB(8),.GA(4))nr(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(nq),.we_group(4'd0),.re_group(4'd0));
 ot_sram_oldread_wreg_nr #(.W(128),.AW(9),.SB(8),.GA(4),.MUT(1))mut(.clk(ck),.rst_n({16{rn}}),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(mq),.we_group(4'd0),.re_group(4'd0));
 integer checks=0,mutants=0;
 always @(posedge ck)begin #1;
  if(rn)begin
   if(q!==nq)$fatal(1,"no-repair memory changed data at%0d",checks);
   if(mq!==nq)mutants=mutants+1;
   checks=checks+1;
  end
 end
 initial begin
  repeat(4)@(negedge ck);rn=1;
  for(integer i=0;i<2048;i=i+1)begin
   if(i<512)begin we=1;wa0=9'(i);ra0=9'(i-1);end
   else begin we=(i%5!=0);ra0=(i%4==0)?wa0:9'($urandom);wa0=9'($urandom);end
   re=(i%7!=0);wd={$urandom,$urandom,$urandom,$urandom};@(negedge ck);
  end
  we=0;repeat(4)@(negedge ck);
  if(mutants==0)$fatal(1,"forwarding mutant escaped");
  $display("HEAD_NR_MEM PASS cycles=%0d rows=512 forwarding_mutant=%0d extra_cycles=0",checks,mutants);$finish;
 end
endmodule
