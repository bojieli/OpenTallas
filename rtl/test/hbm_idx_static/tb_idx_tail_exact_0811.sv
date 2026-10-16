`timescale 1ns/1ps
module tb_idx_tail_exact_0811;
 reg clk=0; always #5 clk=~clk;
 integer cycle=0,mutation=0,errors=0,checked=0,issued=0;
 reg rst_n=0,iv=0;reg[3:0]kv=0,keep=0;reg[511:0]sums=0;reg[15:0]faults=0;
 wire ov;wire[3:0]ok,ofault;wire[63:0]score;
 reg clock_enable=1;
 always @(negedge clk)clock_enable <= !(mutation==3 && cycle==96);
 wire tail_clk=clk && clock_enable;
 reg[511:0]dut_sums;always @*begin
  dut_sums=sums;
  if(mutation==1)for(integer k=0;k<4;k=k+1)begin
   dut_sums[(4*k+1)*32+:32]=sums[(4*k+2)*32+:32];
   dut_sums[(4*k+2)*32+:32]=sums[(4*k+1)*32+:32];
  end
 end
 ot_hbm_idx_tail_native dut(.clk(tail_clk),.rst_n(rst_n),.i_v(iv),.i_kv(kv),.i_keep(keep),.i_sum(dut_sums),
  .i_fault(mutation==2?16'd0:faults),.o_v(ov),.o_kv(ok),.o_score(score),.o_fault(ofault));
 reg[535:0]inputs[0:255];reg[71:0]gold[0:255];
 reg due[0:1023];reg[71:0]expect_word[0:1023];
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)if(rst_n && cycle>20)begin
  if(ov!==due[cycle])begin errors++;if(errors<6)$display("TAIL_TIMELINE cycle%0d expected%0d got%0d",cycle,due[cycle],ov);end
  if(ov)begin
   checked++;
   if({ok,ofault,score}!==expect_word[cycle])begin errors++;if(errors<6)$display("TAIL_DATA cycle%0d expected%h got%h",cycle,expect_word[cycle],{ok,ofault,score});end
  end
 end
 initial begin
  if($value$plusargs("MUT=%d",mutation))begin end
  for(integer c=0;c<1024;c=c+1)begin due[c]=0;expect_word[c]=0;end
  $readmemh("input.hex",inputs);$readmemh("expected.hex",gold);
  repeat(4)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
  for(integer i=0;i<256;i=i+1)begin
   iv=1;{kv,keep,faults,sums}=inputs[i];due[cycle+16]=1;expect_word[cycle+16]=gold[i];issued++;
   @(negedge clk);iv=0;
   // Deterministic holes check exact validity, independent of all data/fault bits.
   if(i%7==0)repeat(2)@(negedge clk);
  end
  iv=0;repeat(24)@(negedge clk);
  $display("IDX_TAIL_EXACT MUT%0d issued%0d checked%0d lanes%0d errors%0d latency16",mutation,issued,checked,checked*4,errors);
  if(errors||checked!=256)$fatal(1,"actual static tail data or fixed-timeline mismatch");
  $display("IDX_TAIL_EXACT PASS");$finish;
 end
endmodule
