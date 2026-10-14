// Default-off live-base capture candidate. core_output_step MUST describe the
// actual coherent producing edge at this base edge; it is never a held valid.
// One reserved slot covers a produced word awaiting the next base capture.
module ot_qwen_numeric_output_queue #(
 parameter integer ENABLE=0,DEPTH=2,
 parameter integer PW=(DEPTH<2?1:$clog2(DEPTH))
)(
 input wire base_clk,rst_n,core_output_step,
 input wire numeric_v,input wire [511:0] numeric_word,
 input wire query_output_toggle,input wire [87:0] query_output_tuple,
 output reg query_output_ack_toggle,
 output wire core_credit,
 input wire consume_ready,
 output wire consume_v,output wire [511:0] consume_word,
 output wire consume_has_query,output wire [87:0] consume_query_tuple,
 output reg fault
);
 reg output_step;
 reg [PW:0] count;
 reg [PW-1:0] head,tail;
 reg [601:0] entries[0:DEPTH-1];
 wire pending_post=output_step && numeric_v;
 wire query_pending=query_output_toggle!=query_output_ack_toggle;
 wire pop=consume_v&&consume_ready;
 assign consume_v=ENABLE && count!=0 && !fault;
 assign {consume_word,consume_has_query,consume_query_tuple}=entries[head][601:1];
 // Capacity must reserve BOTH existing entries and the not-yet-posted word.
 assign core_credit=ENABLE && !fault && !query_pending &&
  ({1'b0,count}+pending_post<DEPTH);
 always @(posedge base_clk)begin
  if(!rst_n)begin output_step<=0;count<=0;head<=0;tail<=0;query_output_ack_toggle<=0;fault<=0;end
  else if(ENABLE)begin
   output_step<=core_output_step;
   if(core_output_step&&!core_credit)fault<=1;
   if(pending_post)begin
    if(count==DEPTH&&!pop)fault<=1;
    else begin
     entries[tail]<={numeric_word,query_pending,query_output_tuple,query_output_toggle};
     tail<=(tail==DEPTH-1)?{PW{1'b0}}:tail+1'b1;
    end
   end
   if(pop)begin
    if(consume_has_query)query_output_ack_toggle<=entries[head][0];
    head<=(head==DEPTH-1)?{PW{1'b0}}:head+1'b1;
   end
   case({pending_post,pop})
    2'b10:if(count!=DEPTH)count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:count<=count;
   endcase
  end
 end
endmodule
