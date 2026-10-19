`timescale 1ns/1ps
`default_nettype none
// One real1024x256 SRAM. Model b482b7fdd precedes this opt-in source.
// Metadata rings and native request/output Qs give one fixed stage contract, no ready/credits.
module ot_smh_calendar_bank_leaf #(
 parameter integer W=135,XW=46,BANK=0,MUT=0,TW=62+XW,QW=(W+15)/16
)(
 input wire clk,rst_n,input wire cfg_we,input wire[9:0]cfg_addr,input wire[255:0]cfg_data,
 input wire[TW-1:0]read_token,
 output reg[W-1:0]row,output wire[QW-1:0]word_ok,output reg[TW-1:0]row_token
);
 (* keep=1 *) reg[1:0] reset_landing;
 always @(posedge clk or negedge rst_n)if(!rst_n)reset_landing<=0;else reset_landing<={reset_landing[0],1'b1};
 wire[5:0] reset_branch;
 for(genvar g=0;g<6;g=g+1)begin:g_reset
  (* keep=1 *) ot_smh_banked_reset_branch u_reset(.clk(clk),.rst_n(rst_n),.phase0(reset_landing[0]),.q(reset_branch[g]));
 end
 reg cw,rv;reg[9:0]ca,ra;reg[255:0]cd;
 always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;ra<=read_token[9:0];end
 always @(posedge clk or negedge reset_branch[0])
  if(!reset_branch[0])begin cw<=0;rv<=0;end
  else begin cw<=cfg_we;rv<=read_token[TW-1];end
 wire[255:0]macro_data;
 ot_sram_1r1w_1024x256_m2_r2c2 u_program(
  .clk(clk),.r_ce_in(rv),.r_addr_in(ra),.rd_out(macro_data),
  .w_ce_in(cw),.w_addr_in(ca),.wd_in(cd),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 localparam integer PAD=((TW+3)/4)*4;
 wire[PAD-1:0] in_pad={{(PAD-TW){1'b0}},read_token};wire[PAD-1:0]out_pad;
 for(genvar g=0;g<PAD/4;g=g+1)begin:g_meta
  (* keep=1 *) ot_smh_banked_ring4 #(.DELAY((MUT==2)?1:2)) u_meta(
   .clk(clk),.rst_n(reset_branch[g%6]),.din(in_pad[4*g+:4]),.dout(out_pad[4*g+:4]));
 end
 wire[TW-1:0] old_token=out_pad[TW-1:0];
 reg[1:0] online;
 always @(posedge clk or negedge reset_branch[0])
  if(!reset_branch[0])online<=0;else if(online!=3)online<=online+1'b1;
 wire incoming_ok=macro_data[255:240]==16'hc7a1&&macro_data[234:224]==old_token[10:0]&&
   macro_data[239:235]==0&&macro_data[223:W]==0&&old_token[10]==1'(BANK);
 for(genvar g=0;g<QW;g=g+1)begin:g_ok
  (* keep=1 *) ot_smh_banked_bit u_ok(.clk(clk),.d(incoming_ok),.q(word_ok[g]));
 end
 always @(posedge clk)begin row<=macro_data[W-1:0];row_token[TW-2:0]<=old_token[TW-2:0];end
 // Only validity needs reset; data/token identity are guarded by this native output Q.
 always @(posedge clk or negedge reset_branch[0])
  if(!reset_branch[0])row_token[TW-1]<=0;
  else row_token[TW-1]<=online>=2&&old_token[TW-1];
endmodule
`default_nettype wire
