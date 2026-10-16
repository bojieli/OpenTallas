`timescale 1ns/1ps
`default_nettype none
// PRIMARY CANDIDATE only. Actual four-PC producer -> eight landing SRAMs ->
// five canonical-row SRAMs -> actual static SM S1 feed. No arithmetic substitute.
// Programme envelope W135 preserves the SM command at[82:0], adds fixed cache
// read/retire metadata. It replaces, never duplicates, the SM programme leaf
// when adopted. Existing production 83-bit ABI is not silently changed.
// [83]read_v,[84]bank,[100:85]epoch,[106:101]row,[116:107]tag;
// [117]retire_v,[118]bank,[134:119]epoch. Read precedes expected packet by1word.
module ot_hbm_svc_sm_feed_programmed #(
 parameter [1:0] STACK=0,parameter integer SM=0,OWNER_AW=5,RESPONSE_DEPTH=8
)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire reserve_v,output wire reserve_ready,input wire[31:0]reserve_base,
 input wire[14:0]reserve_row_base,input wire[11:0]reserve_total,
 input wire reserve_bank,input wire[15:0]reserve_epoch,input wire[6:0]reserve_rows,input wire[9:0]reserve_tag_base,
 output wire[1:0]block_ready,cache_ready,cache_owned,
 input wire start_v,start_bank,input wire[15:0]start_epoch,
 input wire program_cfg_we,input wire[9:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire program_start_v,input wire[9:0]program_start_base,input wire[10:0]program_start_limit,input wire[15:0]program_start_loops,
 output wire program_active,program_done,output wire fault,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[1098:0]packet_observe,output wire[134:0]programme_observe,output wire programme_v,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 wire cdc_ready,cdc_fault,cache_fault,programme_fault,feed_fault;
 reg descriptor_fault;wire[12:0]expected_sectors=(((reserve_rows*136)+127)>>7)<<2;
 wire legal=reserve_rows!=0&&reserve_rows<=64&&reserve_total==expected_sectors;
 assign reserve_ready=cdc_ready&&!cache_owned[reserve_bank]&&legal;
 wire reserve_fire=reserve_v&&reserve_ready;
 reg[6:0]rows_q[0:1];reg[9:0]tag_q[0:1];reg open_q,open_bank_q;reg[15:0]open_epoch_q;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin descriptor_fault<=0;open_q<=0;open_bank_q<=0;open_epoch_q<=0;rows_q[0]<=0;rows_q[1]<=0;tag_q[0]<=0;tag_q[1]<=0;end
  else begin
   if(reserve_v&&!reserve_ready)descriptor_fault<=1;
   if(reserve_fire)begin rows_q[reserve_bank]<=reserve_rows;tag_q[reserve_bank]<=reserve_tag_base;end
   open_q<=start_v;open_bank_q<=start_bank;open_epoch_q<=start_epoch;
  end
 end
 wire out_v,out_bank,out_last;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 ot_hbm_svc_sm4pc_cdc #(.STACK(STACK),.SM(SM),.OWNER_AW(OWNER_AW),.RESPONSE_DEPTH(RESPONSE_DEPTH)) producer(
  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),
  .reserve_v(reserve_fire),.reserve_ready(cdc_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),
  .block_ready(block_ready),.block_ready_v(),.block_ready_bank(),.block_ready_epoch(),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(cdc_fault),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire[95:0]indices;wire[63:0]epochs;
 for(genvar l=0;l<4;l=l+1)begin:metadata
  assign indices[l*24+:24]=out_ordinal+l;assign epochs[l*16+:16]=out_epoch;
 end
 wire[134:0]programme;wire[31:0]ordinal;wire cache_busy;
 ot_smh_calendar_static #(.W(135)) programme_leaf(
  .clk(stream_clk),.rst_n(stream_rst_n),.cfg_we(program_cfg_we),.cfg_addr(program_cfg_addr),.cfg_data(program_cfg_data),
  .start_v(program_start_v),.start_base(program_start_base),.start_limit(program_start_limit),.start_loops(program_start_loops),
  .calendar(programme),.calendar_v(programme_v),.ordinal(ordinal),.active(program_active),.done(program_done),.fault(programme_fault));
 assign programme_observe=programme;
 ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) rows(
  .clk(stream_clk),.rst_n(stream_rst_n),.open_v(open_q),.open_bank(open_bank_q),.open_epoch(open_epoch_q),.open_count(rows_q[open_bank_q]),.open_tag_base(tag_q[open_bank_q]),
  .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch(epochs),.sector_data(out_data),
  .read_v(programme_v&&programme[83]),.read_bank(programme[84]),.read_epoch(programme[100:85]),.read_row(programme[106:101]),.read_tag(programme[116:107]),
  .retire_v(programme_v&&programme[117]),.retire_bank(programme[118]),.retire_epoch(programme[134:119]),
  .block_ready(cache_ready),.bank_owned(cache_owned),.busy(cache_busy),.fault(cache_fault),.out_packet(packet_observe));
 ot_smh_static_feed consumer(
  .clk(stream_clk),.rst_n(stream_rst_n),.command(programme_v?programme[82:0]:83'd0),.packet(packet_observe),
  .expected_request(expected_request),.fault(feed_fault),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
 assign fault=descriptor_fault||cdc_fault||cache_fault||programme_fault||feed_fault;
endmodule
`default_nettype wire
