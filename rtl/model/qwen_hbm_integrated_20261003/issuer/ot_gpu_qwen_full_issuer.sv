`timescale 1ps/1ps
// Source acceptance/control only. Whole-engine events are explicit real ports;
// the PC40 fragment is NOT connected as a whole terminal/result producer.
module ot_gpu_qwen_issuer_record #(
 parameter integer BITS=301, WORDS=(BITS+43)/44, INDEX=0
)(input wire clk,por_n,write_enable,input wire [BITS-1:0] next_data,
 output wire [BITS-1:0] data,output wire clean);
 reg [WORDS*72-1:0] coded;
 wire [WORDS*44-1:0] padded={{(WORDS*44-BITS){1'b0}},next_data};
 wire [WORDS*44-1:0] decoded;
 wire [WORDS*72-1:0] encoded;
 wire [WORDS-1:0] word_clean;
 function automatic [71:0] reset_word(input integer word_index);
  reg [63:0] value;reg [71:0] result;integer p,j,k;
  begin
   value={3'd7,10'(word_index),7'(INDEX),44'b0};result=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin result[p-1]=value[j];j=j+1;end
   for(k=0;k<7;k=k+1)begin
    for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)result[(1<<k)-1]=result[(1<<k)-1]^result[p-1];
   end
   result[71]=^result[70:0];reset_word=result;
  end
 endfunction
 for(genvar w=0;w<WORDS;w=w+1)begin:g_words
  wire [6:0] syndrome;
  wire odd,cc,ce,ue,seal_ok,pad_ok;
  wire [71:0] repaired;
  ot_w2_sealed_secded72 #(.PC_ID(7'(INDEX)),.WORD_INDEX(10'(w)),.WORD_KIND(3'd7),
   .PAYLOAD_BITS(w==WORDS-1 ? BITS-w*44 : 44)) codec(
    .payload(padded[w*44+:44]),.current_word(coded[w*72+:72]),.encoded_word(encoded[w*72+:72]),
    .syndrome(syndrome),.overall_odd(odd),.clean(cc),.correctable(ce),.uncorrectable(ue),
    .seal_ok(seal_ok),.padding_ok(pad_ok),.release_clean(word_clean[w]),
    .repaired_payload(decoded[w*44+:44]),.repaired_word(repaired));
  localparam [71:0] RESET_CODE=reset_word(w);
  always @(posedge clk or negedge por_n)
   if(!por_n)coded[w*72+:72]<=RESET_CODE;
   else if(write_enable && clean)coded[w*72+:72]<=encoded[w*72+:72];
 end
 assign data=decoded[BITS-1:0];
 assign clean=&word_clean;
endmodule

module ot_gpu_qwen_full_issuer_sm #(parameter bit ENABLE=0,parameter integer INDEX=0)(
 input wire clk,por_n,run_enable,session_valid,
 input wire [63:0] session_id,
 input wire issue_valid,row_barrier_ready,backend_go_ready,
 input wire [238:0] issue_tuple,
 input wire [54:0] issue_owner,
 output wire issue_ready,backend_go_valid,
 output wire [238:0] backend_go_tuple,
 output wire [54:0] backend_go_owner,
 input wire producer_result_valid,rf_ack_valid,whole_terminal_valid,whole_reverse_valid,
 input wire [238:0] producer_result_tuple,whole_terminal_tuple,whole_reverse_tuple,
 input wire [54:0] rf_ack_owner,
 output wire producer_result_ready,rf_ack_ready,whole_terminal_ready,whole_reverse_ready,
 output wire publish_valid,retire_valid,
 input wire publish_ready,retire_ready,
 output wire [238:0] publish_tuple,retire_tuple,
 output wire [54:0] publish_owner,retire_owner,
 output wire busy,fault
);
 // {fault,published,reverse,terminal,ACK,producer,busy,tuple239,owner55}.
 wire [300:0] state;
 reg [300:0] next_state;
 wire record_clean;
 wire [238:0] held_tuple=state[293:55];
 wire [54:0] held_owner=state[54:0];
 assign busy=state[294];
 assign fault=ENABLE && (!record_clean || state[300]);
 wire active=ENABLE && por_n && run_enable && session_valid && record_clean && !fault;
 wire legal_issue=issue_tuple[238:175]==session_id &&
  issue_tuple[174:164]<1737 && issue_tuple[35]==(INDEX/32) && issue_tuple[34:30]==(INDEX%32) &&
  issue_tuple[9:0]<=512 && {1'b0,issue_tuple[18:10]}<issue_tuple[9:0];
 wire unexpected=(producer_result_valid && (!busy || state[295] || !result_match)) ||
  (rf_ack_valid && (!busy || state[296] || !ack_match)) ||
  (whole_terminal_valid && (!busy || state[297] || !terminal_match)) ||
  (whole_reverse_valid && (!busy || state[298] || !reverse_match));
 assign backend_go_valid=active && !unexpected && !busy && issue_valid && row_barrier_ready && legal_issue;
 assign issue_ready=active && !unexpected && !busy && row_barrier_ready && legal_issue && backend_go_ready;
 assign backend_go_tuple=issue_tuple;
 assign backend_go_owner=issue_owner;
 wire result_match=producer_result_tuple==held_tuple;
 wire ack_match=rf_ack_owner==held_owner;
 wire terminal_match=whole_terminal_tuple==held_tuple;
 wire reverse_match=whole_reverse_tuple==held_tuple;
 assign producer_result_ready=active && !unexpected && busy && !state[295] && result_match;
 assign rf_ack_ready=active && !unexpected && busy && !state[296] && ack_match;
 assign whole_terminal_ready=active && !unexpected && busy && !state[297] && terminal_match;
 assign whole_reverse_ready=active && !unexpected && busy && !state[298] && reverse_match;
 assign publish_valid=active && !unexpected && busy && state[295] && state[296] && !state[299];
 assign retire_valid=active && !unexpected && busy && state[297] && state[298] && state[299];
 assign publish_tuple=held_tuple;assign retire_tuple=held_tuple;
 assign publish_owner=held_owner;assign retire_owner=held_owner;
 always @* begin
  next_state=state;
  if(active)begin
   if(unexpected)next_state[300]=1;
   else begin
    if(issue_valid && issue_ready)next_state={7'b0000001,issue_tuple,issue_owner};
    if(producer_result_valid && producer_result_ready)next_state[295]=1;
    if(rf_ack_valid && rf_ack_ready)next_state[296]=1;
    if(whole_terminal_valid && whole_terminal_ready)next_state[297]=1;
    if(whole_reverse_valid && whole_reverse_ready)next_state[298]=1;
    if(publish_valid && publish_ready)next_state[299]=1;
    if(retire_valid && retire_ready)next_state=0;
   end
  end
 end
 ot_gpu_qwen_issuer_record #(.BITS(301),.INDEX(INDEX)) owned(
  .clk(clk),.por_n(por_n),.write_enable(active && next_state!=state),.next_data(next_state),.data(state),.clean(record_clean));
endmodule

module ot_gpu_qwen_full_issuer #(parameter bit ENABLE=0)(
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
 input wire [63:0] producer_result_valid,rf_ack_valid,whole_terminal_valid,whole_reverse_valid,
 input wire [64*239-1:0] producer_result_tuple,whole_terminal_tuple,whole_reverse_tuple,
 input wire [64*55-1:0] rf_ack_owner,
 output wire [63:0] producer_result_ready,rf_ack_ready,whole_terminal_ready,whole_reverse_ready,
 output wire [63:0] publish_valid,retire_valid,
 input wire [63:0] publish_ready,retire_ready,
 output wire [64*239-1:0] publish_tuple,retire_tuple,
 output wire [64*55-1:0] publish_owner,retire_owner,
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
  ot_gpu_qwen_full_issuer_sm #(.ENABLE(ENABLE),.INDEX(sm)) leaf(
   .clk(clk),.por_n(por_n),.run_enable(run_enable && !session_fault),.session_valid(session_valid),.session_id(session_id),
   .issue_valid(issue_valid[sm]),.row_barrier_ready(row_barrier_ready[sm]),.backend_go_ready(backend_go_ready[sm]),
   .issue_tuple(issue_tuple[sm*239+:239]),.issue_owner(issue_owner[sm*55+:55]),
   .issue_ready(issue_ready[sm]),.backend_go_valid(backend_go_valid[sm]),
   .backend_go_tuple(backend_go_tuple[sm*239+:239]),.backend_go_owner(backend_go_owner[sm*55+:55]),
   .producer_result_valid(producer_result_valid[sm]),.rf_ack_valid(rf_ack_valid[sm]),
   .whole_terminal_valid(whole_terminal_valid[sm]),.whole_reverse_valid(whole_reverse_valid[sm]),
   .producer_result_tuple(producer_result_tuple[sm*239+:239]),.rf_ack_owner(rf_ack_owner[sm*55+:55]),
   .whole_terminal_tuple(whole_terminal_tuple[sm*239+:239]),.whole_reverse_tuple(whole_reverse_tuple[sm*239+:239]),
   .producer_result_ready(producer_result_ready[sm]),.rf_ack_ready(rf_ack_ready[sm]),
   .whole_terminal_ready(whole_terminal_ready[sm]),.whole_reverse_ready(whole_reverse_ready[sm]),
   .publish_valid(publish_valid[sm]),.publish_ready(publish_ready[sm]),.publish_tuple(publish_tuple[sm*239+:239]),
   .publish_owner(publish_owner[sm*55+:55]),.retire_valid(retire_valid[sm]),.retire_ready(retire_ready[sm]),
   .retire_tuple(retire_tuple[sm*239+:239]),.retire_owner(retire_owner[sm*55+:55]),.busy(busy[sm]),.fault(fault[sm]));
 end
endmodule
