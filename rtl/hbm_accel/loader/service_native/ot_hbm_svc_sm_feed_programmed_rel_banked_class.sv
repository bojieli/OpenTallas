// Isolated functional banked/class composition. Native frontend, clock relation and physical qualification remain OPEN.
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
module ot_hbm_svc_sm_feed_programmed_rel_banked_class #(
 parameter integer CLASS_ENABLE=0,CLASS_MUT=0,ENVELOPE_MUT=0, NATIVE_CACHE_SAFE=0,ATTENTION=0,NATIVE_RETURN=0,RETURN_MUT=0,NATIVE_LANDING=0,FIFOMUT=0,PAW=11,PREL=1,
 parameter integer OWNER_AW=5,RESPONSE_DEPTH=8,DECOUPLE=1,OVERLAP=1,LBANKS=4,
 parameter integer LB=(LBANKS>2)?2:1
)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire program_core_clk,input wire[1:0]program_bank_clk,
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
 input wire[46:0]program_start_ctx,
 output wire program_active,program_done,output wire fault,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[1098:0]packet_observe,output wire[134:0]programme_observe,output wire programme_v,
 // H-DIE 2026-10-15: the SM command this programme issues (fixed idle slot = 0), the die net to the SM's command port
 // (the same value the internal consumer copy sees); packet_observe is the die net to the SM's packet port.
 output wire[82:0]sm_command,output wire[84:0]sm_command_envelope,
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
 ot_hbm_svg_meta_delay7 #(.W(OW),.DELAY(8)) u_open_labels(.clk(stream_clk),.rst_n(stream_rst_n),
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
 wire[134:0]programme;wire cache_busy;
 wire cfg0_we,cfg1_we;wire[9:0]bank_cfg_addr;wire[255:0]bank_cfg_data;
 wire[108:0]request0,request1,token0,token1;wire[134:0]row0,row1;wire[8:0]ok0,ok1;
 wire[84:0]app_command_envelope;
 initial if(PAW!=11)$fatal(1,"banked SVG feed requires the real two-bank2048 store");
 ot_smh_calendar_bank_leaf #(.W(135),.XW(47),.BANK(0)) u_program_bank0(
  .clk(program_bank_clk[0]),.rst_n(stream_rst_n),.cfg_we(cfg0_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
  .read_token(request0),.row(row0),.word_ok(ok0),.row_token(token0));
 ot_smh_calendar_bank_leaf #(.W(135),.XW(47),.BANK(1)) u_program_bank1(
  .clk(program_bank_clk[1]),.rst_n(stream_rst_n),.cfg_we(cfg1_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
  .read_token(request1),.row(row1),.word_ok(ok1),.row_token(token1));
 ot_smh_banked_svg_central #(.PREL(PREL),.XW(47),.CLASS_ENABLE(CLASS_ENABLE),.CLASS_MUT(CLASS_MUT)) programme_leaf(
  .clk(program_core_clk),.rst_n(stream_rst_n),.cfg_we(program_cfg_we),.cfg_addr(program_cfg_addr),.cfg_data(program_cfg_data),
  .start_v(program_start_v),.start_base(program_start_base),.start_limit(program_start_limit),.start_loops(program_start_loops),.start_ctx(program_start_ctx),
  .cfg0_we(cfg0_we),.cfg1_we(cfg1_we),.bank_cfg_addr(bank_cfg_addr),.bank_cfg_data(bank_cfg_data),
  .request0(request0),.request1(request1),.row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1),
  .programme(programme),.programme_v(programme_v),.command_class_observe(),.command_context_valid_observe(),.command_envelope(app_command_envelope),
  .active(calendar_active),.done(calendar_done),.fault(programme_fault));
 assign programme_observe=programme;
 // The safe row cache captures all READ/retire inputs two edges later.
 // Preserve their issue edges, and align the entire external command/format.
 reg[84:0] command_d1,command_d2;
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)begin command_d1<=0;command_d2<=0;end
  else begin command_d1<=app_command_envelope;command_d2<=command_d1;end
 assign sm_command_envelope=NATIVE_CACHE_SAFE!=0?(ENVELOPE_MUT==1?command_d1:command_d2):app_command_envelope;
 assign sm_command=sm_command_envelope[82:0];
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
 assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault;
endmodule
`default_nettype wire
