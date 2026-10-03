`timescale 1ps/1ps
module issuer_tb;
 parameter TB_ENABLE=1;
 reg clk=0,por_n=0,run_enable=1,session_valid=1;
 reg [63:0] session_id=64'h123456789abcdef0;
 reg issue_valid=0,row_barrier_ready=0,backend_go_ready=0;
 reg [238:0] issue_tuple=0;
 reg [54:0] issue_owner=55'h123;
 wire issue_ready,backend_go_valid;
 wire [238:0] backend_go_tuple,publish_tuple,retire_tuple;
 wire [54:0] backend_go_owner,publish_owner,retire_owner;
 reg producer_result_valid=0,rf_ack_valid=0,whole_terminal_valid=0,whole_reverse_valid=0;
 reg [238:0] producer_result_tuple=0,whole_terminal_tuple=0,whole_reverse_tuple=0;
 reg [54:0] rf_ack_owner=0;
 wire producer_result_ready,rf_ack_ready,whole_terminal_ready,whole_reverse_ready;
 wire publish_valid,retire_valid,busy,fault;
 reg publish_ready=0,retire_ready=0;
 ot_gpu_qwen_full_issuer_sm #(.ENABLE(TB_ENABLE),.INDEX(33)) dut(
  .clk(clk),.por_n(por_n),.run_enable(run_enable),.session_valid(session_valid),.session_id(session_id),
  .issue_valid(issue_valid),.row_barrier_ready(row_barrier_ready),.backend_go_ready(backend_go_ready),
  .issue_tuple(issue_tuple),.issue_owner(issue_owner),.issue_ready(issue_ready),.backend_go_valid(backend_go_valid),
  .backend_go_tuple(backend_go_tuple),.backend_go_owner(backend_go_owner),
  .producer_result_valid(producer_result_valid),.rf_ack_valid(rf_ack_valid),
  .whole_terminal_valid(whole_terminal_valid),.whole_reverse_valid(whole_reverse_valid),
  .producer_result_tuple(producer_result_tuple),.rf_ack_owner(rf_ack_owner),
  .whole_terminal_tuple(whole_terminal_tuple),.whole_reverse_tuple(whole_reverse_tuple),
  .producer_result_ready(producer_result_ready),.rf_ack_ready(rf_ack_ready),
  .whole_terminal_ready(whole_terminal_ready),.whole_reverse_ready(whole_reverse_ready),
  .publish_valid(publish_valid),.publish_ready(publish_ready),.publish_tuple(publish_tuple),.publish_owner(publish_owner),
  .retire_valid(retire_valid),.retire_ready(retire_ready),.retire_tuple(retire_tuple),.retire_owner(retire_owner),
  .busy(busy),.fault(fault));
 task edge_step;begin #416;clk=1;#417;clk=0;#1;end endtask
 task need(input cond,input [511:0] msg);begin if(cond!==1'b1)$fatal(1,"%s",msg);end endtask
 reg [238:0] saved;
 initial begin
  edge_step();por_n=1;edge_step();
  issue_tuple={session_id,11'd13,64'hfedcba9876543210,64'h100000000,1'b1,5'd1,11'd37,9'd4,10'd8};
  issue_valid=1;backend_go_ready=1;#1;
  if(!TB_ENABLE)begin
   row_barrier_ready=1;edge_step();need(!issue_ready && !backend_go_valid && !busy && !publish_valid && !retire_valid,"defaultoff falsely GO/publish/retire");
   $display("PASS_DEFAULT_OFF_FULL_ISSUER");$finish;
  end
  need(!issue_ready && !backend_go_valid,"no seven-row barrier admitted GO");
  edge_step();need(!busy,"blocked GO captured identity");
  row_barrier_ready=1;backend_go_ready=0;#1;need(backend_go_valid && !issue_ready,"actual backend readiness not respected");
  edge_step();need(!busy,"unaccepted backend GO captured");backend_go_ready=1;#1;
  need(issue_ready && backend_go_valid,"legal GO not offered");saved=issue_tuple;edge_step();
  need(busy && !issue_ready,"accepted whole GO not retained");issue_valid=0;
  issue_tuple=0;issue_owner=0; // live request changes must not retag completion.
  whole_terminal_tuple=saved;whole_terminal_valid=1;#1;need(whole_terminal_ready,"actual whole terminal refused");edge_step();whole_terminal_valid=0;#1;
  repeat(2)begin edge_step();need(busy && !retire_valid && !publish_valid,"terminal alone retired/published");end
  rf_ack_owner=55'h123;rf_ack_valid=1;#1;need(rf_ack_ready,"actual matching RFcommonACK refused");edge_step();rf_ack_valid=0;#1;
  need(!publish_valid,"RFACK alone published without fullproducer");
  producer_result_tuple=saved;producer_result_valid=1;#1;need(producer_result_ready,"fullproducer refused");edge_step();producer_result_valid=0;#1;
  need(publish_valid && publish_tuple==saved && publish_owner==55'h123,"publication not saved actual owner");
  repeat(2)begin edge_step();need(publish_valid && busy && !retire_valid,"held publication lost debt");end
  publish_ready=1;edge_step();publish_ready=0;need(!publish_valid && busy && !retire_valid,"publication ignored reverse debt");
  whole_reverse_tuple=saved;whole_reverse_valid=1;#1;need(whole_reverse_ready,"whole reverse refused");edge_step();whole_reverse_valid=0;#1;
  need(retire_valid && retire_tuple==saved && retire_owner==55'h123,"matched whole closure not available");
  repeat(2)begin edge_step();need(retire_valid && busy && !issue_ready,"held row retirement forgotten");end
  retire_ready=1;edge_step();retire_ready=0;need(!busy && !fault,"matched row retirement failed");
  issue_tuple=saved;issue_owner=55'h123;issue_valid=1;edge_step();issue_valid=0;
  whole_terminal_tuple=saved^239'h100000;whole_terminal_valid=1;#1;
  need(!whole_terminal_ready,"wrong whole identity consumed");edge_step();whole_terminal_valid=0;#1;
  need(fault && busy && !publish_valid && !retire_valid && !issue_ready,"wrong whole identity did not retain fault/debt");
  $display("PASS_FULL_ISSUER_ACCEPTED_GO_PUBLICATION_WHOLE_REVERSE_FAULT");$finish;
 end
endmodule
