`timescale 1ns/1ps
module tb;
 reg aon_clk=0,raw_qualified_n=0,sequence_ready=0;
 reg [16:0] desired_reset_n=0;
 reg [3:0] root_clk=0;
 reg stop_serial=0;
 wire [3:0] gates_quiet,domain_clk,enable_req;
 wire [16:0] reset_n;
 wire ready,fault;wire [1:0] phase;
 wire [3:0] actual_quiet_ack=
`ifdef MUT_ACK
 4'b1111;
`else
 gates_quiet;
`endif
 ot_hbm_quiescent_reset_commit #(.ENABLE(1)) dut(.*,.clock_enable_req(enable_req));
 for(genvar d=0;d<4;d=d+1) begin:g
  ot_hbm_boot_clock_gate #(.ENABLE(1)) gate(root_clk[d],enable_req[d],domain_clk[d],gates_quiet[d]);
 end
 always #1.5 aon_clk=~aon_clk;
 initial begin #0.071;forever #0.416667 root_clk[0]=~root_clk[0];end
 initial begin #0.183;forever #0.555556 if(!stop_serial) root_clk[1]=~root_clk[1];end
 initial begin #0.299;forever #0.512 root_clk[2]=~root_clk[2];end
 initial begin #0.407;forever #0.416667 root_clk[3]=~root_clk[3];end
 real release_at=0;
 for(genvar r=0;r<17;r=r+1) begin:release_check
  always @(posedge reset_n[r]) begin
   if(gates_quiet!==4'b1111 || domain_clk!==0) $fatal(1,"reset deasserted while an actual clock was live");
   release_at=$realtime;
  end
 end
 for(genvar d=0;d<4;d=d+1) begin:edge_check
  real last_rise=0;
  always @(posedge domain_clk[d]) if(raw_qualified_n && (&reset_n)) begin
   if($realtime-release_at<5.999) $fatal(1,"first actual destination edge preceded reset recovery guard");
   last_rise=$realtime;
  end
  always @(negedge domain_clk[d]) if(raw_qualified_n && (&reset_n) && last_rise!=0)
   if($realtime-last_rise<0.40) $fatal(1,"runt domain clock pulse");
 end
 initial begin
  #8;raw_qualified_n=1;sequence_ready=1;desired_reset_n='1;
  wait(ready);if(fault) $fatal(1,"valid boot faulted");
  @(negedge aon_clk);desired_reset_n[15]=0;
  repeat(3) @(posedge aon_clk);
  @(negedge aon_clk);desired_reset_n[15]=1;
  wait(ready);
  // Stop this actual root only after its gate has acknowledged held-low.
  @(negedge aon_clk);desired_reset_n[16]=0;
  wait(gates_quiet==4'b1111);stop_serial=1;
  @(negedge aon_clk);desired_reset_n[16]=1;
  repeat(12) @(posedge aon_clk);
  if(ready!==0) $fatal(1,"stopped serial root falsely reported started");
  stop_serial=0;wait(ready);
  #0.113;raw_qualified_n=0;#0.01;
  if(reset_n!==0 || ready!==0 || enable_req!==0) $fatal(1,"raw qualification loss not immediate");
  $display("PASS quiescent reset commit, actual phases, guard, stopped-root and raw veto");$finish;
 end
 initial begin #500;$fatal(1,"quiescent handshake did not finish");end
endmodule
