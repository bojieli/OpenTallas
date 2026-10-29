`timescale 1ns/1ps
module tb_asap7_asr_functional;
 reg ck=0,d=0,r=1,s=1;always #5 ck=~ck;wire q,bad;
 DFFASRHQNx1_ASAP7_75t_R u(.QN(q),.D(d),.RESETN(r),.SETN(s),.CLK(ck));
 DFFASRHQN_bad b(.QN(bad),.D(d),.RESETN(r),.SETN(s),.CLK(ck));
 integer checks=0,caught=0;
 task check(input bit wanted);
  #0.01;if(q!==wanted)$fatal(1,"supplied UDP truth mismatch got%b expected%b",q,wanted);
  checks++;if(bad!==wanted)caught++;
 endtask
 initial begin
  @(posedge ck);check(1);@(negedge ck);d=1;@(posedge ck);check(0);
  @(negedge ck);r=0;check(1);s=0;check(0);r=1;check(0);s=1;d=0;
  @(posedge ck);check(1);@(negedge ck);d=1;@(posedge ck);check(0);
  @(negedge ck);r=0;check(1);r=1;@(posedge ck);check(0);
  if(checks<9||caught<2)$fatal(1,"missing model control");
  $display("PASS ASR_truth_checks=%0d bad_reader_model_caught=%0d",checks,caught);$finish;
 end
endmodule
