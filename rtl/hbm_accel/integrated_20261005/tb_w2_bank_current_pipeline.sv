`timescale 1ns/1ps
module tb_w2_bank_current_pipeline;
 import ot_gpu_w6_secded_pkg::*;
 reg clk=0,por_n=0,load=0;
 reg [37*64-1:0] d=0;
 wire [37*64-1:0] q;wire normal,fault,repairing;
 integer edge_count=0,checks=0,start_edge;
 always #5 clk=~clk;
 always @(posedge clk)edge_count<=edge_count+1;
 ot_hbm_w2_protected_bank_current_on #(.WORDS(37)) dut(
 .clk(clk),.por_n(por_n),.load(load),.load_encoded(1'b0),.fatal(1'b0),.d(d),.encoded_d(2664'b0),
 .q(q),.encoded_q(),.normal(normal),.fault(fault),.repairing(repairing));
 task cold;
 begin por_n=0;load=0;repeat(2)@(negedge clk);por_n=1;@(negedge clk);end
 endtask
 task fill;
 begin
  for(integer i=0;i<37;i=i+1)d[i*64+:64]=64'h123456789abcdef0^(64'(i)<<32);
  load=1;@(negedge clk);load=0;
  if(normal||fault)$fatal(1,"load published before check");checks++;
  @(negedge clk);if(!normal||q!==d)$fatal(1,"clean protected capture");checks++;
 end
 endtask
 initial begin
  cold;fill;
  // Actual attributed owner stripe; CURRENT must withhold immediately.
  dut.code[34][62]=~dut.code[34][62];#1;
  if(normal||fault||!repairing)$fatal(1,"stale clean authorization");checks++;
  start_edge=edge_count;
  wait(normal);#1;if(q!==d||fault)$fatal(1,"owner CE repair exactness");checks++;
  $display("CE_REPAIR edges=%0d",edge_count-start_edge);
  @(negedge clk);
  dut.code[0][0]=~dut.code[0][0];dut.code[36][71]=~dut.code[36][71];
  wait(normal);#1;if(q!==d||fault)$fatal(1,"parallel independent CE");checks++;
  @(negedge clk);dut.syndrome[34][0]=~dut.syndrome[34][0];#1;
  if(normal||!fault)$fatal(1,"protected check metadata corruption");checks++;
  @(negedge clk);if(!fault)$fatal(1,"fault not retained");
  cold;fill;
  dut.snapshot_lo[34][0]=~dut.snapshot_lo[34][0];#1;
  if(normal||!fault)$fatal(1,"protected captured owner corruption");checks++;
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];dut.code[34][61]=~dut.code[34][61];
  wait(fault);#1;if(normal)$fatal(1,"DUE permitted");checks++;
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];
  wait(dut.phase==2);@(negedge clk);dut.code[34][60]=~dut.code[34][60];#1;
  if(normal||!fault)$fatal(1,"repair changed identity allowed");checks++;
  cold;fill;
  dut.phase_code[0]=~dut.phase_code[0];#1;
  if(normal||!fault)$fatal(1,"controller corruption permitted");checks++;
  $display("PASS_W2_CURRENT words=37 checks=%0d current_owner34bit62=1 protected_snapshot=1 protected_status=1 parallel_CE=1 DUE_refusal=1 changed_repair_identity=1",checks);
  $finish;
 end
endmodule
