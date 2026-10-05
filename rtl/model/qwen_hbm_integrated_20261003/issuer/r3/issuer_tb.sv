`timescale 1ps/1ps
// Actual coded issuer leaf. Allocator/engine events are directed fixtures.
// This does not test producer arithmetic or source census completeness.
module issuer_r3_tb;
 parameter TB_ENABLE=1;
 reg clk=0,por_n=0,run_enable=1,producer_binding_ready=1;
 reg inputs_bound_valid=0,issue_valid=0,row_barrier_ready=1,backend_go_ready=1,initial_go_ready=0;
 reg [3:0] required_output_rows=0;
 reg [238:0] issue_tuple=0,inputs_bound_tuple=0;
 reg [6:0] inputs_bound_mask=0;
 reg [31:0] issue_output_page_mask=0;
 reg [54:0] issue_owner=55'h123;
 wire issue_ready,backend_go_valid,initial_go_valid,inputs_bound_ready,busy,fault;
 wire [238:0] backend_go_tuple,initial_go_tuple,publish_tuple,frame_retire_tuple,input_terminal_tuple,input_reverse_tuple;
 wire [54:0] backend_go_owner,initial_go_owner,publish_owner,frame_retire_owner;
 wire [31:0] publish_page_mask;
 wire [6:0] input_terminal_mask,input_reverse_mask;
 reg producer_visible_valid=0,rf_range_ack_valid=0,whole_terminal_valid=0,whole_reverse_valid=0;
 reg [238:0] producer_visible_tuple=0,rf_range_ack_tuple=0,whole_terminal_tuple=0,whole_reverse_tuple=0;
 reg [54:0] rf_range_ack_owner=0;
 reg [31:0] rf_range_ack_page_mask=0;
 wire producer_visible_ready,rf_range_ack_ready,whole_terminal_ready,whole_reverse_ready;
 wire publish_valid,frame_retire_valid,input_terminal_valid,input_reverse_valid;
 reg publish_ready=0,frame_retire_ready=0,input_terminal_ready=0,input_reverse_ready=0;
 integer native_go_count=0,initial_go_count=0;
 always @(posedge clk)begin
  if(backend_go_valid&&backend_go_ready)native_go_count=native_go_count+1;
  if(initial_go_valid&&initial_go_ready)initial_go_count=initial_go_count+1;
 end
 ot_gpu_qwen_full_issuer_sm_r3 #(.ENABLE(TB_ENABLE),.ENABLE_TYPED(1),.INDEX(0)) dut(
 .clk(clk),.por_n(por_n),.run_enable(run_enable),.session_valid(1'b1),.session_id(64'h1234),
 .producer_binding_ready(producer_binding_ready),.required_output_rows(required_output_rows),.initial_go_ready(initial_go_ready),.initial_go_valid(initial_go_valid),.initial_go_tuple(initial_go_tuple),.initial_go_owner(initial_go_owner),
 .inputs_bound_valid(inputs_bound_valid),.inputs_bound_tuple(inputs_bound_tuple),.inputs_bound_mask(inputs_bound_mask),.issue_output_page_mask(issue_output_page_mask),.inputs_bound_ready(inputs_bound_ready),
 .issue_valid(issue_valid),.row_barrier_ready(row_barrier_ready),.backend_go_ready(backend_go_ready),.issue_tuple(issue_tuple),.issue_owner(issue_owner),.issue_ready(issue_ready),.backend_go_valid(backend_go_valid),.backend_go_tuple(backend_go_tuple),.backend_go_owner(backend_go_owner),
 .producer_visible_valid(producer_visible_valid),.producer_visible_tuple(producer_visible_tuple),.producer_visible_ready(producer_visible_ready),
 .rf_range_ack_valid(rf_range_ack_valid),.rf_range_ack_tuple(rf_range_ack_tuple),.rf_range_ack_owner(rf_range_ack_owner),.rf_range_ack_page_mask(rf_range_ack_page_mask),.rf_range_ack_ready(rf_range_ack_ready),
 .whole_terminal_valid(whole_terminal_valid),.whole_terminal_tuple(whole_terminal_tuple),.whole_terminal_ready(whole_terminal_ready),.whole_reverse_valid(whole_reverse_valid),.whole_reverse_tuple(whole_reverse_tuple),.whole_reverse_ready(whole_reverse_ready),
 .publish_valid(publish_valid),.publish_ready(publish_ready),.publish_tuple(publish_tuple),.publish_owner(publish_owner),.publish_page_mask(publish_page_mask),
 .frame_retire_valid(frame_retire_valid),.frame_retire_ready(frame_retire_ready),.frame_retire_tuple(frame_retire_tuple),.frame_retire_owner(frame_retire_owner),
 .input_terminal_valid(input_terminal_valid),.input_terminal_ready(input_terminal_ready),.input_terminal_tuple(input_terminal_tuple),.input_terminal_mask(input_terminal_mask),
 .input_reverse_valid(input_reverse_valid),.input_reverse_ready(input_reverse_ready),.input_reverse_tuple(input_reverse_tuple),.input_reverse_mask(input_reverse_mask),.busy(busy),.fault(fault));
 task step;begin #416;clk=1;#417;clk=0;#1;end endtask
 task need(input cond,input [511:0] msg);begin if(cond!==1'b1)$fatal(1,"%s",msg);end endtask
 function [238:0] tuple(input [10:0] pc,version,input [8:0] first,input [9:0] ending);
 begin tuple={64'h1234,pc,64'hfedcba9876543210,64'h100000001,1'b0,5'd0,version,first,ending};end endfunction
 reg [238:0] saved;reg [6:0] saved_mask;
 task finish_root;
 begin
  // Matching source-qualified aggregate is not sufficient without engine visibility.
  rf_range_ack_tuple=saved;rf_range_ack_owner=issue_owner;rf_range_ack_page_mask=issue_output_page_mask;
  rf_range_ack_valid=1;#1;need(rf_range_ack_ready,"aggregate refused");step();rf_range_ack_valid=0;#1;
  need(!publish_valid,"ACK alone published");
  run_enable=0;producer_visible_tuple=saved;producer_visible_valid=1;step();need(!producer_visible_ready&&!publish_valid&&busy,"pause lost root");run_enable=1;
  producer_binding_ready=0;step();need(!producer_visible_ready&&!publish_valid,"allocator notready lost visibility");producer_binding_ready=1;#1;need(producer_visible_ready,"visibility refused");step();producer_visible_valid=0;#1;
  need(publish_valid&&publish_tuple==saved&&publish_page_mask==issue_output_page_mask,"publication tuple/mask mismatch");
  repeat(2)begin step();need(publish_valid&&busy,"publication backpressure lost root");end
  publish_ready=1;step();publish_ready=0;#1;
  whole_terminal_valid=1;whole_terminal_tuple=saved;step();whole_terminal_valid=0;#1;
  need(input_terminal_valid&&input_terminal_tuple==saved&&input_terminal_mask==saved_mask&&!frame_retire_valid,"saved input terminal mismatch");
  whole_reverse_valid=1;whole_reverse_tuple=saved;step();whole_reverse_valid=0;#1;
  need(input_reverse_valid&&input_reverse_mask==saved_mask&&!frame_retire_valid,"saved reverse mismatch");
  input_terminal_ready=1;step();input_terminal_ready=0;#1;need(!frame_retire_valid,"retired before input reverse accepted");
  input_reverse_ready=1;step();input_reverse_ready=0;#1;need(frame_retire_valid&&frame_retire_tuple==saved&&frame_retire_owner==issue_owner,"frame closure absent");
  repeat(2)begin step();need(busy&&frame_retire_valid,"frame backpressure lost debt");end
  frame_retire_ready=1;step();frame_retire_ready=0;#1;need(!busy&&!fault,"frame failed retirement");
 end endtask
 initial begin
  step();por_n=1;step();
  issue_tuple=tuple(10,2047,0,0);inputs_bound_tuple=issue_tuple;issue_valid=1;inputs_bound_valid=1;#1;
  if(!TB_ENABLE)begin initial_go_ready=1;repeat(3)step();need(!backend_go_valid&&!initial_go_valid&&!issue_ready&&!busy&&!publish_valid,"defaultoff accepted");$display("PASS_DEFAULT_OFF_TYPED_ISSUER");$finish;end
  // A zero mask must be accompanied by the exact empty sentinel and source count.
  required_output_rows=1;#1;need(!issue_ready,"empty accepted nonempty source count");required_output_rows=0;
  issue_tuple=tuple(10,2046,0,0);inputs_bound_tuple=issue_tuple;#1;need(!issue_ready,"wrong empty sentinel accepted");
  issue_tuple=tuple(10,2047,0,0);inputs_bound_tuple=issue_tuple;inputs_bound_mask=3;saved_mask=3;saved=issue_tuple;
  row_barrier_ready=0;#1;need(!backend_go_valid&&!issue_ready,"barrier bypass");row_barrier_ready=1;#1;
  need(backend_go_valid&&issue_ready&&!initial_go_valid,"typed empty GO refused");step();issue_valid=0;inputs_bound_valid=0;inputs_bound_mask=0;
  finish_root();need(native_go_count==1&&initial_go_count==0,"empty reGO or INITIAL alias");
  // INITIAL command is admitted only by allocator binding and separate sink.
  issue_tuple=tuple(2047,1773,20,21);inputs_bound_tuple=issue_tuple;inputs_bound_valid=1;issue_valid=1;required_output_rows=1;issue_output_page_mask=1;inputs_bound_mask=0;
  saved=issue_tuple;saved_mask=0;#1;need(initial_go_valid&&!issue_ready&&!backend_go_valid,"INITIAL used native sink");step();need(!busy,"INITIAL accepted before real ready");
  initial_go_ready=1;#1;need(issue_ready&&initial_go_valid&&!backend_go_valid,"INITIAL handshake refused");step();issue_valid=0;inputs_bound_valid=0;finish_root();initial_go_ready=0;
  need(native_go_count==1&&initial_go_count==1,"INITIAL reGO/native alias");
  // Three sibling outputs produce exactly ONE native GO and ONE source aggregate.
  issue_tuple=tuple(5,1378,38,40);inputs_bound_tuple=issue_tuple;inputs_bound_valid=1;issue_valid=1;required_output_rows=3;issue_output_page_mask=3;inputs_bound_mask=5;
  saved=issue_tuple;saved_mask=5;step();issue_valid=0;inputs_bound_valid=0;inputs_bound_mask=0;finish_root();
  need(native_go_count==2&&initial_go_count==1,"grouped root re-executed");
  // Late old aggregate must fault rather than attach to a subsequent frame.
  rf_range_ack_tuple=saved;rf_range_ack_owner=issue_owner;rf_range_ack_page_mask=3;rf_range_ack_valid=1;#1;
  need(!rf_range_ack_ready,"stale aggregate accepted");step();rf_range_ack_valid=0;#1;need(fault&&!publish_valid&&!frame_retire_valid,"stale aggregate did not quarantine");
  $display("PASS_TYPED_EMPTY_INITIAL_SEPARATE_ROOT_GROUP_RECEIVER nativeGO=%0d initialGO=%0d",native_go_count,initial_go_count);$finish;
 end
endmodule
