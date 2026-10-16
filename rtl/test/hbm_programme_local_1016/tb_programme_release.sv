`timescale 1ps/1fs
module tb_programme_release #(parameter integer MUT=0);
 localparam realtime HALF_Q=1250.0/9.0;
 reg serial_clk=0,stream_clk=0,rst_n=1,candidate_busy=0,reference_busy=0;
 integer half_tick=-1,checks=0;
 initial forever begin
  #(HALF_Q);half_tick=half_tick+1;
  serial_clk=(half_tick%8)<4;stream_clk=(half_tick%6)<3;
 end
 wire ref_release,ref_fault,got_release,got_fault;
 ot_hbm_su_bridge_release reference_leaf(.clk_serial(serial_clk),.clk_stream(stream_clk),
  .rst_n(rst_n),.rst_stream_n(rst_n),.prog_busy(reference_busy),.bridge_rst_n(ref_release),.fault(ref_fault));
 ot_hbm_su_bridge_release_local_candidate #(.DELAY(MUT==1?0:2)) candidate_leaf(
  .clk_serial(serial_clk),.clk_stream(stream_clk),.rst_n(rst_n),.rst_stream_n(rst_n),
  .prog_busy(candidate_busy),.bridge_rst_n(got_release),.fault(got_fault));
 initial begin #0.1;rst_n=0;wait(half_tick==24);#0.1;rst_n=1;end
 // External busy stimuli model only an input event, never arithmetic or data.
 // Two scheduled starts share commonE0=96 and288; no runtime status polling.
 initial begin
  wait(half_tick==(MUT==2?64:48));#0.1;candidate_busy=1;
  wait(half_tick==144);#0.1;candidate_busy=0;
  wait(half_tick==(MUT==2?256:240));#0.1;candidate_busy=1;
 end
 initial begin
  wait(half_tick==64);#0.1;reference_busy=1;
  wait(half_tick==160);#0.1;reference_busy=0;
  wait(half_tick==256);#0.1;reference_busy=1;
 end
 always @(posedge stream_clk)begin
  #0.2;
  if(half_tick>=24)begin
   if(ref_fault!==0 || ref_release!==(half_tick>=90))$fatal(1,"REFERENCE_RELEASE_INVALID half=%0d",half_tick);
   if(got_release!==ref_release || got_fault!==ref_fault)$fatal(1,"LOCAL_RELEASE_MISMATCH half=%0d MUT=%0d",half_tick,MUT);
   checks=checks+1;
  end
  if(half_tick>=330)begin $display("LOCAL_RELEASE PASS checks=%0d common_epoch96/288 referenceprime4 localprime6 twofixedserialFF",checks);$finish;end
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
