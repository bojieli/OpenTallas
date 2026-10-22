`timescale 1ns/1ps
// Native core code/scale ROM-port provider. Actual HBM gateway words preload
// one mapped SRAM; the existing core retains its exact INT8 arithmetic.
// Addresses use full token*64+word. Slot and identity faults never stall issue.
module qkd_embedding_static_core_store(
 input wire ck,rst_n,
 input wire fill_begin,input wire [17:0] fill_token,input wire [15:0] fill_epoch,
 input wire preload_slot,preload_v,preload_scale,
 input wire [5:0] preload_word,input wire [17:0] preload_token,
 input wire [15:0] preload_epoch,input wire [511:0] preload_data,
 input wire core_start,input wire [17:0] core_token,input wire [15:0] core_epoch,
 input wire embed_code_re,input wire [23:0] embed_code_addr,output wire [511:0] embed_code_q,
 input wire embed_scale_re,input wire [17:0] embed_scale_addr,output reg [15:0] embed_scale_q,
 output reg fault
);
 reg [63:0] filled;
 reg scale_filled;
 reg [17:0] resident_token;
 reg [15:0] resident_epoch,scale;
 wire complete=(&filled)&&scale_filled;
 wire code_identity=embed_code_addr[23:6]==resident_token;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin filled<=0;scale_filled<=0;resident_token<=0;resident_epoch<=0;fault<=0;end
  else begin
   if(fill_begin)begin
    filled<=0;scale_filled<=0;resident_token<=fill_token;resident_epoch<=fill_epoch;
    if(fill_token>=151936||preload_slot||core_start||embed_code_re||embed_scale_re)fault<=1;
   end
   if(preload_slot!=preload_v)fault<=1;
   if(preload_slot)begin
    if(preload_token!=resident_token||preload_epoch!=resident_epoch||fill_begin)fault<=1;
    if(preload_scale)begin if(scale_filled)fault<=1;scale_filled<=1;end
    else begin if(filled[preload_word])fault<=1;filled[preload_word]<=1;end
   end
   if(core_start&&(!complete||core_token!=resident_token||core_epoch!=resident_epoch||fill_begin||preload_slot))fault<=1;
   if(embed_code_re&&(!complete||!code_identity||preload_slot||fill_begin))fault<=1;
   if(embed_scale_re&&(!complete||embed_scale_addr!=resident_token||preload_slot||fill_begin))fault<=1;
  end
 always @(posedge ck)begin
  if(preload_slot&&preload_v&&preload_scale)scale<=preload_data[15:0];
  if(embed_scale_re)embed_scale_q<=scale;
 end
 ot_sram_1r1w_64x512_m1_r2c2 codes(
  .clk(ck),.r_ce_in(embed_code_re),.r_addr_in(embed_code_addr[5:0]),.rd_out(embed_code_q),
  .w_ce_in(preload_slot&&preload_v&&!preload_scale),.w_addr_in(preload_word),.wd_in(preload_data),
  .w_mask_in({512{1'b1}}),.rr_en(2'b00),.rr_addr(12'd0),.cr_en(2'b00),.cr_sel(18'd0));
endmodule
