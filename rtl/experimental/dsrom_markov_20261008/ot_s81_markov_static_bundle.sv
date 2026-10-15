`timescale 1ns/1ps
`default_nettype none
// One real 128-row head bundle -> four real static Markov A32 consumers.
// Production CUT511/SPLIT9/IOREG/SAFE/BST2: public head output launch is
// G+472+256*k (A0..2), G+474+256*k (A3). Receivers capture one edge later.
// Static slots are generated from go; actual head validity only checks them.
// Shared E ROM preloads four independent real-FF vectors once per token.
module ot_s81_markov_static_bundle #(
 parameter integer GLOBAL_ROW0=0,ID_W=60,parameter INSTANCE="h"
)(input wire clk,rst_n,go,input wire[3:0]clk_A,input wire[151:0]clk_leaf,
 input wire[252:0]clk_E_pair,input wire[15:0]clk_E_group,
 input wire[255:0]xa,xb,input wire[16:0]token,input wire[ID_W-1:0]identity,
 output wire[3:0]joined_valid,output wire[127:0]joined_bits,output wire[67:0]joined_row,
 output wire[67:0]joined_token,output wire[4*ID_W-1:0]joined_identity,
 output wire head_max_v,output wire[16:0]head_max_row,output wire[31:0]head_max_bits,
 output wire[3:0]head_v,output wire[127:0]head_d,output wire[67:0]head_row,
 output wire fault);
 reg active;reg[13:0]age;reg[16:0]held_token;reg[ID_W-1:0]held_id;reg control_fault;
 wire h_fault,e_fault;wire ev;wire[255:0]ed;wire[3:0]eb;wire[16:0]et;wire[ID_W-1:0]ei;
 wire[3:0]c_fault,m_fault,row_slots;
 ot_dsrom_head_bundle #(.BST(2),.CUT(511),.SPLIT9(1),.INSTANCE(INSTANCE),.IOREG(1),.SAFE(1))u_head(
  .clk(clk),.rst_n(rst_n),.go(go),.row0(17'(GLOBAL_ROW0)),.xa(xa),.xb(xb),
  .res_v(head_max_v),.res_row(head_max_row),.res_bits(head_max_bits),.fault(h_fault),
  .head_v(head_v),.head_d(head_d),.head_row(head_row));
 ot_dsrom_markov_embed_static #(.ID_W(ID_W))u_E(.clk(clk),.rst_n(rst_n),.clk_pair(clk_E_pair),.clk_group(clk_E_group),
  .request_slot(go),.token(token),.identity(identity),.word_v(ev),.word_data(ed),.word_beat(eb),.word_token(et),.word_identity(ei),.fault(e_fault));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;age<=0;held_token<=0;held_id<=0;control_fault<=0;end
  else begin
   if(head_v!=row_slots)control_fault<=1;
   if(go)begin
    if(active||GLOBAL_ROW0<0||GLOBAL_ROW0+128>129280||token>=129280)control_fault<=1;
    active<=1;age<=0;held_token<=token;held_id<=identity;
   end else if(active)begin
    if(age==8596)active<=0;else age<=age+1'b1;
   end
  end
 end
 generate for(genvar q=0;q<4;q=q+1)begin:g_A
  localparam integer FIRST=(q==3)?473:471;
  wire slot=active&&age>=FIRST&&age<=FIRST+31*256&&age[7:0]==8'(FIRST%256);
  assign row_slots[q]=slot;
  wire[4:0]local_row=5'((age-FIRST)>>8);
  wire cv;wire[255:0]cd;wire[3:0]cb;wire[16:0]ct;wire[ID_W-1:0]ci;
  ot_s81_markov_embed_cache_static #(.ID_W(ID_W))u_cache(.clk(clk_A[q]),.rst_n(rst_n),
   .load_v(ev),.load_data(ed),.load_beat(eb),.load_token(et),.load_identity(ei),
   .request_slot(slot),.token(held_token),.identity(held_id),.word_v(cv),.word_data(cd),.word_beat(cb),.word_token(ct),.word_identity(ci),.fault(c_fault[q]));
  ot_s81_markov_static_row #(.INSTANCE($sformatf("mk%0d",q)),.ID_W(ID_W),.GLOBAL_ROW0(GLOBAL_ROW0+32*q))u_row(
   .clk(clk_A[q]),.rst_n(rst_n),.clk_leaf(clk_leaf[38*q+:38]),.request_slot(slot),.head_valid(head_v[q]),
   .head_logit(head_d[32*q+:32]),.head_row(head_row[17*q+:17]),.head_token(held_token),.head_identity(held_id),
   .local_row(local_row),.token(held_token),.identity(held_id),.embed_v(cv),.embed_data(cd),.embed_beat(cb),.embed_token(ct),.embed_identity(ci),
   .joined_valid(joined_valid[q]),.joined_bits(joined_bits[32*q+:32]),.joined_row(joined_row[17*q+:17]),
   .joined_token(joined_token[17*q+:17]),.joined_identity(joined_identity[q*ID_W+:ID_W]),.fault(m_fault[q]));
 end endgenerate
 assign fault=control_fault||h_fault||e_fault||(|c_fault)||(|m_fault);
endmodule
`default_nettype wire
