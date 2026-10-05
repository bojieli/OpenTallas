`timescale 1ps/1fs
// Default-off ONE installed CODE pair. The issuer holds all span/context pins
// unchanged until matched reverse ACK and all declared read leases terminate.
// Publication is an external actual hardware authority, not private visibility.
module ot_hbm_qwen_code_pair_join #(
 parameter integer ENABLE=0,NSEG=8,CW=32,ROWS=4496,READ_ALIGN=0,MEM_EXTRA=0
)(
 input wire service_clk,core_clk,por_n,
 input wire service_v,output wire service_r,input ot_hbm_r14_pkg::owned_t service_owned,
 input wire installed,input wire[1:0] span_stack,input wire[33:0] first_sector,
 input wire[13:0] span_rows,input wire[12:0] first_row,
 input wire[63:0] operation,input wire[31:0] phase,input wire[6:0] rank,
 input wire hardware_owner_valid,input ot_hbm_r14_pkg::identity_t expected_identity,
 input wire[NSEG*24-1:0] seg_base,seg_len,input wire[NSEG*CW-1:0] seg_sidx,
 input wire[NSEG*2-1:0] seg_kind,input wire[2:0] installed_segment,
 input wire[23:0] installed_base,installed_length,input wire[CW-1:0] installed_sidx,
 input wire[1:0] installed_kind,input wire published,
 input wire read_v,input wire[23:0] virtual_address,
 output wire[1:0] read_accepted,output wire read_ready,output wire[1:0] read_response_valid,
 output wire[511:0] read_data,output wire[2:0] read_bank,
 input wire consumer_enable,input wire[1:0] response_ready,
 output wire[2659:0] rom_rd,output wire[1:0] tile_response_valid,
 output wire fault,output wire crossing_empty
);
 import ot_hbm_r14_pkg::*;
 owned_t delivered;wire ov,ore,xf,mapf,lv,pv,pready,lf,rf;
 wire[592:0] packet;wire[336:0] key;
 identity_t visible_id;wire[11:0] visible_tag,visible_col;wire[4:0] visible_beat;
 wire[12:0] visible_row,read_row;wire bound;wire[1:0] rr,alignment_ready;wire alignment_fault;
 wire read_issue=read_v&&bound&&(&alignment_ready);
 reg write_pending;
 wire span_format=installed&&(installed_kind==1||installed_kind==2)&&
   installed_length==span_rows&&installed_length!=0&&installed_segment<NSEG&&
   seg_base[installed_segment*24+:24]==installed_base&&
   seg_len[installed_segment*24+:24]==installed_length&&
   seg_sidx[installed_segment*CW+:CW]==installed_sidx&&
   seg_kind[installed_segment*2+:2]==installed_kind&&
   ({1'b0,installed_base}+{1'b0,installed_length})<=25'h1000000;
 ot_hbm_accel_owned_crossing crossing(.service_clk(service_clk),.stream_clk(core_clk),.por_n(por_n),
  .iv(service_v&&ENABLE),.ir(service_r),.id(service_owned),.ov(ov),.ore(ore),.od(delivered),.fault(xf),.empty(crossing_empty));
 assign key={operation,phase,rank,visible_row,visible_col,visible_id,visible_tag,visible_beat};
 ot_hbm_qwen_code_leaf_map #(.ENABLE(ENABLE),.ROWS(ROWS)) mapper(
 .clk(core_clk),.por_n(por_n),.owned_v(ov),.owned_r(ore),.owned(delivered),.owned_we(1'b0),.owned_credit(1'b0),
 .installed_span_valid(span_format),.span_stack(span_stack),.span_first_sector(first_sector),
 .span_rows(span_rows),.span_first_row(first_row),.span_first_column(12'd0),
 .operation(operation),.phase(phase),.global_rank(rank),.hardware_owner_valid(hardware_owner_valid),
 .expected_identity(expected_identity),.leaf_v(lv),.leaf_packet(packet),
 .private_visible(pv),.private_visible_key(key),.fault(mapf));
 // ov remains asserted across the reverse crossing: write exactly once.
 always @(posedge core_clk or negedge por_n)
  if(!por_n)write_pending<=0;
  else if(ore)write_pending<=0;
  else if(lv&&!write_pending&&pready)write_pending<=1;
 ot_hbm_qwen_code_span_read #(.ENABLE(ENABLE),.NSEG(NSEG),.CW(CW),.ROWS(ROWS)) read_mapper(
 .seg_base(seg_base),.seg_len(seg_len),.seg_sidx(seg_sidx),.seg_kind(seg_kind),.installed(installed),
 .installed_segment(installed_segment),.installed_base(installed_base),.installed_length(installed_length),
 .installed_sidx(installed_sidx),.installed_kind(installed_kind),.installed_first_row(first_row),
 .installed_rows(span_rows),.published(published),.read_v(read_v),.virtual_address(virtual_address),
 .read_bound(bound),.physical_row(read_row),.virtual_bank(read_bank),.mapping_fault(rf));
 ot_qwen_hbm_code_payload_pair #(.ENABLE(ENABLE),.COLUMN_BASE(0),.ROWS(ROWS)) leaf(
 .clk(core_clk),.por_n(por_n),.wr_v(lv&&!write_pending),.wr_r(pready),.wr_owned(delivered),
 .wr_span_bound(span_format),.wr_kind(1'b0),.wr_row(packet[489:477]),.wr_column(packet[476:465]),
 .visible_v(pv),.visible_r(ore),.visible_id(visible_id),.visible_tag(visible_tag),.visible_beat(visible_beat),
 .visible_row(visible_row),.visible_column(visible_col),.rd_v({2{read_issue}}),
 .rd_span_bound({2{bound}}),.rd_published({2{published}}),.rd_row({read_row,read_row}),
 .rd_r(rr),.rd_rsp_v(read_response_valid),.rd_data(read_data),.rd_corrected(),.rd_uncorrectable(),.fault(lf));
 assign read_accepted=rr & {2{read_issue}};
 generate if(READ_ALIGN==2)begin:fixed_pipeline
 assign alignment_ready=2'b11;
 ot_qwen_hbm_code_read_pipeline #(.ENABLE(ENABLE)) align(
  .clk(core_clk),.por_n(por_n),.rd_fire(read_accepted),.virtual_bank({read_bank,read_bank}),
  .leaf_rd_rsp_v(read_response_valid),.leaf_rd_data(read_data),.leaf_fault(lf),
  .rom_rd(rom_rd),.rsp_v(tile_response_valid),.fault(alignment_fault));
 end else if(READ_ALIGN==1)begin:read_alignment
 ot_qwen_hbm_code_read_align #(.ENABLE(ENABLE),.MEM_EXTRA(MEM_EXTRA)) align(
  .clk(core_clk),.por_n(por_n),.consumer_enable(consumer_enable),
  .rd_fire(rr & {2{read_issue}}),.virtual_bank({read_bank,read_bank}),
  .leaf_rd_rsp_v(read_response_valid),.leaf_rd_data(read_data),.leaf_fault(lf),
  .consumer_ready(alignment_ready),.rsp_v(tile_response_valid),.rsp_ready(response_ready),
  .rom_rd(rom_rd),.fault(alignment_fault));
 end else begin:raw_leaf_only
 assign alignment_ready=2'b11;assign alignment_fault=0;
 assign rom_rd=0;assign tile_response_valid=0;
 end endgenerate
 assign read_ready=bound&&(&rr)&&(&alignment_ready)&&!fault;
 assign fault=xf||mapf||lf||rf||alignment_fault;
endmodule
