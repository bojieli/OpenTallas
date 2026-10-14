// Default-off streaming join. Source and base clock MUST have the explicitly
// proved same-family edge ordering: base E+1 samples the registered E word/tag
// before the next coherent source NBA overwrite. output_step is an actual
// producing-clock event, sampled even on disabled source edges. This module
// does not establish that physical phase/clock contract.
module ot_qwen_numeric_stream_queue #(
 parameter integer ENABLE=0, DEPTH=8,
 parameter integer PW=(DEPTH<2?1:$clog2(DEPTH))
)(
 input wire base_clk,rst_n,core_output_step,
 input wire numeric_v,input wire [511:0] numeric_word,
 input wire numeric_has_query,input wire [47:0] numeric_identity,
 input wire [39:0] numeric_query_seq,
 output wire core_credit,
 input wire consume_ready,
 output wire consume_v,output wire [511:0] consume_word,
 output wire consume_has_query,output wire [87:0] consume_query_tuple,
 output reg fault
);
 reg output_step;
 reg [PW:0] count;
 reg [PW-1:0] head,tail;
 reg [600:0] entries[0:DEPTH-1];
 wire pending_post=output_step&&numeric_v;
 wire pop=consume_v&&consume_ready;
 assign consume_v=ENABLE&&!fault&&count!=0;
 assign {consume_word,consume_has_query,consume_query_tuple}=entries[head];
 // Do not borrow a same-edge pop for source credit. Reserve the word already
 // produced but not copied as well as every durable queued word.
 assign core_credit=ENABLE&&!fault&&({1'b0,count}+pending_post<DEPTH);
 always @(posedge base_clk)begin
  if(!rst_n)begin output_step<=0;count<=0;head<=0;tail<=0;fault<=0;end
  else if(ENABLE)begin
   output_step<=core_output_step;
   if(core_output_step&&!core_credit)fault<=1;
   if(pending_post)begin
    if(count==DEPTH&&!pop)fault<=1;
    else begin
     entries[tail]<={numeric_word,numeric_has_query,numeric_identity,numeric_query_seq};
     tail<=(tail==DEPTH-1)?{PW{1'b0}}:tail+1'b1;
    end
   end
   if(pop)head<=(head==DEPTH-1)?{PW{1'b0}}:head+1'b1;
   case({pending_post,pop})
    2'b10:if(count!=DEPTH)count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:count<=count;
   endcase
  end
 end
endmodule
