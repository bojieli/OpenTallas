`timescale 1ns/1ps
`default_nettype none
// Compiler-ordered argmax accumulator. Local candidate and incoming carry
// occupy separate fixed slots; no FIFO/ready or runtime draining. IEEE finite
// FP32 order and minimum global vocabulary ID break ties (including +/-0).
module ot_s81_markov_static_argmax #(parameter integer ID_W=60)(
 input wire clk,rst_n,clear_slot,candidate_slot,carry_slot,result_slot,
 input wire candidate_valid,input wire[31:0]candidate_bits,input wire[16:0]candidate_row,
 input wire[ID_W-1:0]candidate_identity,identity,
 input wire carry_valid,input wire[31:0]carry_bits,input wire[16:0]carry_row,
 input wire[ID_W-1:0]carry_identity,
 output reg result_valid,output reg[31:0]result_bits,output reg[16:0]result_row,
 output reg[ID_W-1:0]result_identity,output reg fault);
 reg have;reg[31:0]best_bits;reg[16:0]best_row;reg[ID_W-1:0]held_identity;
 function automatic[31:0]key(input[31:0]v);reg[31:0]z;begin z=(v[30:0]==0)?0:v;key=z[31]?~z:(z^32'h80000000);end endfunction
 wire take=candidate_slot||carry_slot;
 wire[31:0]bits=candidate_slot?candidate_bits:carry_bits;
 wire[16:0]row=candidate_slot?candidate_row:carry_row;
 wire[ID_W-1:0]iid=candidate_slot?candidate_identity:carry_identity;
 wire valid=candidate_slot?candidate_valid:carry_valid;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin have<=0;best_bits<=0;best_row<=0;held_identity<=0;result_valid<=0;result_bits<=0;result_row<=0;result_identity<=0;fault<=0;end
  else begin
   result_valid<=result_slot;
   if(clear_slot)begin have<=0;held_identity<=identity;end
   if((clear_slot&&(take||result_slot))||(candidate_slot&&carry_slot)||(result_slot&&take))fault<=1;
   if(candidate_valid!=candidate_slot||carry_valid!=carry_slot)fault<=1;
   if(take)begin
    if(!valid||iid!=held_identity||row>=129280||bits[30:23]==8'hff)fault<=1;
    if(!have||key(bits)>key(best_bits)||(key(bits)==key(best_bits)&&row<best_row))begin best_bits<=bits;best_row<=row;end
    have<=1;
   end
   if(result_slot)begin
    if(!have)fault<=1;
    result_bits<=best_bits;result_row<=best_row;result_identity<=held_identity;
   end
  end
 end
endmodule
`default_nettype wire
