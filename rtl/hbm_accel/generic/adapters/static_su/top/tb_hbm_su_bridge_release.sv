`timescale 1ns/1ps
// Bench of ot_hbm_su_bridge_release (H-NETLIST 2026-10-15) on the exact 3:4 quantum lattice of
// tb_hbm_su_native_multirate_top (serial = (ht%8)<4, stream = (ht%6)<3, epoch 24 half-ticks).
// Reference: a second real ot_hbm_su_multirate_bridge reset by the IDEAL release used by the whole-SU multirate proof
// (bridge_rst_n raised at half-tick E0-1). The DUT bridge is reset by the leaf. Both bridges get identical random
// serial/stream traffic; every output of both must match on every edge from reset to the end (the leaf release must be
// functionally identical to the proven phase-zero release). prog_busy follows ot_hbm_su_programme: start sampled at the
// serial edge E0-32 half-ticks, busy high after it, low after done.
// Runs: +RUNS=n programme runs, each epoch-aligned (no fault allowed); +MISALIGN restart one serial edge off (fault
// REQUIRED); -P...MUT=1/2 release one stream edge early/late (outputs must mismatch -> FAIL).
module tb_hbm_su_bridge_release;
 parameter integer MUT=0;
 localparam realtime HALF_Q=1250.0/9.0;
 reg serial_clk=0,stream_clk=0,rst_n=0,ideal_rst_n=0,prog_busy=0;
 integer half_tick=-1,e0=-1,errors=0,cmp_edges=0,runs=2,misalign=0;
 initial forever begin
  #(HALF_Q);half_tick=half_tick+1;
  serial_clk=(half_tick%8)<4;stream_clk=(half_tick%6)<3;
 end
 wire bridge_rst_n,leaf_fault;
 ot_hbm_su_bridge_release #(.MUT(MUT)) dut(.clk_serial(serial_clk),.clk_stream(stream_clk),.rst_n(rst_n),
  .rst_stream_n(rst_n),.prog_busy(prog_busy),.bridge_rst_n(bridge_rst_n),.fault(leaf_fault));
 // identical random traffic into both bridges
 reg [16:0] s_rq=0; reg [280:0] s_wq=0; reg [256:0] t_rr=0; reg t_done=0;
 always @(posedge serial_clk) begin s_rq<=$random; s_wq<={$random,$random,$random,$random,$random,$random,$random,$random,$random}; end
 always @(posedge stream_clk) begin t_rr<={$random,$random,$random,$random,$random,$random,$random,$random,$random}; t_done<=$random; end
 wire [256:0] a_rr,b_rr; wire a_done,b_done,a_f,b_f; wire [16:0] a_rq,b_rq; wire [280:0] a_wq,b_wq;
 ot_hbm_su_multirate_bridge u_ref(.serial_clk(serial_clk),.stream_clk(stream_clk),.rst_n(ideal_rst_n),
  .serial_rq(s_rq),.serial_wq(s_wq),.serial_rr(a_rr),.serial_done(a_done),.stream_rq(a_rq),.stream_wq(a_wq),
  .stream_rr(t_rr),.stream_done(t_done),.fault(a_f));
 ot_hbm_su_multirate_bridge u_dut(.serial_clk(serial_clk),.stream_clk(stream_clk),.rst_n(bridge_rst_n),
  .serial_rq(s_rq),.serial_wq(s_wq),.serial_rr(b_rr),.serial_done(b_done),.stream_rq(b_rq),.stream_wq(b_wq),
  .stream_rr(t_rr),.stream_done(t_done),.fault(b_f));
 always @(negedge serial_clk) if(rst_n) begin
  cmp_edges=cmp_edges+1;
  if(a_rr!==b_rr||a_done!==b_done)begin errors=errors+1; if(errors<5)$display("serial mismatch ht=%0d",half_tick); end
 end
 always @(negedge stream_clk) if(rst_n) begin
  cmp_edges=cmp_edges+1;
  if(a_rq!==b_rq||a_wq!==b_wq||a_f!==b_f)begin errors=errors+1; if(errors<5)$display("stream mismatch ht=%0d",half_tick); end
 end
 integer rel_ht=-1;
 always @(posedge bridge_rst_n) rel_ht=half_tick;
 task automatic run_programme(input integer start_e0,input integer shift);
  // start sampled at serial edge start_e0-32+shift (shift multiple of 8); busy high after it for 200 half-ticks
  wait(half_tick==start_e0-32+shift);#1;prog_busy=1;
  wait(half_tick==start_e0-32+shift+200);#1;prog_busy=0;
 endtask
 initial begin
  if($value$plusargs("RUNS=%d",runs));
  misalign=$test$plusargs("MISALIGN");
  repeat(5)@(negedge serial_clk);rst_n=1;
  e0=24*((half_tick+120)/24);
  fork
   begin wait(half_tick==e0-1);ideal_rst_n=1; end
   run_programme(e0,0);
  join
  for(integer r=1;r<runs;r=r+1)run_programme(e0+24*(20*r),(misalign&&r==runs-1)?8:0);
  wait(half_tick==e0+24*(20*runs)+96);#2;
  $display("BRIDGE_RELEASE release_ht=E0%0d window=[E0-6,E0-1] cmp_edges=%0d errors=%0d leaf_fault=%0d bridge_fault=%0d/%0d",
           rel_ht-e0,cmp_edges,errors,leaf_fault,a_f,b_f);
  if(rel_ht<e0-6||rel_ht>e0-1)begin errors=errors+1;$display("release outside window"); end
  // random traffic violates the bridge slot protocol on purpose: both bridges must fault identically (compared per edge)
  if(misalign)begin
   if(!leaf_fault)begin errors=errors+1;$display("misaligned restart not faulted"); end
  end else if(leaf_fault)errors=errors+1;
  if(errors)$fatal(1,"BRIDGE_RELEASE FAIL errors=%0d",errors);
  $display("BRIDGE_RELEASE PASS");$finish;
 end
endmodule
