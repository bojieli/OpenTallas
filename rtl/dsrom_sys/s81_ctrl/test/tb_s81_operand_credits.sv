`timescale 1ns/1ps
module tb_s81_operand_credits;
 reg clk=0, rst=0, cv=0, credit=0, ready=0;
 always #0.4166 clk=~clk;
 reg [83:0] cd=0;
 wire ev,dv,fault,online; wire [83:0] ed; wire [7:0] dt;
 integer starts=0, errors=0;
 ot_s81_engine_adapter #(.INPUT_CREDITS(1)) dut (
  .c_clk(clk),.c_rst_n(rst),.c_cmd_v(cv),.c_cmd_d(cd),
  .c_done_v(dv),.c_done_tag(dt),.fault(fault),.online(online),
  .e_clk(clk),.e_rst_n(rst),.e_cmd_v(ev),.e_cmd_d(ed),
  .e_cmd_ready(ready),.e_inputs_present(credit),.e_done_v(1'b0),.e_done_tag(8'd0));
 always @(posedge clk) if(rst && ev && ready) begin
  if(ed[6:0] != starts) errors=errors+1;
  starts=starts+1;
 end
 task pulse_credit;
  @(negedge clk); credit=1; @(negedge clk); credit=0;
 endtask
 initial begin
  repeat(8) @(negedge clk); rst=1; wait(online);
  // Credits arrive before commands and persist through an engine stall.
  pulse_credit(); pulse_credit();
  for(integer i=0;i<3;i++) begin @(negedge clk);cv=1;cd=i;end
  @(negedge clk);cv=0;
  repeat(24) @(negedge clk);
  if(starts!=0 || dut.input_tokens!=2) errors++;
  ready=1; repeat(24) @(negedge clk);
  if(starts!=2 || ev || dut.input_tokens!=0) errors++;
  pulse_credit(); repeat(24) @(negedge clk);
  if(starts!=3 || fault || dut.input_tokens!=0) errors++;
  // Reset discards the previous epoch's unconsumed tokens.
  pulse_credit(); rst=0; repeat(8) @(negedge clk); rst=1;
  wait(online); repeat(8) @(negedge clk);
  if(dut.input_tokens!=0 || ev || fault) errors++;
  // An over-credit faults rather than wrapping the token count to zero.
  repeat(9) pulse_credit(); repeat(8) @(negedge clk);
  if(!fault || dut.input_tokens!=8) errors++;
  $display("OPERAND_CREDITS %s starts=%0d errors=%0d",errors==0?"PASS":"FAIL",starts,errors);
  $finish;
 end
endmodule
