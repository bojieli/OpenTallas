`timescale 1ps/1ps
module tb_boot_branch;
 reg clk=0, fclk=0, rclk=0;
 integer phase=83, pad=0, efall=1, n=0, checks=0, boots=0;
 initial begin
  if (!$value$plusargs("PHASE=%d",phase)) phase=83;
  if (!$value$plusargs("PAD=%d",pad)) pad=0;
  if (!$value$plusargs("EFALL=%d",efall)) efall=1;
 end
 always begin #416 clk=1; #417 clk=0; end
 always @(clk) fclk <= #25 clk;
 initial begin #2; #(phase); forever begin #416 rclk=1; #417 rclk=0; end end
 always @(posedge clk) n <= n+1;
 wire raw_parent = (n%240 >= 2) && (n%240 < 220);
 wire p_start = (n%240 >= 20) && (n%240 < 220);
 wire receiver_start = (n%240 >= 10+pad) && (n%240 < 220);
 reg baseline_raw;
 always @(posedge clk) baseline_raw <= raw_parent;
 wire baseline_start, baseline_d, s0, north_start, north_raw, off_start, off_raw;
 ot_dp_landing_origin_s #(.PADW(1),.BOOT_BRANCH_EXPORT(1)) origin (
  .clk(clk),.rst_raw_n(baseline_raw),.p_start(p_start),.strap_efall(efall[0]),
  .strap_pad(pad[0]),.start(baseline_start),.start_d(baseline_d),.boot_s0(s0));
 ot_dp_landing_boot_branch #(.ENABLE(1)) branch (
  .clk(clk),.baseline_start(baseline_start),.baseline_raw(baseline_raw),
  .origin_s0(s0),.raw_parent(raw_parent),.strap_pad(pad[0]),
  .north_start(north_start),.north_raw(north_raw));
 ot_dp_landing_boot_branch off_branch (
  .clk(clk),.baseline_start(baseline_start),.baseline_raw(baseline_raw),
  .origin_s0(s0),.raw_parent(raw_parent),.strap_pad(pad[0]),
  .north_start(off_start),.north_raw(off_raw));
 wire old_fstart,new_fstart;
 ot_dp_landing_relay old_face (.clk(clk),.rst_raw_n(baseline_raw),.d(baseline_d),.q(old_fstart));
 ot_dp_landing_relay new_face (.clk(clk),.rst_raw_n(north_raw),.d(north_start),.q(new_fstart));
 reg old_fstart_prev;
 always @(posedge clk) begin
  old_fstart_prev <= old_fstart;
  #1;
  if (n>4) begin
   if (north_raw !== baseline_raw) $fatal(1,"RESET_COPY_MISMATCH");
   if (north_start !== baseline_start) $fatal(1,"INTERNAL_START_MISMATCH");
   if (off_start !== baseline_start || off_raw !== baseline_raw) $fatal(1,"DEFAULT_OFF_MISMATCH");
   if (baseline_raw && new_fstart !== old_fstart_prev) $fatal(1,"FORWARDED_PHASE_MISMATCH");
  end
 end
 reg [15:0] payload=16'h71ad;
 always @(negedge clk) payload <= payload+16'h31;
 wire [15:0] qold,qnew;
 wire rold,rnew,fold,fnew;
`ifdef BOOT_MUTANT_K
 localparam [5:0] NEWK=6'd14;
`else
 localparam [5:0] NEWK=6'd15;
`endif
 ot_dp_clk_landing_cas #(.W(16),.DEPTH(4)) old_ring (
  .fclk(fclk),.t_rst_n(old_fstart),.clk(rclk),.rst_n(receiver_start),.strap_k(6'd14),
  .d(payload),.q(qold),.ready(rold),.fault(fold));
 ot_dp_clk_landing_cas #(.W(16),.DEPTH(4)) new_ring (
  .fclk(fclk),.t_rst_n(new_fstart),.clk(rclk),.rst_n(receiver_start),.strap_k(NEWK),
  .d(payload),.q(qnew),.ready(rnew),.fault(fnew));
 always @(posedge rclk) begin
  #2;
  if (n%240>80 && n%240<215) begin
   if (fold || fnew || !rold || !rnew) $fatal(1,"RING_NOT_QUALIFIED n=%0d fault=%b/%b ready=%b/%b",n,fold,fnew,rold,rnew);
   if (qold !== qnew) $fatal(1,"PRODUCTION_DATA_MISMATCH n=%0d old=%h new=%h",n,qold,qnew);
   checks=checks+1;
  end
 end
 initial begin
  #600000;
  if (checks<300) $fatal(1,"VACUOUS_CHECKS %0d",checks);
  $display("BOOT_BRANCH PASS phase=%0d pad=%0d efall=%0d production_checks=%0d boots=3 period_ps=833",phase,pad,efall,checks);
  $finish;
 end
endmodule
