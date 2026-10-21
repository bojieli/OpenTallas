`timescale 1ns/1ps
`default_nettype none
// SOURCE-only consumer of the exact minimal HBC1 fields; no indexed book.
// It advances at fixed dates even if an actual header is missing. RX faults,
// never completion/credit feedback, decide whether actual data may be written.
module dsdv_hbc1_affine_book(input wire ck,rst_n,context_valid,input wire[511:0] fields,
 input wire[47:0] receiver_edge,
 output wire[15:0] tid,output wire[9:0] user_id,output wire[20:0] position,token,
 output wire[31:0] epoch_id,output wire[63:0] programme_id,
 output wire[7:0] expected_data_stage,output wire[1:0] expected_data_rank,
 output wire next_header_slot,next_forward_slot,prev_header_slot,prev_forward_slot,status_sample_slot,return_send_slot,
 output wire[47:0] transit_body_edge);
 wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 reg was_valid;reg[8:0] remaining;reg[47:0] next_header,last_header;
 assign tid=fields[15:0];assign user_id=fields[25:16];assign position=fields[46:26];assign token=fields[67:47];
 assign epoch_id=fields[99:68];assign programme_id=fields[163:100];
 assign expected_data_stage=fields[497:490];assign expected_data_rank=fields[499:498];
 wire[47:0] ks_date=fields[345:298],prev_date=fields[393:346];
 wire word_header=context_valid&&was_valid&&remaining!=0&&receiver_edge==next_header;
 assign next_header_slot=word_header||(context_valid&&receiver_edge==ks_date);
 assign next_forward_slot=context_valid&&was_valid&&((remaining!=417&&(receiver_edge==last_header+1||receiver_edge==last_header+5))||receiver_edge==ks_date+1);
 assign prev_header_slot=context_valid&&receiver_edge==prev_date;
 assign prev_forward_slot=context_valid&&receiver_edge==prev_date+1;
 assign status_sample_slot=context_valid&&receiver_edge==fields[441:394];
 assign return_send_slot=context_valid&&receiver_edge==fields[489:442];
 assign transit_body_edge=receiver_edge+4;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin was_valid<=0;remaining<=0;end
  else begin
   was_valid<=context_valid;
   if(!context_valid)remaining<=0;
   else if(!was_valid)remaining<=417;
   else if(word_header)remaining<=remaining-1'b1;
  end
 end
 always @(posedge ck)begin
  if(context_valid&&!was_valid)next_header<=fields[259:212];
  else if(word_header)begin last_header<=next_header;next_header<=next_header+16;end
 end
endmodule
`default_nettype wire
