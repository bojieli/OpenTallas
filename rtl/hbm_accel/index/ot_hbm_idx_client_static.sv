`timescale 1ns/1ps
`default_nettype none
// The SW IDX client (H-IDX 2026-10-15): the die's one IDX unit, static. INDEX = ot_hbm_idx_scheduled_static
// (programme SRAM issuer + full static parent, unchanged), TOPK = ot_hbm_idx_topk_static, both on the ONE SW IDX
// read group (read group 4 of hfd_hgi_vms_static_SW) through ot_hbm_idx_vm_share_static (four bank-pair leaves,
// compiler-booked owners, zero added latency). TOPK writes its O/R sectors through the SW 'idx' record client
// (packet client 4: cq338/client_seq2/cr274). No credit, lease, ready or queue on any port.
// v15 binding (replaces hb_idx = ot_hbm_idx_scheduled_static): vm_rq/vm_rr -> hb_vms_SW rq/rr group 4,
// cq/cq_seq/cr -> hb_vms_SW cq/client_seq/cr client 4, sid = 0 (declared constant), TOPK descriptor/go -> the
// IDX record issuer (programme loader / CP), done/fault -> calendar fault aggregation.
module ot_hbm_idx_client_static(
 input wire clk_program,clk_program_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[3:0]clk_score,input wire[15:0]clk_engine,clk_meta,clk_tail,
 input wire[63:0]clk_chunk,input wire[2047:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire[3:0]clk_pair,input wire clk_topk,input wire rst_n,
 input wire[1:0]sid,input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire[6:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[1367:0]keep_bitmap,
 output wire key_slot,output wire[7:0]key_index,input wire[35167:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[2439:0]score_observe,output wire done,fault,
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,output wire share_fault
);
 wire[135:0]index_rq,topk_rq;wire[2055:0]index_rr,topk_rr;
 ot_hbm_idx_scheduled_static index(.clk_program(clk_program),.clk_program_mem(clk_program_mem),.program_we(program_we),
  .program_addr(program_addr),.program_data(program_data),.start(start),.length(length),.clk_operand(clk_operand),
  .clk_query(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_query_bank(clk_query_bank),
  .clk_score(clk_score),.clk_engine(clk_engine),.clk_meta(clk_meta),.clk_tail(clk_tail),.clk_chunk(clk_chunk),
  .clk_hslice(clk_hslice),.clk_sel(clk_sel),.clk_sel_q(clk_sel_q),.clk_sel_mem(clk_sel_mem),.clk_link(clk_link),
  .clk_link_mem(clk_link_mem),.rst_n(rst_n),.sid(sid),.weight_sector(weight_sector),.query_sector(query_sector),
  .vm_rq(index_rq),.vm_rr(index_rr),.rank(rank),.gbase(gbase),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),
  .key_slot(key_slot),.key_index(key_index),.key_lines(key_lines),.tx_v(tx_v),.tx(tx),.score_observe(score_observe),
  .done(done),.fault(fault));
 ot_hbm_idx_topk_static topk(.clk(clk_topk),.rst_n(rst_n),.sid(sid),.go(topk_go),.k(topk_k),.order(topk_order),
  .n(topk_n),.m(topk_m),.a_mirror(topk_a_mirror),.a_base(topk_a_base),.a_str(topk_a_str),.o_mirror(topk_o_mirror),
  .o_base(topk_o_base),.o_str(topk_o_str),.has_r(topk_has_r),.r_base(topk_r_base),.r_str(topk_r_str),
  .vm_rq(topk_rq),.vm_rr(topk_rr),.cq(cq),.cq_seq(cq_seq),.cr(cr),.busy(topk_busy),.done(topk_done),.fault(topk_fault));
 ot_hbm_idx_vm_share_static share(.clk_pair(clk_pair),.rst_n(rst_n),.index_rq(index_rq),.topk_rq(topk_rq),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.index_rr(index_rr),.topk_rr(topk_rr),.fault(share_fault));
endmodule
`default_nettype wire
