`timescale 1ns/1ps
`default_nettype none
// Actual scheduled draft-head row: W32 mask ROM + fixed K256 arithmetic.
// Shared E lookup receives the SAME request/token/identity. Its pin outputs
// launch at R+6..21; this row captures them at R+7..22. Kernel start is R+6.
// The dynamic LM head logit is captured at R with its actual candidate row.
// Availability/identity checks only fault; they cannot stretch any slot.
module ot_s81_markov_static_row #(
 parameter INSTANCE="mk",parameter integer ID_W=60,GLOBAL_ROW0=0,VALID_ROWS=32,
 parameter integer MUTANT_FOLD=0
)(input wire clk,rst_n,input wire[37:0]clk_leaf,input wire request_slot,
 input wire head_valid,input wire[31:0]head_logit,input wire[16:0]head_row,head_token,
 input wire[ID_W-1:0]head_identity,
 input wire[4:0]local_row,input wire[16:0]token,input wire[ID_W-1:0]identity,
 input wire embed_v,input wire[255:0]embed_data,input wire[3:0]embed_beat,
 input wire[16:0]embed_token,input wire[ID_W-1:0]embed_identity,
 output wire joined_valid,output wire[31:0]joined_bits,
 output wire[16:0]joined_row,joined_token,output wire[ID_W-1:0]joined_identity,
 output wire fault);
 reg[183:0]slots;reg[31:0]held_head;reg[16:0]held_row,held_token;
 reg[ID_W-1:0]held_identity;reg schedule_fault;
 wire wv,wfault;wire[255:0]wd;wire[3:0]wb;wire[16:0]wr,wt;wire[ID_W-1:0]wi;
 wire kfault;wire operand_slot=|slots[21:6];
 reg[3:0]expected_beat;integer b;
 always @*begin expected_beat=0;for(b=0;b<16;b=b+1)if(slots[b+6])expected_beat=4'(b);end
 ot_dsrom_markov_weight32_static #(.INSTANCE(INSTANCE),.ID_W(ID_W),.GLOBAL_ROW0(GLOBAL_ROW0),.VALID_ROWS(VALID_ROWS))u_w(
  .clk(clk),.rst_n(rst_n),.request_slot(request_slot),.row(local_row),.token(token),.identity(identity),
  .word_v(wv),.word_data(wd),.word_beat(wb),.word_row(wr),.word_token(wt),.word_identity(wi),.fault(wfault));
 ot_s81_markov_k256_static #(.MUTANT_FOLD(MUTANT_FOLD))u_math(
  .clk(clk),.rst_n(rst_n),.clk_leaf(clk_leaf),.start(slots[5]),.head_logit(held_head),
  .weight_bf16(wd),.embed_bf16(embed_data),.out_valid(joined_valid),.out_bits(joined_bits),.fault(kfault));
 assign joined_row=held_row;assign joined_token=held_token;assign joined_identity=held_identity;
 assign fault=schedule_fault||wfault||kfault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin slots<=0;held_head<=0;held_row<=0;held_token<=0;held_identity<=0;schedule_fault<=0;end
  else begin
   slots<={slots[182:0],request_slot};
   if(request_slot)begin
    held_head<=head_logit;held_row<=head_row;held_token<=token;held_identity<=identity;
    if((|slots[182:0])||!head_valid||head_row!=17'(GLOBAL_ROW0)+local_row||head_token!=token||head_identity!=identity||local_row>=VALID_ROWS||token>=129280)schedule_fault<=1;
   end
   if(wv!=operand_slot||embed_v!=operand_slot)schedule_fault<=1;
   if(operand_slot&&(wb!=expected_beat||embed_beat!=expected_beat||wr!=held_row||wt!=held_token||embed_token!=held_token||wi!=held_identity||embed_identity!=held_identity))schedule_fault<=1;
   if(joined_valid!=slots[183])schedule_fault<=1;
  end
 end
endmodule
`default_nettype wire
