`timescale 1ns/1ps
module tb;
 reg clk=0,power_on_reset_n=0,warm_reset=0;
 always #5 clk=~clk;
 reg go_valid=0;wire go_ready;reg [238:0] go_tuple=0;reg [54:0] go_owner=55'h123456;
 reg [31:0] go_input_bits=32'h00012345;
 reg [1:0] write_accept=0,query_valid=0,query_owner_retained=0,ACK_accept=0,RF_drained=0;
 reg [17:0] write_slots=0,query_slots=0,ACK_slots=0;
 reg [91:0] write_owners=0,query_owners=0,ACK_owners=0;
 reg [8191:0] write_data=0;reg [477:0] query_tuples=0;
 reg root_ACK_accept=0;reg [238:0] root_ACK_tuple=0;reg [54:0] root_ACK_owner=0;
 reg close_valid=0;wire close_ready;reg [238:0] close_tuple=0;reg [54:0] close_owner=0;
 wire [1:0] initial_write_admit;wire provider_quiesce;
 wire visible_valid,terminal_valid,reverse_valid;reg visible_ready=0,terminal_ready=0,reverse_ready=0;
 wire [238:0] event_tuple;wire [54:0] event_owner;
 reg frame_retire_accept=0;reg [238:0] frame_retire_tuple=0;reg [54:0] frame_retire_owner=0;
 wire busy,fault;integer checks=0;
 ot_gpu_qwen_initial_completion #(.ENABLE(1)) dut(.*);
 task step;begin @(posedge clk);#1;end endtask
 task must(input bit ok,input [511:0] message_text);begin checks=checks+1;if(!ok)$fatal(1,"FAIL %s",message_text);end endtask
 task reset_case;begin
  @(negedge clk);power_on_reset_n=0;go_valid=0;write_accept=0;ACK_accept=0;
  root_ACK_accept=0;close_valid=0;frame_retire_accept=0;warm_reset=0;
  query_valid=0;query_owner_retained=0;RF_drained=0;visible_ready=0;terminal_ready=0;reverse_ready=0;
  step;@(negedge clk);power_on_reset_n=1;
  go_tuple=(239'd4<<175)|(239'd2047<<164)|(239'd0<<19)|(239'd32<<10)|239'd33;
  query_tuples={go_tuple,go_tuple};write_slots={9'd32,9'd32};query_slots=write_slots;ACK_slots=write_slots;
  query_owners={46'd701,46'd700};write_owners=query_owners;ACK_owners=query_owners;
  write_data=0;write_data[0+:32]=go_input_bits;write_data[4096+:32]=go_input_bits;
  root_ACK_tuple=go_tuple;root_ACK_owner=go_owner;close_tuple=go_tuple;close_owner=go_owner;
  frame_retire_tuple=go_tuple;frame_retire_owner=go_owner;
  go_valid=1;#1;must(go_ready,"source INITIAL offer");step;go_valid=0;
  must(busy&&!fault&&initial_write_admit==3,"captured INITIAL scope");
 end endtask
 task page_write;begin query_valid=3;query_owner_retained=3;write_accept=3;step;write_accept=0;end endtask
 task page_ACK;begin ACK_accept=3;step;ACK_accept=0;end endtask
 task aggregate;begin root_ACK_accept=1;step;root_ACK_accept=0;end endtask
 task close_epoch;begin close_valid=1;#1;must(close_ready,"close captured root");step;close_valid=0;end endtask
 initial begin
 reset_case;page_write;page_ACK;aggregate;close_epoch;
 must(provider_quiesce&&initial_write_admit==0&&!visible_valid,"close gates new writes and waits drain");
 RF_drained=3;repeat(2)step;must(!visible_valid,"live query seats prohibit visibility");
 query_valid=0;query_owner_retained=0;step;
 must(visible_valid&&event_tuple==go_tuple&&event_owner==go_owner,"actual allbank visibility");
 repeat(2)step;must(visible_valid&&!terminal_valid,"held visibility backpressure");
 visible_ready=1;step;visible_ready=0;must(terminal_valid&&!reverse_valid,"terminal follows actual visibility capture");
 repeat(2)step;must(terminal_valid,"held terminal");terminal_ready=1;step;terminal_ready=0;
 must(reverse_valid&&busy,"reverse retained");repeat(2)step;must(reverse_valid,"held reverse");
 reverse_ready=1;step;reverse_ready=0;must(busy&&!reverse_valid,"wait actual frame retire");
 frame_retire_accept=1;step;frame_retire_accept=0;must(!busy&&!fault,"actual frame retirement only");
 reset_case;page_write;ACK_owners[0+:46]=46'd999;page_ACK;
 must(fault&&!visible_valid&&!terminal_valid,"wrong ACK owner failclosed");
 reset_case;page_write;page_ACK;close_epoch;query_valid=0;query_owner_retained=0;RF_drained=3;
 repeat(3)step;must(!visible_valid&&!terminal_valid,"host two ACKs not protected aggregate proof");
 reset_case;query_valid=3;query_owner_retained=3;query_tuples[0+:239]=go_tuple^239'd1;
 write_accept=1;step;write_accept=0;must(fault,"wrong query/root refusal");
 reset_case;page_write;page_ACK;aggregate;close_epoch;write_accept=1;step;write_accept=0;
 must(fault&&!visible_valid,"write after CLOSE failclosed");
 reset_case;page_write;page_ACK;aggregate;close_epoch;warm_reset=1;step;warm_reset=0;
 must(fault&&busy&&!visible_valid,"warm reset retains quarantine debt");
 reset_case;page_write;page_ACK;aggregate;close_epoch;
 dut.code[0][0]=~dut.code[0][0];#1;must(!visible_valid,"CE stalls not free decode");step;#1;
 must(!fault,"verified CE scrub preserves context");
 dut.code[0][0]=~dut.code[0][0];dut.code[0][1]=~dut.code[0][1];#1;
 must(fault&&!visible_valid&&!terminal_valid,"DUE rejects completion");
 $display("PASS initial_completion checks=%0d",checks);$finish;
 end
endmodule
