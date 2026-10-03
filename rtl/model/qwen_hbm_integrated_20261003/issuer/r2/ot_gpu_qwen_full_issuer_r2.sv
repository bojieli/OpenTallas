`timescale 1ps/1ps
// R2 FRAMEONLY retirement. Published sourcelease stays with actual allocator.
module ot_gpu_qwen_full_issuer_sm_r2 #(parameter bit ENABLE=0,parameter integer INDEX=0)(
 input wire inputs_bound_valid,
 input wire [238:0] inputs_bound_tuple,
 input wire [6:0] inputs_bound_mask,
 input wire [31:0] issue_output_page_mask,
 output wire inputs_bound_ready,
 input wire [238:0] rf_range_ack_tuple,
 input wire [31:0] rf_range_ack_page_mask,
 output wire [31:0] publish_page_mask,
 output wire input_terminal_valid,input_reverse_valid,
 input wire input_terminal_ready,input_reverse_ready,
 output wire [238:0] input_terminal_tuple,input_reverse_tuple,
 output wire [6:0] input_terminal_mask,input_reverse_mask,
 input wire clk,por_n,run_enable,session_valid,
 input wire [63:0] session_id,
 input wire issue_valid,row_barrier_ready,backend_go_ready,
 input wire [238:0] issue_tuple,
 input wire [54:0] issue_owner,
 output wire issue_ready,backend_go_valid,
 output wire [238:0] backend_go_tuple,
 output wire [54:0] backend_go_owner,
 input wire producer_visible_valid,rf_range_ack_valid,whole_terminal_valid,whole_reverse_valid,
 input wire [238:0] producer_visible_tuple,whole_terminal_tuple,whole_reverse_tuple,
 input wire [54:0] rf_range_ack_owner,
 output wire producer_visible_ready,rf_range_ack_ready,whole_terminal_ready,whole_reverse_ready,
 output wire publish_valid,frame_retire_valid,
 input wire publish_ready,frame_retire_ready,
 output wire [238:0] publish_tuple,frame_retire_tuple,
 output wire [54:0] publish_owner,frame_retire_owner,
 output wire busy,fault
);
 // {fault,published,reverse,terminal,ACK,producer,busy,tuple239,owner55}.
 wire [341:0] state;
 reg [341:0] next_state;
 wire record_clean;
 wire [238:0] held_tuple=state[332:94];
 wire [54:0] held_owner=state[93:39];
 assign busy=state[333];
 assign fault=ENABLE && (!record_clean || state[341]);
 wire active=ENABLE && por_n && run_enable && session_valid && record_clean && !fault;
 wire legal_issue=inputs_bound_valid && inputs_bound_tuple==issue_tuple && issue_output_page_mask!=0 &&issue_tuple[238:175]==session_id &&
  issue_tuple[174:164]<1737 && issue_tuple[35]==(INDEX/32) && issue_tuple[34:30]==(INDEX%32) &&
  issue_tuple[9:0]<=512 && {1'b0,issue_tuple[18:10]}<issue_tuple[9:0];
 wire unexpected=(producer_visible_valid && (!busy || state[334] || !result_match)) ||
  (rf_range_ack_valid && (!busy || state[335] || !ack_match)) ||
  (whole_terminal_valid && (!busy || state[336] || !terminal_match)) ||
  (whole_reverse_valid && (!busy || state[337] || !reverse_match));
 assign backend_go_valid=active && !unexpected && !busy && issue_valid && row_barrier_ready && legal_issue;
 assign issue_ready=active && !unexpected && !busy && row_barrier_ready && legal_issue && backend_go_ready;
 assign backend_go_tuple=issue_tuple;
 assign backend_go_owner=issue_owner;
 wire result_match=producer_visible_tuple==held_tuple;
 wire ack_match=rf_range_ack_owner==held_owner && rf_range_ack_tuple==held_tuple && rf_range_ack_page_mask==state[31:0];
 wire terminal_match=whole_terminal_tuple==held_tuple;
 wire reverse_match=whole_reverse_tuple==held_tuple;
 assign producer_visible_ready=active && !unexpected && busy && !state[334] && result_match;
 assign rf_range_ack_ready=active && !unexpected && busy && !state[335] && ack_match;
 assign whole_terminal_ready=active && !unexpected && busy && !state[336] && terminal_match;
 assign whole_reverse_ready=active && !unexpected && busy && !state[337] && reverse_match;
 assign publish_valid=active && !unexpected && busy && state[334] && state[335] && !state[338];
 assign frame_retire_valid=active && !unexpected && busy && state[336] && state[337] && state[338] && state[339] && state[340];
 assign inputs_bound_ready=issue_valid && issue_ready;
 assign input_terminal_valid=active && !unexpected && busy && state[336] && !state[339];
 assign input_reverse_valid=active && !unexpected && busy && state[337] && !state[340];
 assign input_terminal_tuple=held_tuple;assign input_reverse_tuple=held_tuple;
 assign input_terminal_mask=state[38:32];assign input_reverse_mask=state[38:32];
 assign publish_page_mask=state[31:0];
 assign publish_tuple=held_tuple;assign frame_retire_tuple=held_tuple;
 assign publish_owner=held_owner;assign frame_retire_owner=held_owner;
 always @* begin
  next_state=state;
  if(active)begin
   if(unexpected)next_state[341]=1;
   else begin
    if(issue_valid && issue_ready)next_state={9'b000000001,issue_tuple,issue_owner,inputs_bound_mask,issue_output_page_mask};
    if(producer_visible_valid && producer_visible_ready)next_state[334]=1;
    if(rf_range_ack_valid && rf_range_ack_ready)next_state[335]=1;
    if(whole_terminal_valid && whole_terminal_ready)next_state[336]=1;
    if(whole_reverse_valid && whole_reverse_ready)next_state[337]=1;
    if(input_terminal_valid && input_terminal_ready)next_state[339]=1;
    if(input_reverse_valid && input_reverse_ready)next_state[340]=1;
    if(publish_valid && publish_ready)next_state[338]=1;
    if(frame_retire_valid && frame_retire_ready)next_state=0;
   end
  end
 end
 ot_gpu_qwen_issuer_record #(.BITS(342),.INDEX(INDEX)) owned(
  .clk(clk),.por_n(por_n),.write_enable(active && next_state!=state),.next_data(next_state),.data(state),.clean(record_clean));
endmodule

module ot_gpu_qwen_full_issuer_r2 #(parameter bit ENABLE=0)(
 input wire [63:0] inputs_bound_valid,
 input wire [64*239-1:0] inputs_bound_tuple,
 input wire [64*7-1:0] inputs_bound_mask,
 input wire [64*32-1:0] issue_output_page_mask,
 output wire [63:0] inputs_bound_ready,
 input wire [64*239-1:0] rf_range_ack_tuple,
 input wire [64*32-1:0] rf_range_ack_page_mask,
 output wire [64*32-1:0] publish_page_mask,
 output wire [63:0] input_terminal_valid,input_reverse_valid,
 input wire [63:0] input_terminal_ready,input_reverse_ready,
 output wire [64*239-1:0] input_terminal_tuple,input_reverse_tuple,
 output wire [64*7-1:0] input_terminal_mask,input_reverse_mask,
 input wire clk,por_n,run_enable,
 input wire session_begin_valid,
 input wire [63:0] session_begin_id,
 input wire [7:0] source_quiescent,
 output wire session_begin_ready,session_valid,session_fault,
 output wire [63:0] session_id,
 input wire [63:0] issue_valid,row_barrier_ready,backend_go_ready,
 input wire [64*239-1:0] issue_tuple,
 input wire [64*55-1:0] issue_owner,
 output wire [63:0] issue_ready,backend_go_valid,
 output wire [64*239-1:0] backend_go_tuple,
 output wire [64*55-1:0] backend_go_owner,
 input wire [63:0] producer_visible_valid,rf_range_ack_valid,whole_terminal_valid,whole_reverse_valid,
 input wire [64*239-1:0] producer_visible_tuple,whole_terminal_tuple,whole_reverse_tuple,
 input wire [64*55-1:0] rf_range_ack_owner,
 output wire [63:0] producer_visible_ready,rf_range_ack_ready,whole_terminal_ready,whole_reverse_ready,
 output wire [63:0] publish_valid,frame_retire_valid,
 input wire [63:0] publish_ready,frame_retire_ready,
 output wire [64*239-1:0] publish_tuple,frame_retire_tuple,
 output wire [64*55-1:0] publish_owner,frame_retire_owner,
 output wire [63:0] busy,fault
);
 wire [64:0] session;
 wire session_clean;
 assign session_valid=ENABLE && por_n && session_clean && session[64];
 assign session_id=session[63:0];
 assign session_fault=ENABLE && !session_clean;
 // These eight bits must come from actual owned cohort debt/held-copy checks.
 // This is NOT a host reservation, invented grant or installed all-copy proof.
 assign session_begin_ready=ENABLE && por_n && run_enable && session_clean &&
   !(|busy) && !(|fault) && (&source_quiescent);
 ot_gpu_qwen_issuer_record #(.BITS(65),.INDEX(64)) cold_session(
  .clk(clk),.por_n(por_n),.write_enable(session_begin_valid && session_begin_ready),
  .next_data({1'b1,session_begin_id}),.data(session),.clean(session_clean));
 for(genvar sm=0;sm<64;sm=sm+1)begin:g_sm
  ot_gpu_qwen_full_issuer_sm_r2 #(.ENABLE(ENABLE),.INDEX(sm)) leaf(
   .inputs_bound_valid(inputs_bound_valid[sm]),
   .inputs_bound_tuple(inputs_bound_tuple[sm*239+:239]),
   .inputs_bound_mask(inputs_bound_mask[sm*7+:7]),
   .issue_output_page_mask(issue_output_page_mask[sm*32+:32]),
   .inputs_bound_ready(inputs_bound_ready[sm]),
   .rf_range_ack_tuple(rf_range_ack_tuple[sm*239+:239]),
   .rf_range_ack_page_mask(rf_range_ack_page_mask[sm*32+:32]),
   .publish_page_mask(publish_page_mask[sm*32+:32]),
   .input_terminal_valid(input_terminal_valid[sm]),
   .input_reverse_valid(input_reverse_valid[sm]),
   .input_terminal_ready(input_terminal_ready[sm]),
   .input_reverse_ready(input_reverse_ready[sm]),
   .input_terminal_tuple(input_terminal_tuple[sm*239+:239]),
   .input_reverse_tuple(input_reverse_tuple[sm*239+:239]),
   .input_terminal_mask(input_terminal_mask[sm*7+:7]),
   .input_reverse_mask(input_reverse_mask[sm*7+:7]),
   .clk(clk),.por_n(por_n),.run_enable(run_enable && !session_fault),.session_valid(session_valid),.session_id(session_id),
   .issue_valid(issue_valid[sm]),.row_barrier_ready(row_barrier_ready[sm]),.backend_go_ready(backend_go_ready[sm]),
   .issue_tuple(issue_tuple[sm*239+:239]),.issue_owner(issue_owner[sm*55+:55]),
   .issue_ready(issue_ready[sm]),.backend_go_valid(backend_go_valid[sm]),
   .backend_go_tuple(backend_go_tuple[sm*239+:239]),.backend_go_owner(backend_go_owner[sm*55+:55]),
   .producer_visible_valid(producer_visible_valid[sm]),.rf_range_ack_valid(rf_range_ack_valid[sm]),
   .whole_terminal_valid(whole_terminal_valid[sm]),.whole_reverse_valid(whole_reverse_valid[sm]),
   .producer_visible_tuple(producer_visible_tuple[sm*239+:239]),.rf_range_ack_owner(rf_range_ack_owner[sm*55+:55]),
   .whole_terminal_tuple(whole_terminal_tuple[sm*239+:239]),.whole_reverse_tuple(whole_reverse_tuple[sm*239+:239]),
   .producer_visible_ready(producer_visible_ready[sm]),.rf_range_ack_ready(rf_range_ack_ready[sm]),
   .whole_terminal_ready(whole_terminal_ready[sm]),.whole_reverse_ready(whole_reverse_ready[sm]),
   .publish_valid(publish_valid[sm]),.publish_ready(publish_ready[sm]),.publish_tuple(publish_tuple[sm*239+:239]),
   .publish_owner(publish_owner[sm*55+:55]),.frame_retire_valid(frame_retire_valid[sm]),.frame_retire_ready(frame_retire_ready[sm]),
   .frame_retire_tuple(frame_retire_tuple[sm*239+:239]),.frame_retire_owner(frame_retire_owner[sm*55+:55]),.busy(busy[sm]),.fault(fault[sm]));
 end
endmodule
