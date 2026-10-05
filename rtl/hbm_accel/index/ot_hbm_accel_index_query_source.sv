`timescale 1ps/1fs
// Native VM read join, one prepaid 32-word response. NO local payload dictionary,
// expected inputs or quantisation. Source addresses are the existing SU opcode
// Q/O/IWo bases; O's unwritten prefix is NEVER read. Real parent holds identity.
// Read response is not acknowledged on an identity/tag mismatch. This component
// does not confer VM ownership/publication; caller supplies actual retained VM.
module ot_hbm_accel_index_query_source #(parameter bit ENABLE=0)(
 input wire clk,por_n,start,output wire start_ready,
 input wire[31:0] source_job,input wire[3:0] source_gen,
 input wire[19:0] source_pos,input wire[6:0] source_rank,
 input wire[31:0] original_q_base,rotated_q_base,scaled_weight_base,
 input wire[7:0] source_tail_words,
 output wire read_v,input wire read_r,output wire[31:0] read_addr,
 output wire[7:0] read_tag,output wire[5:0] read_words,
 output wire[31:0] read_job,output wire[3:0] read_gen,
 output wire[19:0] read_pos,output wire[6:0] read_rank,
 input wire rsp_v,output wire rsp_r,input wire[1023:0] rsp_data,
 input wire[7:0] rsp_tag,input wire[31:0] rsp_job,input wire[3:0] rsp_gen,
 input wire[19:0] rsp_pos,input wire[6:0] rsp_rank,
 output wire block_v,input wire block_r,
 output wire[4:0] block_head,output wire[1:0] block_number,
 output wire[1023:0] block_data,output wire[15:0] head_weight,
 output reg fault,output reg done
);
 generate if(!ENABLE)begin:disabled
  assign start_ready=0;assign read_v=0;assign read_addr=0;assign read_tag=0;assign read_words=0;
  assign read_job=0;assign read_gen=0;assign read_pos=0;assign read_rank=0;
  assign rsp_r=0;assign block_v=0;assign block_head=0;assign block_number=0;assign block_data=0;assign head_weight=0;
  always @*begin fault=0;done=0;end
 end else begin:enabled
  reg active,pending,have_weights,buffer_v;
  reg[7:0] cursor,pending_tag;
  reg[31:0] job,qbase,obase,wbase;reg[3:0] generation;reg[19:0] position;reg[6:0] rank;
  reg[1023:0] buffer_data;reg[15:0] weights[0:31];
  wire[32:0] qend={1'b0,original_q_base}+33'd4095;
  wire[32:0] oend={1'b0,rotated_q_base}+33'd4095;
  wire[32:0] wend={1'b0,scaled_weight_base}+33'd31;
  wire descriptor_bad=source_tail_words!=64||source_rank>=96||qend[32]||oend[32]||wend[32]||
   |original_q_base[4:0]|| |rotated_q_base[4:0]|| |scaled_weight_base[4:0];
  assign start_ready=!active&&!pending&&!buffer_v&&!fault;
  assign read_v=active&&!pending&&!buffer_v&&cursor<128&&!fault;
  assign read_tag=have_weights?cursor:8'd128;
  assign read_words=6'd32;
  assign read_addr=have_weights?((cursor[1]?obase:qbase)+{20'b0,cursor[6:2],7'b0}+{25'b0,cursor[1:0],5'b0}):wbase;
  assign read_job=job;assign read_gen=generation;assign read_pos=position;assign read_rank=rank;
  wire rsp_match=pending&&rsp_tag==pending_tag&&rsp_job==job&&rsp_gen==generation&&rsp_pos==position&&rsp_rank==rank;
  assign rsp_r=active&&rsp_match&&!buffer_v&&!fault;
  assign block_v=active&&buffer_v&&!fault;
  assign block_head=cursor[6:2];assign block_number=cursor[1:0];
  assign block_data=buffer_data;assign head_weight=weights[cursor[6:2]];
  integer h;
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin active<=0;pending<=0;buffer_v<=0;have_weights<=0;cursor<=0;pending_tag<=0;
    job<=0;generation<=0;position<=0;rank<=0;qbase<=0;obase<=0;wbase<=0;fault<=0;done<=0;end
   else begin
    done<=0;
    if(start&&start_ready)begin
     if(descriptor_bad)fault<=1;
     else begin active<=1;cursor<=0;have_weights<=0;job<=source_job;generation<=source_gen;position<=source_pos;rank<=source_rank;
      qbase<=original_q_base;obase<=rotated_q_base;wbase<=scaled_weight_base;end
    end
    if(read_v&&read_r)begin pending<=1;pending_tag<=read_tag;end
    // Never signal acceptance to a wrong provider/position/generation/tag.
    if(rsp_v&&!rsp_match)fault<=1;
    if(rsp_v&&rsp_r)begin
     pending<=0;
     if(pending_tag==128)begin
      have_weights<=1;
      for(h=0;h<32;h=h+1)begin
       // Producer rounded to BF16 already; no host or new rounding at this join.
       if(rsp_data[32*h+:16]!=0||rsp_data[32*h+23+:8]==8'hff)fault<=1;
       weights[h]<=rsp_data[32*h+16+:16];
      end
     end else begin buffer_v<=1;buffer_data<=rsp_data;end
    end
    if(block_v&&block_r)begin buffer_v<=0;cursor<=cursor+1;
     if(cursor==127)begin active<=0;done<=1;end
    end
   end
  end
 end endgenerate
endmodule
