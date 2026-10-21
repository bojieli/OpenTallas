`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED programme feed of the svg = ot_hbm_svc_sm_feed_programmed_rel_id at the r11 die
// parameters (PREL 1, XSLOT 0, OPEN_IL 0, DECOUPLE 1, LBANKS 4) INCLUDING the HBM-QINT8 S1 INT8 view (PREL word bit
// [118] packed-line mark, held tag 2 deep); that module stays byte-identical.  Same RELOC stages, same programme /
// sm_command / packet_observe on every edge, same S1 consumer fault rule.  Changes:
//   * producer = ot_hbm_svc_sm4pc_cdc_rel_h, programme leaf = ot_smh_calendar_static_xh, cache =
//     ot_hbm_svc_static_sm_packed136_h (see those headers);
//   * the RELOC R stage needs no word_v enable: the leaf drives calendar / ctx / iter / lastit to 0 on every edge
//     without a valid word, so the ungated stage computes the same zero (no 135-bit enable net);
//   * the S1 consumer copy is reduced to what the die reads -- its fault: expected_request / lt0 / lt1 / lb0 / lb1 / fm
//     were open outputs of the GEN2e4 r11 die (contract_pre open_outputs, 3,359 b per svg), and their registers fed
//     nothing else; the fault rule (packet valid == command[29], tag == command[39:30] when valid, issue implies packet)
//     is ot_smh_static_feed's, registered on the same edge;
//   * reset only on control (rst_n leaves); rows_q / tag_q / open fields are datapath (read only at an open of a
//     reserved landing block).
module ot_hbm_svc_sm_feed_rel_h #(
 parameter integer PAW=11,LBANKS=4,
 parameter integer LB=(LBANKS>2)?2:1
)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,
 input wire stream_clk,hbm_clk,
 input wire [3:0] st_rst,                // stream family (stream_rst_n): [0] feed control, [1:2] programme leaf, [3] cache
 input wire [11:0] s_rst,input wire [14:0] h_rst,   // producer families (either port reset)
 input wire reserve_v,output wire reserve_ready,input wire[31:0]reserve_base,
 input wire[14:0]reserve_row_base,input wire[11:0]reserve_total,
 input wire[LB-1:0]reserve_bank,input wire[15:0]reserve_epoch,input wire[6:0]reserve_rows,input wire[9:0]reserve_tag_base,
 output wire[LBANKS-1:0]block_ready,output wire[1:0]cache_ready,cache_owned,
 input wire start_v,input wire[LB-1:0]start_bank,input wire[15:0]start_epoch,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire program_start_v,input wire[PAW-1:0]program_start_base,input wire[PAW:0]program_start_limit,input wire[15:0]program_start_loops,
 input wire[45:0]program_start_ctx,
 output wire program_active,program_done,output wire fault,
 output wire[1098:0]packet_observe,
 output wire[82:0]sm_command,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 localparam integer PREL=1;
 wire cdc_ready,cdc_fault,cache_fault,programme_fault;reg feed_fault;
 reg descriptor_fault;wire[12:0]expected_sectors=(((reserve_rows*136)+127)>>7)<<2;
 wire legal=reserve_rows!=0&&reserve_rows<=64&&reserve_total==expected_sectors;
 assign reserve_ready=cdc_ready&&legal;      // DECOUPLE 1
 wire reserve_fire=reserve_v&&reserve_ready;
 reg[6:0]rows_q[0:LBANKS-1];reg[9:0]tag_q[0:LBANKS-1];reg open_q;reg[LB-1:0]open_land_q;reg[15:0]open_epoch_q;integer qb;
 wire open_bank_q=open_land_q[0];
 always @(posedge stream_clk)begin
  for(qb=0;qb<LBANKS;qb=qb+1)if(reserve_fire&&reserve_bank==qb)begin rows_q[qb]<=reserve_rows;tag_q[qb]<=reserve_tag_base;end
  open_land_q<=start_bank;open_epoch_q<=start_epoch;
 end
 wire out_v,out_last;wire[LB-1:0]out_bank;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 ot_hbm_svc_sm4pc_cdc_rel_h #(.LBANKS(LBANKS)) producer(
  .id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.hbm_clk(hbm_clk),.s_rst(s_rst),.h_rst(h_rst),
  .reserve_v(reserve_fire),.reserve_ready(cdc_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),
  .block_ready(block_ready),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(cdc_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire[95:0]indices;wire[63:0]epochs;
 for(genvar l=0;l<4;l=l+1)begin:metadata
  assign indices[l*24+:24]=out_ordinal+l;assign epochs[l*16+:16]=out_epoch;
 end
 wire[134:0]word;wire[45:0]wctx;wire[15:0]wit;wire wlast,word_v;wire[31:0]ordinal;wire cache_busy;
 ot_smh_calendar_static_xh #(.W(135),.AW(PAW),.XW(46)) programme_leaf(
  .clk(stream_clk),.rst_n(st_rst[2:1]),.cfg_we(program_cfg_we),.cfg_addr(program_cfg_addr),.cfg_data(program_cfg_data),
  .start_v(program_start_v),.start_base(program_start_base),.start_limit(program_start_limit),.start_loops(program_start_loops),
  .start_ctx(program_start_ctx),.calendar(word),.calendar_ctx(wctx),.calendar_iter(wit),.calendar_lastit(wlast),
  .calendar_v(word_v),.ordinal(ordinal),.active(program_active),.done(program_done),.fault(programme_fault));
 // RELOC (P2), as ot_hbm_svc_sm_feed_programmed_rel_id PREL 1 / XSLOT 0
 wire[11:0]c_roff=wctx[45:34];wire[9:0]c_tag=wctx[33:24];wire[15:0]c_ep=wctx[23:8];wire c_bank=wctx[7];
 wire[3:0]c_lstep=wctx[6:3];wire c_fl=wctx[2];wire[1:0]c_fmt=wctx[1:0];
 wire looped=c_lstep!=0;
 wire[9:0]c_lofs=wit[5:0]*c_lstep;
 reg[33:0]rd_r;
 reg[82:0]cmd_r,cmd_c;reg ret_r,ret_c;reg[16:0]retf_r,retf_c;reg inj_f;
 reg[134:0]programme;reg programme_v_q;
 reg i8_r,i8_c,i8_p1,i8_p2,i8_p3,i8_f;reg[9:0]i8_t1,i8_t2;   // HBM-QINT8 mark (R, C) + converter view
 wire raw_v=packet_observe[1098];wire[9:0]raw_tag=packet_observe[1097:1088];
 wire i8_conv=i8_p2||i8_p3;
 // HBM-QINT8: the packet the SM front sees (the raw packet when no INT8 mark is in flight)
 wire s1_v=i8_conv||(raw_v&&!i8_c);wire[9:0]s1_tag=i8_conv?i8_t2:raw_tag;
 wire[1098:0]s1_packet={s1_v,s1_tag,packet_observe[1087:0]};   // bench visibility (tb i8view check); no load
 always @(posedge stream_clk)begin
  // R stage (ungated: every field is 0 on an edge without a valid word)
  cmd_r<=word[82:0];rd_r<=word[116:83];
  if(word[25])begin
   cmd_r[22:11]<=word[22:11]+c_roff;cmd_r[9:7]<=word[9:7]+c_roff[2:0];
   if(looped)begin cmd_r[6:0]<=word[6:0]+wit[6:0];cmd_r[24]<=word[24]|(wit==0);cmd_r[23]<=word[23]|wlast;end
  end
  if(word[29])cmd_r[39:30]<=word[39:30]+c_tag+c_lofs;
  if(word[83])begin rd_r[1]<=c_bank;rd_r[17:2]<=c_ep;rd_r[23:18]<=word[106:101]+c_lofs[5:0];rd_r[33:24]<=word[116:107]+c_tag+c_lofs;end
  ret_r<=word[117]&&(!looped||wlast);retf_r<={c_ep,c_bank};
  // C stage
  cmd_c<=cmd_r;ret_c<=ret_r;retf_c<=retf_r;
  if(word_v&&ordinal==0&&c_fl)begin cmd_c[28]<=1'b1;cmd_c[27:26]<=c_fmt;end
  if(i8_c&&raw_v)i8_t1<=raw_tag;i8_t2<=i8_t1;     // held tag (as ot_smh_static_int8), 2 deep: no delay line
 end
 always @(posedge stream_clk or negedge st_rst[0])
  if(!st_rst[0])begin
   descriptor_fault<=0;open_q<=0;programme_v_q<=0;inj_f<=0;i8_r<=0;i8_c<=0;i8_p1<=0;i8_p2<=0;i8_p3<=0;i8_f<=0;feed_fault<=0;
  end else begin
   if(reserve_v&&!reserve_ready)descriptor_fault<=1;
   open_q<=start_v;
   programme_v_q<=word_v;
   if(word_v&&ordinal==0&&c_fl&&(cmd_r!=0||ret_r))inj_f<=1;     // format launch slot not idle
   i8_r<=word_v&&word[118];i8_c<=i8_r;
   i8_p1<=i8_c&&raw_v;i8_p2<=i8_p1;i8_p3<=i8_p2;
   if((i8_c&&(!raw_v||i8_p1))||(!i8_c&&raw_v&&i8_conv))i8_f<=1;
   // S1 consumer copy (ot_smh_static_feed MUT 0) on the SM-front INT8 view
   if(s1_v!=sm_command[29]||(sm_command[29]&&s1_tag!=sm_command[39:30])||(sm_command[25]&&!sm_command[29]))feed_fault<=1;
  end
 always @* begin
  programme=0;
  programme[116:83]=rd_r;programme[82:0]=cmd_c;programme[117]=ret_c;programme[134:118]=retf_c;
 end
 assign sm_command=programme[82:0];
 ot_hbm_svc_static_sm_packed136_h rows(
  .clk(stream_clk),.rst_n(st_rst[3]),.open_v(open_q),.open_bank(open_bank_q),.open_epoch(open_epoch_q),.open_count(rows_q[open_land_q]),.open_tag_base(tag_q[open_land_q]),
  .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch(epochs),.sector_data(out_data),
  .read_v(programme_v_q&&programme[83]),.read_bank(programme[84]),.read_epoch(programme[100:85]),.read_row(programme[106:101]),.read_tag(programme[116:107]),
  .retire_v(programme[117]),.retire_bank(programme[118]),.retire_epoch(programme[134:119]),
  .block_ready(cache_ready),.bank_owned(cache_owned),.busy(cache_busy),.fault(cache_fault),.out_packet(packet_observe));
 assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault||inj_f||i8_f;
endmodule
`default_nettype wire
