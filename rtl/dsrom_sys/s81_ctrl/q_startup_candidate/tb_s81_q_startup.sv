`timescale 1ns/1ps
module tb_s81_q_startup;
 reg clk=0, run_clk=1, rst_n=0;
 always #0.5 if(run_clk) clk=~clk;
 wire [11:0] ack;wire ready;
 ot_s81_q_elem_startup_native #(.QCG(1),.QH(1),.PQ(1),.QM(5),.QS(6),.QX(10),.QY(1),.QZ(1),.NB(2),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.QTIMING_FIX(1),.QPIPE(1)) dut
 (.clk(clk),.rst_n(rst_n),.cfg_v(1'b0),.cfg_a(5'd0),.cfg_d(48'd0),.go(1'b0),.go_tag(2'b0),
 .xs_v(1'b0),.xs_p(8'd0),.xs_b(3'd0),.xs_sv(2'b0),.xs_q0(256'd0),.xs_e0(10'd0),.xs_q1(256'd0),.xs_e1(10'd0),.xs_pos(3'd0),.startup_rst_ack(ack),.startup_local_ready(ready));
 initial begin
  repeat(4) @(negedge clk);
  rst_n=1;
  repeat(15) @(negedge clk);
  if(ack!==12'hfff||!ready) $fatal(1,"STARTUP_FAIL GO withheld genuine gated reset release ACK missing");
  if(dut.u_e.startup_keepalive) $fatal(1,"STARTUP_FAIL keepalive did not retire");
  for(int n=0;n<6;n++)begin
   run_clk=0;rst_n=0;#1;
   if(ack!==0||ready) $fatal(1,"STARTUP_FAIL stopped-clock raw epoch clear");
   rst_n=1;#2;
   if(ack!==0||ready) $fatal(1,"STARTUP_FAIL stopped-clock forged release");
   run_clk=1;
   repeat(15) @(negedge clk);
   if(ack!==12'hfff||!ready) $fatal(1,"STARTUP_FAIL restarted gate did not acknowledge");
  end
  rst_n=0;repeat(3) @(negedge clk);
  force dut.u_e.g_mac[1].rst_mt=1'b0;
  rst_n=1;repeat(15) @(negedge clk);
  if(ack[10]!==0) $fatal(1,"STARTUP_FAIL held actual tree reset falsely witnessed");
  if(ready) $fatal(1,"STARTUP_FAIL omitted real tree reset consumer");
  release dut.u_e.g_mac[1].rst_mt;
  repeat(15) @(negedge clk);
  if(ack!==12'hfff||!ready) $fatal(1,"STARTUP_FAIL tree release did not complete");
  $display("Q_STARTUP_PASS genuine12 reset/clock groups GOwithheld six stopped-clock epochs held tree reset");$finish;
 end
 initial begin #500;$fatal(1,"STARTUP_FAIL bounded execution timeout");end
endmodule
