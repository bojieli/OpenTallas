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
 output wire next_header_slot,next_forward_slot,prev_header_slot,prev_forward_slot,status_sample_slot,return_send_slot,source_return_TX_slot,
 output wire[47:0] transit_body_edge);
 wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 reg was_valid,sent_any;reg[9:0] remaining;wire[47:0] next_header,last_header;
 assign tid=fields[15:0];assign user_id=fields[25:16];assign position=fields[46:26];assign token=fields[67:47];
 assign epoch_id=fields[99:68];assign programme_id=fields[163:100];
 assign expected_data_stage=fields[497:490];assign expected_data_rank=fields[499:498];
 wire[47:0] ks_date=fields[345:298],prev_date=fields[393:346];
 wire nonzero=remaining!=0,edge_eq=receiver_edge==next_header;
 wire word_header=context_valid&&was_valid&&nonzero&&edge_eq;
 assign next_header_slot=word_header||(context_valid&&receiver_edge==ks_date);
 assign next_forward_slot=context_valid&&was_valid&&((sent_any&&(receiver_edge==last_header+1||receiver_edge==last_header+5))||receiver_edge==ks_date+1);
 assign prev_header_slot=context_valid&&receiver_edge==prev_date;
 assign prev_forward_slot=context_valid&&receiver_edge==prev_date+1;
 assign status_sample_slot=context_valid&&receiver_edge==fields[441:394];
 assign return_send_slot=context_valid&&receiver_edge==fields[489:442];
 assign source_return_TX_slot=context_valid&&receiver_edge==fields[489:442]+1;
 assign transit_body_edge=receiver_edge+4;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin was_valid<=0;remaining<=0;sent_any<=0;end
  else begin
   was_valid<=context_valid;
   if(!context_valid)begin remaining<=0;sent_any<=0;end
   else if(!was_valid)begin remaining<=fields[281:272];sent_any<=0;end
   else if(word_header)begin remaining<=remaining-1'b1;sent_any<=1;end
  end
 end
 genvar k;
 generate for(k=0;k<4;k=k+1)begin:g_words
  wire[11:0] step;
  if(k==0)begin:g_low assign step=12'd16;end
  else begin:g_high assign step={11'd0,(&next_header[12*k-1:4])};end
  (* keep_hierarchy="yes" *)dsdv_hbc_book_next12 #(.ID(k)) u_next(.ck(ck),.context_valid(context_valid),.was_valid(was_valid),.nonzero(nonzero),.edge_eq(edge_eq),
   .first(fields[212+12*k+:12]),.step(step),.q(next_header[12*k+:12]));
  wire en;
  (* keep_hierarchy="yes" *)dsdv_hbc_book_enable #(.ID(k+4)) u_last_en(.context_valid(context_valid),.was_valid(was_valid),.nonzero(nonzero),.edge_eq(edge_eq),.first(),.advance(en));
  (* keep_hierarchy="yes" *)dsdv_hostb_hold_bits #(.ID(k),.W(12)) u_last(.ck(ck),.en(en),.d(next_header[12*k+:12]),.q(last_header[12*k+:12]));
 end endgenerate
endmodule
module dsdv_hbc_book_enable #(parameter integer ID=0)(input wire context_valid,was_valid,nonzero,edge_eq,output wire first,advance);
 assign first=context_valid&&!was_valid;
 assign advance=context_valid&&was_valid&&nonzero&&edge_eq;
endmodule
module dsdv_hbc_book_next12 #(parameter integer ID=0)(input wire ck,context_valid,was_valid,nonzero,edge_eq,input wire[11:0]first,step,output reg[11:0]q);
 wire init,advance;
 (* keep_hierarchy="yes" *)dsdv_hbc_book_enable #(.ID(ID)) u_enable(.context_valid(context_valid),.was_valid(was_valid),.nonzero(nonzero),.edge_eq(edge_eq),.first(init),.advance(advance));
 always @(posedge ck)if(init)q<=first;else if(advance)q<=q+step;
endmodule
`default_nettype wire
