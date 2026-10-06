`timescale 1ps/1fs
`default_nettype none
// Default OFF. Actual index_query_source -> passed FP32 SRAM backend.
// The enclosing protected stage_join holds owner_frame/rank and the real
// allocation through bind, all producer ACKs, query/consumer drain and release.
// TOKEN17 stays at that owner; backend63 is never interpreted as full73.
// No owner/payload copy or new grant. Model hbm_native_index_sram_join_model.
module ot_hbm_integrated_native_index_sram_join #(parameter integer ENABLE=0)(
 input wire clk,por_n,warm_req,
 input wire owner_valid,owner_fault,allocation_granted,
 input wire [72:0] owner_frame,allocation_frame,
 // Protected enclosing bind receipt: asserted only after this window's real
 // bind_v&&bind_ready. Clear on released allocation, never alias backend held63.
 input wire window_bound_valid,input wire [72:0] window_bound_frame,
 input wire [6:0] owner_rank,
 input wire bind_v,output wire bind_ready,
 input wire [31:0] base_word,span_words,
 input wire wr_v,output wire wr_ready,
 input wire [72:0] wr_frame,input wire [31:0] wr_addr,
 input wire [1023:0] wr_data,
 output wire wr_ACK_v,input wire wr_ACK_ready,
 output wire [72:0] wr_ACK_frame,output wire [31:0] wr_ACK_addr,
 output wire positive_publication_ACK,
 // This must be the actual producer's retained checked-publication completion,
 // not issued-write count, CRC, or source-engine done without provider ACKs.
 input wire producer_published,producer_drained,
 input wire start_v,output wire start_ready,input wire [72:0] start_frame,
 input wire [31:0] original_q_base,rotated_q_base,scaled_weight_base,
 input wire [7:0] source_tail_words,
 output wire block_v,input wire block_r,
 output wire [72:0] block_frame,output wire [6:0] block_rank,
 output wire [4:0] block_head,output wire [1:0] block_number,
 output wire [1023:0] block_data,output wire [15:0] head_weight,
 output wire query_done,backend_drained,query_idle,fault
);
 wire lease_allowed=ENABLE&&owner_valid&&!owner_fault&&allocation_granted&&allocation_frame==owner_frame;
 wire allowed=lease_allowed&&window_bound_valid&&window_bound_frame==owner_frame;
 wire write_match=wr_frame==owner_frame;
 wire start_match=start_frame==owner_frame;
 wire q_ready,b_ready,b_held,b_wr_r,b_ack_v,b_positive,b_fault,q_fault;
 wire [31:0] ack_job;wire [3:0] ack_gen;wire [19:0] ack_pos;wire [6:0] ack_rank;
 wire ack_match={ack_job,ack_gen,ack_pos,ack_rank}==
                {owner_frame[31:0],owner_frame[35:32],owner_frame[72:53],owner_rank};
 // Warm blocks new bind/query only; writes/ACKs needed by the accepted producer
 // and all accepted query responses continue. POR is cold, never warm reset.
 wire new_bind=lease_allowed&&!warm_req&&q_ready;
 assign bind_ready=new_bind&&b_ready;
 wire source_start=allowed&&!warm_req&&start_match&&b_held&&backend_drained&&producer_published&&producer_drained;
 assign start_ready=source_start&&q_ready&&!bind_v&&!wr_v;
 assign wr_ready=allowed&&write_match&&b_wr_r;
 assign wr_ACK_v=allowed&&ack_match&&b_ack_v;
 assign wr_ACK_frame=owner_frame;
 assign positive_publication_ACK=wr_ACK_v&&wr_ACK_ready&&b_positive;
 assign block_frame=owner_frame;assign block_rank=owner_rank;
 assign query_idle=q_ready;
 assign fault=ENABLE&&(owner_fault||b_fault||q_fault||
              (owner_valid&&allocation_granted&&allocation_frame!=owner_frame)||
              (wr_v&&!write_match)||(start_v&&!start_match)||(b_ack_v&&!ack_match));
 wire rd_v,rd_r,rsp_v,rsp_r;wire [31:0] rd_addr,rd_job,rsp_job;
 wire [7:0] rd_tag,rsp_tag;wire [5:0] rd_words;
 wire [3:0] rd_gen,rsp_gen;wire [19:0] rd_pos,rsp_pos;
 wire [6:0] rd_rank,rsp_rank;wire [1023:0] rsp_data;
 wire source_block_v;
 assign block_v=allowed&&source_block_v;
 ot_hbm_accel_index_query_source #(.ENABLE(ENABLE)) u_query(
  .clk(clk),.por_n(por_n),.start(start_v&&start_ready),.start_ready(q_ready),
  .source_job(owner_frame[31:0]),.source_gen(owner_frame[35:32]),
  .source_pos(owner_frame[72:53]),.source_rank(owner_rank),
  .original_q_base(original_q_base),.rotated_q_base(rotated_q_base),
  .scaled_weight_base(scaled_weight_base),.source_tail_words(source_tail_words),
  .read_v(rd_v),.read_r(rd_r),.read_addr(rd_addr),.read_tag(rd_tag),.read_words(rd_words),
  .read_job(rd_job),.read_gen(rd_gen),.read_pos(rd_pos),.read_rank(rd_rank),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_data(rsp_data),.rsp_tag(rsp_tag),
  .rsp_job(rsp_job),.rsp_gen(rsp_gen),.rsp_pos(rsp_pos),.rsp_rank(rsp_rank),
  .block_v(source_block_v),.block_r(block_r&&allowed),.block_head(block_head),
  .block_number(block_number),.block_data(block_data),.head_weight(head_weight),
  .fault(q_fault),.done(query_done));
 wire backend_rd_r;
 assign rd_r=backend_rd_r&&allowed;
 ot_hbm_index_fp32_sram_adapter #(.ENABLE(ENABLE)) u_backend(
  .clk(clk),.por_n(por_n),.bind_v(bind_v&&new_bind),.bind_ready(b_ready),
  .bind_base_word(base_word),.bind_span_words(span_words),
  .bind_job(owner_frame[31:0]),.bind_gen(owner_frame[35:32]),
  .bind_pos(owner_frame[72:53]),.bind_rank(owner_rank),.owner_held(b_held),
  .wr_v(wr_v&&allowed&&write_match),.wr_ready(b_wr_r),.wr_addr(wr_addr),.wr_data(wr_data),
  .wr_job(wr_frame[31:0]),.wr_gen(wr_frame[35:32]),.wr_pos(wr_frame[72:53]),.wr_rank(owner_rank),
  .wr_ACK_v(b_ack_v),.wr_ACK_ready(wr_ACK_ready&&allowed&&ack_match),
  .wr_ACK_addr(wr_ACK_addr),.wr_ACK_job(ack_job),.wr_ACK_gen(ack_gen),
  .wr_ACK_pos(ack_pos),.wr_ACK_rank(ack_rank),.positive_publication_ACK(b_positive),
  .read_v(rd_v&&allowed),.read_r(backend_rd_r),.read_addr(rd_addr),.read_words(rd_words),
  .read_tag(rd_tag),.read_job(rd_job),.read_gen(rd_gen),.read_pos(rd_pos),.read_rank(rd_rank),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_data(rsp_data),.rsp_tag(rsp_tag),
  .rsp_job(rsp_job),.rsp_gen(rsp_gen),.rsp_pos(rsp_pos),.rsp_rank(rsp_rank),
  .drained(backend_drained),.fault(b_fault));
endmodule
`default_nettype wire
