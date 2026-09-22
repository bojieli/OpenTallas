`timescale 1ns/1ps
module tb_a3_hc_sinkhorn20_pipe_protocol;
 parameter integer PIPELINED_DIVIDER=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_valid=0,out_ready=0,ref_start=0;
 reg [511:0] matrix_codes={16{32'h3f800000}};
 wire in_ready,out_valid,ref_ready,ref_valid;
 wire [511:0] result_codes,ref_codes;
 wire [1:0] result_error,ref_error;
 reg [513:0] saved;
 integer state_id,resets=0,recoveries=0,stalls=0,handoffs=0,k;
 integer left_requests=0,right_requests=0;
 ot_a3_hc_sinkhorn20_rne_pipe #(.PIPELINED_DIVIDER(PIPELINED_DIVIDER)) dut(.*);
 ot_a3_hc_sinkhorn20_rne reference_impl(
 .clk(clk),.rst_n(rst_n),.in_valid(ref_start),.in_ready(ref_ready),
 .matrix_codes(matrix_codes),.out_valid(ref_valid),.out_ready(1'b0),
 .result_codes(ref_codes),.result_error(ref_error));
 always @(posedge clk)if(rst_n && dut.div_handoff && dut.div_in_ready)handoffs<=handoffs+1;
 always @(posedge clk)if(rst_n)begin
  if(dut.adder_left.valid_in)left_requests<=left_requests+1;
  if(dut.adder_right.valid_in)begin
   right_requests<=right_requests+1;
   if(dut.state!=dut.S_SUM_A_WAIT)$fatal(1,"right adder issued outside pair stage");
  end
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset_operation;begin
  rst_n=0;in_valid=0;ref_start=0;out_ready=0;tick();rst_n=1;
  repeat(12)begin tick();if(out_valid || ref_valid)$fatal(1,"cancelled result escaped");end
  if(!in_ready || !ref_ready)$fatal(1,"reset failed to release ownership");
 end endtask
 task launch(input bit with_reference);begin
  if(!in_ready || (with_reference && !ref_ready))$fatal(1,"launch while busy");
  in_valid=1;ref_start=with_reference;tick();in_valid=0;ref_start=0;
 end endtask
 task recover_and_stall;begin
  left_requests=0;right_requests=0;
  matrix_codes={16{32'h3f000000}};launch(1);
  while(!out_valid || !ref_valid)tick();
  if(result_error!=0 || {result_error,result_codes}!={ref_error,ref_codes})$fatal(1,"recovery not equivalent");
  if(left_requests!=468 || right_requests!=156)$fatal(1,"redundant adder requests left=%0d right=%0d",left_requests,right_requests);
  saved={result_error,result_codes};
  // A waiting replacement may not overwrite a held result or become accepted.
  in_valid=1;matrix_codes={16{32'h7f800000}};
  repeat(9)begin
   tick();if(in_ready || !out_valid || {result_error,result_codes}!==saved)$fatal(1,"stalled result changed");
   stalls=stalls+1;
  end
  in_valid=0;out_ready=1;tick();out_ready=0;tick();
  if(out_valid || !in_ready)$fatal(1,"result not consumed exactly once");
  recoveries=recoveries+1;
 end endtask
 initial begin
  tick();rst_n=1;tick();
  // Every active controller state, including packed output held by the sink.
  for(state_id=1;state_id<=10;state_id=state_id+1)begin
   if(state_id!=6 && state_id!=7)begin
   reset_operation();matrix_codes={16{32'h3f800000}};launch(0);
   while(dut.state!=4'(state_id))tick();
   reset_operation();resets=resets+1;recover_and_stall();
   end
  end
  // Cancel after actual same-edge replacements, not just the first DIV_WAIT.
  reset_operation();matrix_codes={16{32'h3f800000}};launch(0);
  while(!dut.div_handoff)tick();tick();
  reset_operation();resets=resets+1;recover_and_stall();
  // Error results are atomic and stable under backpressure as well.
  reset_operation();matrix_codes={16{32'h7f800000}};launch(1);
  while(!out_valid || !ref_valid)tick();
  if(result_error==0 || result_codes!=0 || {result_error,result_codes}!={ref_error,ref_codes})$fatal(1,"error result");
  saved={result_error,result_codes};
  repeat(9)begin tick();if(!out_valid || in_ready || {result_error,result_codes}!==saved)$fatal(1,"error stall");stalls=stalls+1;end
  if(handoffs==0)$fatal(1,"handoff not exercised");
  $display("PASS Sinkhorn protocol divider=%0d resets=%0d recoveries=%0d stalls=%0d handoffs=%0d",PIPELINED_DIVIDER,resets,recoveries,stalls,handoffs);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
