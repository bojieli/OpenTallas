`timescale 1ns/1ps
`default_nettype none
// Opt-in APPLICATION hard boundary: central bank selection AND original R/C.
// Model before build: banked calendar adds2 edges; the existing R/C below adds
// its existing1/2 edges, so this wrapper adds ZERO further calendar latency.
// COMMANDALIGN=0 deliberately carries no safe-cache command-only alignment;
// the independent +2 cache/mirror stages require separate priced composition.
// Physical OPEN: inherited word-valid/format/RELOC control fanout requires a
// mapped audit. No delayed-shadow control copies or timing exceptions added.
// SVG R/C inventory: rd52 + cmd2x83 + retire2 + retirefields2x17 =254
// nonreset datapath bits; programme_v and sticky injection fault =2 reset bits.
module ot_smh_banked_svg_central #(
 parameter integer PREL=1,CALMUT=0,COMMANDALIGN=0
)(
 input wire clk,rst_n,
 input wire cfg_we,input wire[10:0]cfg_addr,input wire[255:0]cfg_data,
 input wire start_v,input wire[10:0]start_base,input wire[11:0]start_limit,
 input wire[15:0]start_loops,input wire[45:0]start_ctx,
 output wire cfg0_we,cfg1_we,output wire[9:0]bank_cfg_addr,output wire[255:0]bank_cfg_data,
 output wire[107:0]request0,request1,
 input wire[134:0]row0,row1,input wire[8:0]ok0,ok1,input wire[107:0]token0,token1,
 output reg[134:0]programme,output wire programme_v,
 output wire active,done,fault
);
 initial if(COMMANDALIGN!=0)$fatal(1,"command-only alignment is not implemented in this wrapper");
 wire[134:0]word;wire[45:0]wctx;wire[15:0]wit;wire wlast,word_v;wire[31:0]ordinal;
 wire calendar_fault,app_reset_n,app_next_valid;wire[7:0]app_resets;wire[134:0]app_next_word;
 wire[15:0]local_valid;wire[3:0]write_copy;
 for(genvar g=0;g<16;g=g+1)begin:g_app_valid
  (* keep=1 *) ot_smh_banked_rbit u_v(.clk(clk),.rst_n(app_resets[2+g%6]),.d(app_next_valid),.q(local_valid[g]));
 end
 for(genvar g=0;g<4;g=g+1)begin:g_write_copy
  (* keep=1 *) ot_smh_banked_bit u_w(.clk(clk),.d(app_next_word[25]),.q(write_copy[g]));
 end
 ot_smh_calendar_banked_central #(.W(135),.AW(11),.XW(46),.MUT(CALMUT)) u_core(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),
  .cfg0_we(cfg0_we),.cfg1_we(cfg1_we),.bank_cfg_addr(bank_cfg_addr),.bank_cfg_data(bank_cfg_data),
  .request0(request0),.request1(request1),.row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1),
  .calendar(word),.calendar_ctx(wctx),.calendar_iter(wit),.calendar_lastit(wlast),
  .calendar_v(word_v),.ordinal(ordinal),.active(active),.done(done),.fault(calendar_fault),.app_reset_n(app_reset_n),.app_reset_branches(app_resets),.app_next_valid(app_next_valid),.app_next_calendar(app_next_word));
 // RELOC (P2).  Context {row_off12, tag_base10, epoch16, bank1, lstep4, fl1, mode2}; iteration i of a looped body.
 //   R stage (+1 edge): cache READ of word t, relocated: row += i*lstep, tag += tag_base + i*lstep, bank/epoch = context.
 //   C stage (+2 edges): SM COMMAND (+ cache retire) of word t, relocated: row12 / slot += row_off, xaddr += i, first |=
 //   (i == 0), last |= final iteration (looped body), packet tag += tag_base + i*lstep; retire only on the final iteration.
 //   PREL: programme words are LINE-ALIGNED (a line's read and its command in the same word); the C stage lags the R stage
 //   one edge, so the packet the R-stage read returns meets its command exactly as the old one-word read-ahead did.  fl:
 //   the format launch {1, mode[1:0]} is issued on the R edge of the programme's first word (one edge before its first
 //   line; the C slot of that edge must be idle, else fault).  PREL=0: absolute words, read and command of the same word
 //   both on the R edge (the old envelope), C stage unused.
 wire[11:0]c_roff=wctx[45:34];wire[9:0]c_tag=wctx[33:24];wire[15:0]c_ep=wctx[23:8];wire c_bank=wctx[7];
 wire[3:0]c_lstep=wctx[6:3];wire c_fl=wctx[2];wire[1:0]c_fmt=wctx[1:0];
 wire looped=c_lstep!=0;
 wire[9:0]c_lofs=wit[5:0]*c_lstep;
 reg[51:0]rd_r;reg rd_v_r;           // {read_v, bank, epoch16, row6, tag10, retire-free} of the R stage -> bits [116:83]
 reg[82:0]cmd_r,cmd_c;reg ret_r,ret_c;reg[16:0]retf_r,retf_c;reg inj_f;
 reg programme_v_q;
 reg[82:0]cmd_next;reg[33:0]rd_next;reg ret_next;reg[16:0]retf_next;
 always @*begin
  cmd_next=word[82:0];rd_next=word[116:83];ret_next=word[117];retf_next={word[134:119],word[118]};
  if(PREL!=0)begin
   if(write_copy[0])cmd_next[22:11]=word[22:11]+c_roff;
   if(write_copy[1])cmd_next[9:7]=word[9:7]+c_roff[2:0];
   if(write_copy[2]&&looped)cmd_next[6:0]=word[6:0]+wit[6:0];
   if(write_copy[3]&&looped)begin cmd_next[24]=word[24]|(wit==0);cmd_next[23]=word[23]|wlast;end
   if(word[29])cmd_next[39:30]=word[39:30]+c_tag+c_lofs;
   if(word[83])begin rd_next[1]=c_bank;rd_next[17:2]=c_ep;rd_next[23:18]=word[106:101]+c_lofs[5:0];rd_next[33:24]=word[116:107]+c_tag+c_lofs;end
   ret_next=word[117]&&(!looped||wlast);retf_next={c_ep,c_bank};
  end
 end
 for(genvar g=0;g<6;g=g+1)begin:g_cmd_r
  localparam integer BW=(83-16*g<16)?83-16*g:16;
  always @(posedge clk)cmd_r[16*g+:BW]<=local_valid[g]?cmd_next[16*g+:BW]:{BW{1'b0}};
 end
 for(genvar g=0;g<3;g=g+1)begin:g_rd_r
  localparam integer BW=(34-16*g<16)?34-16*g:16;
  always @(posedge clk)rd_r[16*g+:BW]<=local_valid[6+g]?rd_next[16*g+:BW]:{BW{1'b0}};
 end
 always @(posedge clk)begin
  rd_r[51:34]<=0;
  ret_r<=local_valid[9]&&ret_next;
  retf_r[15:0]<=local_valid[10]?retf_next[15:0]:16'b0;
  retf_r[16]<=local_valid[11]&&retf_next[16];
  cmd_c<=cmd_r;ret_c<=ret_r;retf_c<=retf_r;
  if(PREL!=0&&local_valid[12]&&ordinal==0&&c_fl)begin cmd_c[28]<=1'b1;cmd_c[27:26]<=c_fmt;end
 end
 always @(posedge clk or negedge app_reset_n)
  if(!app_reset_n)begin programme_v_q<=0;inj_f<=0;end
  else begin
   programme_v_q<=local_valid[13];
   if(PREL!=0&&local_valid[14]&&ordinal==0&&c_fl&&(cmd_r!=0||ret_r))inj_f<=1;     // format launch slot not idle
  end
 always @* begin
  programme=0;
  programme[116:83]=rd_r[33:0];
  if(PREL!=0)begin programme[82:0]=cmd_c;programme[117]=ret_c;programme[134:118]=retf_c;end
  else begin programme[82:0]=cmd_r;programme[117]=ret_r;programme[134:118]=retf_r;end
 end
 assign programme_v=programme_v_q;
 assign fault=calendar_fault||inj_f;
endmodule
`default_nettype wire
