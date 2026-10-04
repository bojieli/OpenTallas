`timescale 1ps/1ps
module issuer_r2_tb;
 parameter TB_ENABLE=1;
 reg clk=0,por_n=0;
 reg issue_valid=0,row_barrier_ready=0,backend_go_ready=0,inputs_bound_valid=0;
 reg [238:0] issue_tuple=0,inputs_bound_tuple=0;
 reg [6:0] inputs_bound_mask=7'b101;
 reg [31:0] issue_output_page_mask=3;
 reg [54:0] issue_owner=55'h123;
 wire issue_ready,backend_go_valid,inputs_bound_ready,busy,fault;
 wire [238:0] backend_go_tuple,publish_tuple,frame_retire_tuple,input_terminal_tuple,input_reverse_tuple;
 wire [54:0] backend_go_owner,publish_owner,frame_retire_owner;
 wire [31:0] publish_page_mask;
 wire [6:0] input_terminal_mask,input_reverse_mask;
 reg producer_visible_valid=0,rf_range_ack_valid=0,whole_terminal_valid=0,whole_reverse_valid=0;
 reg [238:0] producer_visible_tuple=0,rf_range_ack_tuple=0,whole_terminal_tuple=0,whole_reverse_tuple=0;
 reg [54:0] rf_range_ack_owner=0;
 reg [31:0] rf_range_ack_page_mask=0;
 wire producer_visible_ready,rf_range_ack_ready,whole_terminal_ready,whole_reverse_ready;
 wire publish_valid,frame_retire_valid,input_terminal_valid,input_reverse_valid;
 reg publish_ready=0,frame_retire_ready=0,input_terminal_ready=0,input_reverse_ready=0;
 ot_gpu_qwen_full_issuer_sm_r2 #(.ENABLE(TB_ENABLE),.INDEX(33)) dut(
  .clk(clk),.por_n(por_n),.run_enable(1'b1),.session_valid(1'b1),.session_id(64'h1234),
  .issue_valid(issue_valid),.row_barrier_ready(row_barrier_ready),.backend_go_ready(backend_go_ready),
  .issue_tuple(issue_tuple),.issue_owner(issue_owner),.inputs_bound_valid(inputs_bound_valid),
  .inputs_bound_tuple(inputs_bound_tuple),.inputs_bound_mask(inputs_bound_mask),.issue_output_page_mask(issue_output_page_mask),
  .inputs_bound_ready(inputs_bound_ready),.issue_ready(issue_ready),.backend_go_valid(backend_go_valid),
  .backend_go_tuple(backend_go_tuple),.backend_go_owner(backend_go_owner),
  .producer_visible_valid(producer_visible_valid),.producer_visible_tuple(producer_visible_tuple),
  .rf_range_ack_valid(rf_range_ack_valid),.rf_range_ack_owner(rf_range_ack_owner),.rf_range_ack_tuple(rf_range_ack_tuple),.rf_range_ack_page_mask(rf_range_ack_page_mask),
  .whole_terminal_valid(whole_terminal_valid),.whole_terminal_tuple(whole_terminal_tuple),
  .whole_reverse_valid(whole_reverse_valid),.whole_reverse_tuple(whole_reverse_tuple),
  .producer_visible_ready(producer_visible_ready),.rf_range_ack_ready(rf_range_ack_ready),
  .whole_terminal_ready(whole_terminal_ready),.whole_reverse_ready(whole_reverse_ready),
  .publish_valid(publish_valid),.publish_ready(publish_ready),.publish_tuple(publish_tuple),.publish_owner(publish_owner),.publish_page_mask(publish_page_mask),
  .frame_retire_valid(frame_retire_valid),.frame_retire_ready(frame_retire_ready),.frame_retire_tuple(frame_retire_tuple),.frame_retire_owner(frame_retire_owner),
  .input_terminal_valid(input_terminal_valid),.input_terminal_ready(input_terminal_ready),.input_terminal_tuple(input_terminal_tuple),.input_terminal_mask(input_terminal_mask),
  .input_reverse_valid(input_reverse_valid),.input_reverse_ready(input_reverse_ready),.input_reverse_tuple(input_reverse_tuple),.input_reverse_mask(input_reverse_mask),.busy(busy),.fault(fault));
 task step;begin #416;clk=1;#417;clk=0;#1;end endtask
 task need(input cond,input [511:0] msg);begin if(cond!==1'b1)$fatal(1,"%s",msg);end endtask
 reg [238:0] saved;
 initial begin
  step();por_n=1;step();
  issue_tuple={64'h1234,11'd13,64'hfedcba9876543210,64'h100000000,1'b1,5'd1,11'd37,9'd4,10'd8};
  issue_valid=1;row_barrier_ready=1;backend_go_ready=1;#1;
  if(!TB_ENABLE)begin inputs_bound_valid=1;inputs_bound_tuple=issue_tuple;step();need(!busy&&!issue_ready&&!backend_go_valid&&!publish_valid&&!frame_retire_valid,"defaultoff credit");$display("PASS_DEFAULT_OFF_RANGE_ISSUER");$finish;end
  need(!backend_go_valid&&!issue_ready,"unbound inputs issued GO");
  inputs_bound_valid=1;inputs_bound_tuple=issue_tuple^239'h100000;#1;need(!issue_ready&&!backend_go_valid,"wrong input tuple issued GO");
  inputs_bound_tuple=issue_tuple;#1;need(issue_ready&&backend_go_valid&&inputs_bound_ready,"bound actual GO refused");saved=issue_tuple;step();
  issue_valid=0;issue_tuple=0;inputs_bound_mask=0;issue_output_page_mask=0;inputs_bound_valid=0;#1;need(busy&&!issue_ready,"accepted frame lost bindings");
  producer_visible_tuple=saved;producer_visible_valid=1;#1;need(producer_visible_ready,"whole producer refused");step();producer_visible_valid=0;#1;
  need(!publish_valid,"producer alone published");
  rf_range_ack_page_mask=1;rf_range_ack_owner=55'h123;rf_range_ack_tuple=saved;
  repeat(2)begin step();need(!publish_valid,"partial raw page ACK published range");end
  rf_range_ack_page_mask=3;rf_range_ack_valid=1;#1;need(rf_range_ack_ready,"complete matched page aggregate refused");step();rf_range_ack_valid=0;#1;
  need(publish_valid&&publish_page_mask==3&&publish_tuple==saved,"saved allpage publication missing");
  publish_ready=1;step();publish_ready=0;
  whole_terminal_tuple=saved;whole_terminal_valid=1;#1;need(whole_terminal_ready,"whole terminal refused");step();whole_terminal_valid=0;#1;
  need(input_terminal_valid&&input_terminal_mask==5&&input_terminal_tuple==saved&&!frame_retire_valid,"input row terminal not held or frame retired early");
  whole_reverse_tuple=saved;whole_reverse_valid=1;#1;need(whole_reverse_ready,"whole reverse refused");step();whole_reverse_valid=0;#1;
  need(input_reverse_valid&&input_reverse_mask==5&&!frame_retire_valid,"bound input reverse/debt lost");
  repeat(2)step();input_terminal_ready=1;step();input_terminal_ready=0;need(!frame_retire_valid,"reverse input notification omitted");
  input_reverse_ready=1;step();input_reverse_ready=0;
  need(frame_retire_valid&&frame_retire_tuple==saved&&frame_retire_owner==55'h123,"matched operation frame closure missing");
  repeat(2)begin step();need(busy&&frame_retire_valid,"frame sink backpressure lost debt");end
  frame_retire_ready=1;step();frame_retire_ready=0;need(!busy&&!fault,"frame retirement failed");
  // No source-lease retirement port/event exists in this issuer.
  issue_tuple=saved;inputs_bound_tuple=saved;inputs_bound_valid=1;inputs_bound_mask=5;issue_output_page_mask=3;issue_valid=1;step();issue_valid=0;
  rf_range_ack_page_mask=1;rf_range_ack_valid=1;#1;need(!rf_range_ack_ready,"incomplete aggregate accepted as visibility");step();rf_range_ack_valid=0;#1;
  need(fault&&busy&&!publish_valid&&!frame_retire_valid,"bad range aggregate did not retain fault/debt");
  $display("PASS_BOUND_INPUT_RANGE_PUBLICATION_FRAME_ONLY_ISSUER");$finish;
 end
endmodule
