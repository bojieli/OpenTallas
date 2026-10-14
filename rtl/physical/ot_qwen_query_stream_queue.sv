// Default-off live query capture. Related base/source edges must be proven:
// E+1 copies the E registered allocation tuple before next source NBA overwrite.
// Source reserve is granted BEFORE producing CC edge; actual_step is sampled
// on every live base edge, including disabled CC edges. No clock-ratio/CDC proof.
module ot_qwen_query_stream_queue #(
 parameter integer ENABLE=0,DEPTH=8,
 parameter integer PW=(DEPTH<2?1:$clog2(DEPTH))
)(
 input wire base_clk,rst_n,core_output_step,query_alloc_v,
 input wire [209:0] query_tuple,
 output wire core_credit,
 input wire consume_ready,
 output wire consume_v,output wire [209:0] consume_tuple,
 output reg fault
);
 reg output_step;
 reg [PW:0] count;
 reg [PW-1:0] head,tail;
 reg [209:0] entries[0:DEPTH-1];
 wire pending_post=output_step&&query_alloc_v;
 wire pop=consume_v&&consume_ready;
 assign consume_v=ENABLE&&!fault&&count!=0;
 assign consume_tuple=entries[head];
 assign core_credit=ENABLE&&!fault&&({1'b0,count}+pending_post<DEPTH);
 always @(posedge base_clk)begin
  if(!rst_n)begin output_step<=0;count<=0;head<=0;tail<=0;fault<=0;end
  else if(ENABLE)begin
   output_step<=core_output_step;
   if(core_output_step&&!core_credit)fault<=1;
   if(pending_post)begin
    if(query_tuple[209:206]==0)fault<=1;
    if(count==DEPTH&&!pop)fault<=1;
    else begin
     entries[tail]<=query_tuple;
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
