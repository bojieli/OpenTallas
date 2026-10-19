`timescale 1ns/1ps
module tb_s81sl_txmem #(parameter integer MUT=0);
 reg clk=0,rst=0;always #0.5 clk=~clk;
 reg we=0,re=0;reg[8:0]wa=0,ra=0;reg[552:0]wd=0;
 wire[552:0]gold,q;
 ot_s81ph_mem1r1w #(.W(553),.DEPTH(512),.SRAM(1),.WREG(1)) refmem(
  .clk(clk),.rst_n(rst),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(gold));
 ot_sram_oldread_wreg #(.W(553),.AW(9),.MUT(MUT)) dut(
  .clk(clk),.rst_n({35{rst}}),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),.q(q));
 integer cyc=0,errors=0,checks=0,i,j;reg[31:0]rng=32'h8675309;
 task step;begin
   @(negedge clk);if(cyc>0)begin checks=checks+1;if(q!==gold)begin errors=errors+1;if(errors<5)$display("TXMEM mismatch cycle%0d re%0d",cyc,re);end end
   cyc=cyc+1;
 end endtask
 task payload;begin for(j=0;j<18;j=j+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);wd=(wd<<32)|553'(rng);end end endtask
 initial begin
   step;step;rst=1;
   for(i=0;i<512;i=i+1)begin we=1;wa=9'(i);re=0;payload;step;end
   we=0;re=1;ra=511;step;
   for(i=0;i<4000;i=i+1)begin
     payload;we=(rng&3)!=0;re=(rng&7)!=0;wa=9'(rng>>4);
     ra=(i%4==0)?wa:9'(rng>>18);step;
   end
   we=0;re=0;repeat(4)step;
   if(errors==0)$display("TXMEM_EQ PASS checks%0d W553 depth512 OLDread+hold+forward",checks);
   else $display("TXMEM_EQ FAIL errors%0d checks%0d",errors,checks);
   $finish;
 end
endmodule
