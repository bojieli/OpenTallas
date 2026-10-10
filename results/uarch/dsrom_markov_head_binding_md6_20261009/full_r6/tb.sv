`timescale 1ns/1ps
module tb #(parameter MUTANT=0);
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0]d_i=21946,row0=21920;reg[31:0]transaction=32'h12345;
 reg[255:0]x=0;reg b_v=0;reg[31:0]b_d=0;wire head_go,root_valid,joined_valid,done,fault,best_valid;
 wire[31:0]root_bits,joined_bits,best_bits;wire[16:0]joined_row,best_row;
 ot_dsrom_markov_head_lookup_A #(.ENABLE(1),.PINREG(1),.MUTANT_FOLD(MUTANT))dut(.*);
 reg[255:0]xm[0:255];reg[31:0]roots[0:31],bm[0:31],gold[0:31];
 integer cyc=0,g0=-1,nroot=0,njoin=0,first_tail=-1,last_tail=-1,highwater=0,head_cycle[0:31];
 reg[8*1024-1:0]dir;
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)begin
  b_v=0;
  if(head_go&&g0<0)g0=cyc;
  if(g0>=0&&cyc-g0>=5)x=xm[(cyc-g0-5)%256];
  if(root_valid)begin
   if(root_bits!==roots[nroot])$fatal(1,"actual Aroot mismatch row%0d got%h gold%h",nroot,root_bits,roots[nroot]);
   b_v=1;b_d=bm[nroot];nroot=nroot+1;
  end
  if(dut.successor.hv)head_cycle[dut.successor.driver.emitted]=cyc;
  if(dut.successor.driver.hn>highwater)highwater=dut.successor.driver.hn;
  if(joined_valid)begin
   if(joined_bits!==gold[njoin]||joined_row!==21920+njoin)$fatal(1,"postMarkov mismatch row%0d got%h gold%h",njoin,joined_bits,gold[njoin]);
   if(first_tail<0)first_tail=cyc-head_cycle[njoin];last_tail=cyc-head_cycle[njoin];njoin=njoin+1;
  end
  if(fault)$fatal(1,"successor fault");
  if(done)begin
   if(!best_valid||nroot!=32||njoin!=32||best_row!=21946||best_bits!==32'h3ed1ad60)$fatal(1,"argmax mismatch");
   $display("PASS actualAroot lookup256dot separatejoin argmax roots=%0d rows=%0d firsttail=%0d lasttail=%0d headqueuehighwater=%0d",nroot,njoin,first_tail,last_tail,highwater);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/x_skew.hex"},xm);$readmemh({dir,"/root.hex"},roots);$readmemh({dir,"/b.hex"},bm);$readmemh({dir,"/joined.hex"},gold);
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);while(!start_ready)@(negedge clk);
  start=1;@(negedge clk);start=0;
 end
 initial begin #30000;$fatal(1,"timeout");end
endmodule
