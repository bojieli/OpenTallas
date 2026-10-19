// HBM-SMB-KITS opt-in SRAM-response-FIFO composition. Original master byte-identical.
// Storage-only causal equivalence candidate; native registered boundaries/region clock integration still open.
`timescale 1ns/1ps
`default_nettype none
// HBM-SMBUDGET 2026-10-19 (coordinator decision 0jx, P2 + 2,048-word store): ot_hbm_svc_sm_feed_programmed_id with
//   * the programme leaf = ot_smh_calendar_static_x (PAW-bit store: 2,048 words on two 1024x256 macros) launched with the
//     issuer's go CONTEXT {row_off12, tag_base10, epoch16, bank1} (ot_hbm_svc_sm_issuer_rel), carried with every word;
//   * PREL=1: SHAPE-GENERIC programme words, relocated per launch in one registered stage (RELOC, +1 edge on the whole
//     envelope, so read -> packet -> command alignment is unchanged; the extension calendar xc adds the same stage):
//       command row12 [22:11] += row_off and slot3 [9:7] += row_off[2:0]   (only on a valid issue word, cmd[25])
//       command packet tag [39:30] += tag_base                              (only with cmd[29])
//       cache read  : bank = ctx bank, epoch = ctx epoch, tag [116:107] += tag_base     (only with read_v [83])
//       cache retire: bank = ctx bank, epoch = ctx epoch                               (only with retire_v [117])
//     A word without those flags passes unchanged (format launch, idle).  PREL=0 = absolute words (old envelope) through
//     the same +1 stage.
// Everything else (four-PC producer, landing/cache SRAMs, packed136 rows, S1 consumer copy, faults) is the _id feed.
module ot_hbm_svc_sm_feed_programmed_rel_sram_id #(
 parameter integer NATIVE_CACHE_SAFE=0,ATTENTION=0,NATIVE_RETURN=0,RETURN_MUT=0,NATIVE_LANDING=0,FIFOMUT=0,PAW=11,PREL=1,
 parameter integer OWNER_AW=5,RESPONSE_DEPTH=8,DECOUPLE=1,OVERLAP=1,LBANKS=4,
 parameter integer LB=(LBANKS>2)?2:1
)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [3:0]return_pair_clk,return_local_clk,return_pair_hbm_clk,
 input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire reserve_v,output wire reserve_ready,input wire[31:0]reserve_base,
 input wire[14:0]reserve_row_base,input wire[11:0]reserve_total,
 input wire[LB-1:0]reserve_bank,input wire[15:0]reserve_epoch,input wire[6:0]reserve_rows,input wire[9:0]reserve_tag_base,
 // landing index LB bits (LBANKS blocks); the canonical-row cache bank of a block is its landing index LSB
 output wire[LBANKS-1:0]block_ready,output wire[1:0]cache_ready,cache_owned,
 input wire start_v,input wire[LB-1:0]start_bank,input wire[15:0]start_epoch,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire program_start_v,input wire[PAW-1:0]program_start_base,input wire[PAW:0]program_start_limit,input wire[15:0]program_start_loops,
 input wire[45:0]program_start_ctx,
 output wire program_active,program_done,output wire fault,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[1098:0]packet_observe,output wire[134:0]programme_observe,output wire programme_v,
 // H-DIE 2026-10-15: the SM command this programme issues (fixed idle slot = 0), the die net to the SM's command port
 // (the same value the internal consumer copy sees); packet_observe is the die net to the SM's packet port.
 output wire[82:0]sm_command,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 wire cdc_ready,cdc_fault,cache_fault,programme_fault,feed_fault;
 reg descriptor_fault;wire[12:0]expected_sectors=(((reserve_rows*136)+127)>>7)<<2;
 wire legal=reserve_rows!=0&&reserve_rows<=64&&reserve_total==expected_sectors;
 // H-DIE 2026-10-15: the landing bank is free once its block has been copied (cdc allocated[] clears at drain end);
 // the canonical-row cache bank of the same index is checked at OPEN (start), not at reserve, so epoch e+2's prefetch
 // overlaps epoch e's programme.  DECOUPLE=0 = the Codex 14:47 coupling (ablation).
 assign reserve_ready=cdc_ready&&(DECOUPLE!=0||!cache_owned[reserve_bank[0]])&&legal;
 wire reserve_fire=reserve_v&&reserve_ready;
 reg[6:0]rows_q[0:LBANKS-1];reg[9:0]tag_q[0:LBANKS-1];reg open_q;reg[LB-1:0]open_land_q;reg[15:0]open_epoch_q;integer qb;
 wire open_bank_q=open_land_q[0];
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin descriptor_fault<=0;open_q<=0;open_land_q<=0;open_epoch_q<=0;for(qb=0;qb<LBANKS;qb=qb+1)begin rows_q[qb]<=0;tag_q[qb]<=0;end end
  else begin
   if(reserve_v&&!reserve_ready)descriptor_fault<=1;
   if(reserve_fire)begin rows_q[reserve_bank]<=reserve_rows;tag_q[reserve_bank]<=reserve_tag_base;end
   open_q<=start_v;open_land_q<=start_bank;open_epoch_q<=start_epoch;
  end
 end
 wire out_v,out_bank,out_last;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 ot_hbm_svc_sm4pc_cdc_rel_sram_id #(.NATIVE_RETURN(NATIVE_RETURN),.RETURN_MUT(RETURN_MUT),.NATIVE_LANDING(NATIVE_LANDING),.FIFOMUT(FIFOMUT),.OWNER_AW(OWNER_AW),.RESPONSE_DEPTH(RESPONSE_DEPTH),.OVERLAP(OVERLAP),.LBANKS(LBANKS)) producer(
  .id_stack(id_stack),.id_sm(id_sm),
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.return_pair_clk(return_pair_clk),.return_local_clk(return_local_clk),.return_pair_hbm_clk(return_pair_hbm_clk),.stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),
  .reserve_v(reserve_fire),.reserve_ready(cdc_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),
  .block_ready(block_ready),.block_ready_v(),.block_ready_bank(),.block_ready_epoch(),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(cdc_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 // Cache consumes a fixed sector train immediately after OPEN. Native landing
 // delays that train two edges, so its complete OPEN envelope follows identically.
 localparam integer OW=35;
 reg [OW-1:0] open_d1,open_d2;
 wire [OW-1:0] open_raw={open_q,open_bank_q,open_epoch_q,rows_q[open_land_q],tag_q[open_land_q]};
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin open_d1<=0;open_d2<=0;end
  else begin open_d1<=open_raw;open_d2<=open_d1;end
 wire cache_open_v,cache_open_bank;wire[15:0]cache_open_epoch;
 wire[6:0]cache_open_count;wire[9:0]cache_open_tag;
 wire[OW-1:0] open_native=NATIVE_LANDING!=0?open_d2:open_raw;
 wire[OW-1:0] open_return;
 ot_hbm_svg_meta_delay7 #(.W(OW)) u_open_labels(.clk(stream_clk),.rst_n(stream_rst_n),
  .data_in(open_native),.data_out(open_return));
 assign {cache_open_v,cache_open_bank,cache_open_epoch,cache_open_count,cache_open_tag}=
  NATIVE_RETURN!=0?open_return:open_native;
 wire[95:0]indices;wire[63:0]epochs;
 for(genvar l=0;l<4;l=l+1)begin:metadata
  assign indices[l*24+:24]=out_ordinal+l;assign epochs[l*16+:16]=out_epoch;
 end
 wire calendar_active,calendar_done;
 reg[1:0] active_tail,done_tail;
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin active_tail<=0;done_tail<=0;end
  else begin active_tail<={active_tail[0],calendar_active};done_tail<={done_tail[0],calendar_done};end
 assign program_active=NATIVE_CACHE_SAFE!=0?active_tail[1]:calendar_active;
 assign program_done=NATIVE_CACHE_SAFE!=0?done_tail[1]:calendar_done;
 wire[134:0]word;wire[45:0]wctx;wire[15:0]wit;wire wlast,word_v;wire[31:0]ordinal;wire cache_busy;
 ot_smh_calendar_static_x #(.W(135),.AW(PAW),.XW(46)) programme_leaf(
  .clk(stream_clk),.rst_n(stream_rst_n),.cfg_we(program_cfg_we),.cfg_addr(program_cfg_addr),.cfg_data(program_cfg_data),
  .start_v(program_start_v),.start_base(program_start_base),.start_limit(program_start_limit),.start_loops(program_start_loops),
  .start_ctx(program_start_ctx),.calendar(word),.calendar_ctx(wctx),.calendar_iter(wit),.calendar_lastit(wlast),
  .calendar_v(word_v),.ordinal(ordinal),.active(calendar_active),.done(calendar_done),.fault(programme_fault));
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
 reg[134:0]programme;reg programme_v_q;
 always @(posedge stream_clk)begin
  // R stage
  rd_r<=0;cmd_r<=0;ret_r<=0;retf_r<=0;
  if(word_v)begin
   cmd_r<=word[82:0];ret_r<=word[117];retf_r<={word[134:119],word[118]};
   rd_r[33:0]<=word[116:83];
   if(PREL!=0)begin
    if(word[25])begin
     cmd_r[22:11]<=word[22:11]+c_roff;cmd_r[9:7]<=word[9:7]+c_roff[2:0];
     if(looped)begin cmd_r[6:0]<=word[6:0]+wit[6:0];cmd_r[24]<=word[24]|(wit==0);cmd_r[23]<=word[23]|wlast;end
    end
    if(word[29])cmd_r[39:30]<=word[39:30]+c_tag+c_lofs;
    if(word[83])begin rd_r[1]<=c_bank;rd_r[17:2]<=c_ep;rd_r[23:18]<=word[106:101]+c_lofs[5:0];rd_r[33:24]<=word[116:107]+c_tag+c_lofs;end
    ret_r<=word[117]&&(!looped||wlast);retf_r<={c_ep,c_bank};
   end
  end
  // C stage (PREL): the command of the previous R word, plus the format launch of a programme's first word
  cmd_c<=cmd_r;ret_c<=ret_r;retf_c<=retf_r;
  if(PREL!=0&&word_v&&ordinal==0&&c_fl)begin cmd_c[28]<=1'b1;cmd_c[27:26]<=c_fmt;end
 end
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin programme_v_q<=0;inj_f<=0;end
  else begin
   programme_v_q<=word_v;
   if(PREL!=0&&word_v&&ordinal==0&&c_fl&&(cmd_r!=0||ret_r))inj_f<=1;     // format launch slot not idle
  end
 always @* begin
  programme=0;
  programme[116:83]=rd_r[33:0];
  if(PREL!=0)begin programme[82:0]=cmd_c;programme[117]=ret_c;programme[134:118]=retf_c;end
  else begin programme[82:0]=cmd_r;programme[117]=ret_r;programme[134:118]=retf_r;end
 end
 assign programme_v=programme_v_q;
 assign programme_observe=programme;
 // The safe row cache captures all READ/retire inputs two edges later.
 // Preserve their issue edges, and align the entire external command/format.
 reg[82:0] command_d1,command_d2;
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin command_d1<=0;command_d2<=0;end
  else begin command_d1<=programme[82:0];command_d2<=command_d1;end
 assign sm_command=NATIVE_CACHE_SAFE!=0?command_d2:programme[82:0];
 generate if(NATIVE_CACHE_SAFE!=0)begin:g_safe_cache
 ot_hbm_svc_static_sm_packed136_native_safe #(.PACKED136(1)) rows(
  .clk(stream_clk),.rst_n(stream_rst_n),.open_v(cache_open_v),.open_bank(cache_open_bank),.open_epoch(cache_open_epoch),.open_count(cache_open_count),.open_tag_base(cache_open_tag),
  .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch(epochs),.sector_data(out_data),
  .read_v(programme_v&&programme[83]),.read_bank(programme[84]),.read_epoch(programme[100:85]),.read_row(programme[106:101]),.read_tag(programme[116:107]),
  .retire_v(programme[117]),.retire_bank(programme[118]),.retire_epoch(programme[134:119]),
  .block_ready(cache_ready),.bank_owned(cache_owned),.busy(cache_busy),.fault(cache_fault),.out_packet(packet_observe));
 end else begin:g_native8_cache
 ot_hbm_svc_static_sm_packed136_native8 #(.PACKED136(1)) rows(
  .clk(stream_clk),.rst_n(stream_rst_n),.open_v(cache_open_v),.open_bank(cache_open_bank),.open_epoch(cache_open_epoch),.open_count(cache_open_count),.open_tag_base(cache_open_tag),
  .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch(epochs),.sector_data(out_data),
  .read_v(programme_v&&programme[83]),.read_bank(programme[84]),.read_epoch(programme[100:85]),.read_row(programme[106:101]),.read_tag(programme[116:107]),
  .retire_v(programme[117]),.retire_bank(programme[118]),.retire_epoch(programme[134:119]),
  .block_ready(cache_ready),.bank_owned(cache_owned),.busy(cache_busy),.fault(cache_fault),.out_packet(packet_observe));
 end endgenerate
 // Attention command[25] means KV-converter consume, independently of packet arrival.
 // The unused dense decoder receives packet/tag checks but no dense issue requests.
 wire[82:0]dense_check_command=ATTENTION ? (sm_command & ~(83'd1<<25)) : sm_command;
 ot_smh_static_feed consumer(
  .clk(stream_clk),.rst_n(stream_rst_n),.command(dense_check_command),.packet(packet_observe),
  .expected_request(expected_request),.fault(feed_fault),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
 assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault||inj_f;
endmodule
`default_nettype wire
