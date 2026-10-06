`timescale 1ps/1fs
// Registered-veto bank bench. The original CHECK bench (tb_w2_bank_check_pipeline)
// asserts same-edge withdrawal (#1 after a corruption). The registered veto
// instead guarantees that normal is only ever asserted together with the exact
// protected value it verified: the monitor below checks q===expected on EVERY
// edge where normal is high, across every injected corruption. Each original
// scenario is kept; "immediately" becomes "within the two-edge verdict
// pipeline", and every fault must latch within FAULT_EDGES.
module tb_w2_bank_veto(input wire clk,output reg done=0);
 import ot_gpu_w6_secded_pkg::*;
`ifndef VETO_STAGE
 `define VETO_STAGE 0
`endif
`ifndef VETO_DIST
 `define VETO_DIST 1
`endif
 localparam integer FAULT_EDGES=6,REPAIR_EDGES=40;
 reg por_n=0,load=0,load_sel=0;
 reg [37*64-1:0] d=0,expected=0;reg [37*72-1:0] enc=0;
 wire [37*64-1:0] q;wire normal,fault,repairing;
 integer edge_count=0,checks=0,start_edge,k,normal_edges=0;
 reg armed=0;
 always @(posedge clk)edge_count<=edge_count+1;
 ot_hbm_w2_protected_bank_veto_on #(.WORDS(37),.STAGE(`VETO_STAGE),.DIST(`VETO_DIST)) dut(
  .clk(clk),.por_n(por_n),.load(load),.load_sel(load_sel),.fatal(1'b0),.encoded_d(enc),
  .q(q),.normal(normal),.fault(fault),.repairing(repairing));
 // Registered-veto invariant: a permission is a verdict about exactly the
 // presented bits. Sampled on every rising edge (where consumers sample).
 always @(posedge clk)if(armed&&normal)begin
  normal_edges=normal_edges+1;
  if(q!==expected)$fatal(1,"VETO: normal asserted with unverified data");
  if(fault)$fatal(1,"VETO: normal and fault together");
 end
 task cold;
  begin armed=0;por_n=0;load=0;repeat(2)@(negedge clk);por_n=1;
   for(k=0;k<REPAIR_EDGES&&!normal;k=k+1)@(negedge clk);
   if(!normal||fault||q!==0)$fatal(1,"POR zero commit");expected=0;armed=1;end
 endtask
 task fill;
  begin
   for(integer i=0;i<37;i=i+1)begin d[i*64+:64]=64'h123456789abcdef0^(64'(i)<<32);enc[i*72+:72]=encode64(d[i*64+:64]);end
   if(!normal)$fatal(1,"fill needs EVAL");
   load=1;load_sel=1;@(negedge clk);load=0;load_sel=0;
   if(normal||fault)$fatal(1,"load published before check");checks++;
   expected=d;
   @(negedge clk);if(normal||fault)$fatal(1,"VERIFY published before protected verdict");checks++;
   for(k=0;k<REPAIR_EDGES&&!normal;k=k+1)@(negedge clk);
   if(!normal||q!==d)$fatal(1,"clean protected capture");checks++;
  end
 endtask
 task wait_fault(input [8*48-1:0] what,input integer bound=FAULT_EDGES);
  begin
   for(k=0;k<bound&&!fault;k=k+1)@(negedge clk);
   if(!fault||normal)$fatal(1,"%0s",what);checks++;
   repeat(3)@(negedge clk);if(!fault||normal)$fatal(1,"fault not retained");
  end
 endtask
 task wait_withdraw(input [8*48-1:0] what);
  begin
   for(k=0;k<3&&normal;k=k+1)@(negedge clk);
   if(normal||fault||!repairing)$fatal(1,"%0s",what);checks++;
  end
 endtask
 initial begin
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];
  wait_withdraw("stale clean authorization");
  start_edge=edge_count;
  for(k=0;k<REPAIR_EDGES&&!normal;k=k+1)@(negedge clk);
  if(!normal||q!==d||fault)$fatal(1,"owner CE repair exactness");checks++;
  $display("CE_REPAIR edges=%0d",edge_count-start_edge);
  @(negedge clk);
  dut.code[0][0]=~dut.code[0][0];dut.code[36][71]=~dut.code[36][71];
  wait_withdraw("parallel CE used stale authorization");
  for(k=0;k<REPAIR_EDGES&&!normal;k=k+1)@(negedge clk);
  if(!normal||q!==d||fault)$fatal(1,"parallel independent CE");checks++;
  @(negedge clk);dut.syndrome[34][0]=~dut.syndrome[34][0];
  wait_fault("protected check metadata corruption");
  cold;fill;
  dut.snapshot_lo[34][0]=~dut.snapshot_lo[34][0];
  wait_fault("protected captured owner corruption");
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];dut.code[34][61]=~dut.code[34][61];
  wait_fault("DUE permitted",REPAIR_EDGES); // original: unbounded wait(fault)
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];
  wait(dut.phase==3);@(negedge clk);dut.code[34][60]=~dut.code[34][60];
  wait_fault("repair changed identity allowed");
  cold;fill;
  dut.phase_code[0]=~dut.phase_code[0];
  wait_fault("controller corruption permitted");
  cold;fill;
  dut.verdict[34][0]=~dut.verdict[34][0];
  wait_fault("protected verdict corruption permitted");
  cold;fill;
  dut.checked_lo[34][0]=~dut.checked_lo[34][0];
  wait_fault("checker snapshot parity mutation permitted");
  cold;fill;
  dut.code[34][62]=~dut.code[34][62];
  wait(dut.phase==1);@(negedge clk);dut.snapshot_lo[34][0]=~dut.snapshot_lo[34][0];
  wait_fault("VERIFY input corruption permitted",REPAIR_EDGES); // original: unbounded wait(fault)
  // Kept per-word enable copies are checked against the protected phase.
  cold;fill;
  dut.word[17].u_cp.q[4]=~dut.word[17].u_cp.q[4];
  wait_fault("enable copy corruption permitted");
  cold;fill;
  dut.word[3].u_cp.q[0]=~dut.word[3].u_cp.q[0];
  wait_fault("commit-select copy corruption permitted");
  if(normal_edges<20)$fatal(1,"monitor saw too few normal edges");
  $display("PASS_W2_VETO words=37 stage=%0d dist=%0d checks=%0d normal_edges_monitored=%0d current_owner34bit62=1 protected_snapshot=1 protected_status=1 parallel_CE=1 DUE_refusal=1 changed_repair_identity=1 copy_check=1",
   `VETO_STAGE,`VETO_DIST,checks,normal_edges);
  done=1;
 end
endmodule

module tb_w2_bank_veto_top;
 reg clk=0;wire done;
 always #416.666 clk=~clk;
 tb_w2_bank_veto u(.clk(clk),.done(done));
 initial begin wait(done);$finish;end
 initial begin #50000000;$fatal(1,"timeout");end
endmodule
