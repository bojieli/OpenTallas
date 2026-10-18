`timescale 1ns/1ps
`default_nettype none
// SOFT composition of the die's SW IDX client (H-NETLIST/IDXP 2026-10-16; H-DIE grant 6413258a6 'hb_idx as a SOFT
// hierarchy'). Same ports as ot_hbm_idx_client_static_sw. WIRES AND CONSTANTS ONLY: every gate/register of the
// client's glue lives in ot_hbm_idx_ctl_static, so each instance below is a die-level instance hb_idx__<name>
// (tools/hbm_die_v15/idx_soft_parent_1016.py) and the v16 die binds them at the grant slots idx_ctl, idx_op, idx_q,
// idx_s0..s3, idx_sel, idx_link. Proof of equivalence with ot_hbm_idx_client_static_sw (leaf children cut, all
// glue compared, sequential induction): results/arch/hbm_idx_soft_parent_1016/equiv.
module ot_hbm_idx_client_static_soft #(parameter integer N_Q=4,TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(   // N_Q as ot_hbm_idx_parent_static (A2P: 2)
 input wire clk_program,clk_program_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[N_Q-1:0]clk_score,input wire[4*N_Q-1:0]clk_engine,clk_meta,clk_tail,
 input wire[16*N_Q-1:0]clk_chunk,input wire[512*N_Q-1:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire[3:0]clk_pair,input wire clk_topk,input wire rst_n,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire[RANK_W-1:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[342*N_Q-1:0]keep_bitmap,
 output wire key_slot,output wire[7:0]key_index,input wire[8792*N_Q-1:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[610*N_Q-1:0]score_observe,output wire done,fault,
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,output wire share_fault,
 // third owner of the SW IDX read group: the static ARGMAX.LOCAL VM reader (ot_hbm_argmax_static, separate unit)
 input wire[135:0]argmax_rq,output wire[2055:0]argmax_rr
);
 wire weight_slot,query_slot,query_emit,key_slot_w,ingest_v,link_flush,link_emit;
 wire[6:0]query_index;wire[4:0]query_emit_head;wire[7:0]key_index_w;
 wire[3:0]sel_op;wire[1:0]sel_pass;wire[7:0]sel_addr;wire[3:0]link_group;wire[12*N_Q-1:0]nq;
 wire vf,qf,sf,lf;wire[N_Q-1:0]scf;wire[3:0]selected_v;
 wire[135:0]index_rq;wire[2055:0]index_rr;
 assign key_slot=key_slot_w;assign key_index=key_index_w;
 ot_hbm_idx_ctl_static #(.N_Q(N_Q)) ctl(.clk_program(clk_program),.clk_program_mem(clk_program_mem),.clk_sel(clk_sel),.clk_topk(clk_topk),
  .clk_pair(clk_pair),.rst_n(rst_n),.program_we(program_we),.program_addr(program_addr),.program_data(program_data),
  .start(start),.length(length),.nkeys(nkeys),.weight_slot(weight_slot),.query_slot(query_slot),.query_index(query_index),
  .query_emit(query_emit),.query_emit_head(query_emit_head),.key_slot(key_slot_w),.key_index(key_index_w),
  .sel_op(sel_op),.sel_pass(sel_pass),.sel_addr(sel_addr),.link_flush(link_flush),.link_emit(link_emit),.link_group(link_group),
  .nq(nq),.selected_v(selected_v),.ingest_v(ingest_v),.score0_ev(score_observe[0]),.vf(vf),.qf(qf),.scf(scf),.sf(sf),.lf(lf),
  .done(done),.fault(fault),.topk_go(topk_go),.topk_k(topk_k),.topk_order(topk_order),.topk_n(topk_n),.topk_m(topk_m),
  .topk_a_mirror(topk_a_mirror),.topk_a_base(topk_a_base),.topk_a_str(topk_a_str),.topk_o_mirror(topk_o_mirror),
  .topk_o_base(topk_o_base),.topk_o_str(topk_o_str),.topk_has_r(topk_has_r),.topk_r_base(topk_r_base),.topk_r_str(topk_r_str),
  .cq(cq),.cq_seq(cq_seq),.cr(cr),.topk_busy(topk_busy),.topk_done(topk_done),.topk_fault(topk_fault),
  .index_rq(index_rq),.index_rr(index_rr),.argmax_rq(argmax_rq),.argmax_rr(argmax_rr),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .share_fault(share_fault));
 wire bv;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]bw;
 ot_hbm_idx_vm_query_static operands(.clk(clk_operand),.rst_n(rst_n),.sid(2'd0),.weight_slot(weight_slot),.query_slot(query_slot),
  .query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(index_rq),.vm_rr(index_rr),
  .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),.fault(vf));
 wire qv;wire[7:0]qh;wire[511:0]qc;wire[31:0]qs;wire[15:0]qw;
 ot_hbm_idx_query_static query(.clk(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_query_bank),
  .rst_n(rst_n),.frame_start(start),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
  .emit_v(query_emit),.emit_head(query_emit_head),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.fault(qf));
 wire[2367:0]sel_in;wire[2367:0]selected_line;
 wire[610*N_Q-1:0]score_all;
 assign score_observe=score_all;
 if(N_Q<4)begin:gabsent
  assign sel_in[2367:N_Q*592]='0;                 // absent scorer slots: no valid lane (kv 0), as ot_hbm_idx_parent_static
 end
 for(genvar q=0;q<N_Q;q=q+1)begin:gscore
  for(genvar l=0;l<16;l=l+1)begin:lane
   assign sel_in[q*592+l*37+:37]={score_all[q*610+290+l*20+:20],score_all[q*610+34+l*16+:16],score_all[q*610+18+l]};
  end
  ot_hbm_idx_score_static #(.TP(TP)) scorer(.clk_ctl(clk_score[q]),.clk_engine(clk_engine[q*4+:4]),.clk_meta(clk_meta[q*4+:4]),
   .clk_tail(clk_tail[q*4+:4]),.clk_chunk(clk_chunk[q*16+:16]),.clk_hslice(clk_hslice[q*512+:512]),.rst_n(rst_n),
   .rank(rank),.first_ord(11'(q*342)),.nkeys(nq[q*12+:12]),.keep_en(keep_en),.keep_bitmap(keep_bitmap[q*342+:342]),
   .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.beat_v(key_slot_w),.beat_index(key_index_w),
   .key_lines(key_lines[q*8792+:8792]),.score(score_all[q*610+:610]),.fault(scf[q]));
 end
 wire[3:0]unused_ov;wire[2367:0]unused_ol;wire[15:0]threshold;wire[55:0]selected_count;
 ot_hbm_idx_selector_static selector(.clk_ctl(clk_sel),.clk_q(clk_sel_q),.clk_mem(clk_sel_mem),.rst_n(rst_n),.op(sel_op),.pass(sel_pass),
  .addr(sel_addr),.k(10'd512),.in_line(sel_in),.out_v(unused_ov),.out_line(unused_ol),.selected_v(selected_v),.selected_line(selected_line),
  .threshold_observe(threshold),.selected_observe(selected_count),.fault(sf));
 wire[9:0]total;
`ifdef OT_IDX_DENSE_LINK
 ot_hbm_idx_topk_link_static_dense link(.clk(clk_link),
`else
 ot_hbm_idx_topk_link_static link(.clk(clk_link),
`endif
  .clk_mem(clk_link_mem),.rst_n(rst_n),.clear(start),.ingest_v(ingest_v),
  .selected_line(selected_line),.flush(link_flush),.emit_v(link_emit),.emit_group(link_group),.rank(8'(rank)),.gbase(gbase),
  .tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(total));
endmodule
`default_nettype wire
