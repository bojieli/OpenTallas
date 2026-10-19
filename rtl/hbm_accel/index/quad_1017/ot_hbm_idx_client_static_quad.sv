`default_nettype none
// HBM d4g plan (b) IDX client, PER-QUADRANT form (lane HBM-B-RTL2, 2026-10-17). SOFT composition (wires and
// constants only; every instance is a die-level instance hb_idx__<name>):
//   per quadrant q (0..3, die straps S = stack of its KV ordinals, H = half = its 4 PCs of that stack):
//     idx_ctl<q>  ot_hbm_idx_qctl_static          local calendar copy + operand/query/key-beat fields + fault OR
//     idx_op<q>   ot_hbm_idx_vm_query_static      operand reader on the quadrant's OWN VM (q0: via the SW share)
//     idx_q<q>    ot_hbm_idx_query_static         local query unit (the compiler replicates the index query block
//                                                 and the head weights into all 4 quadrant VMs, same sectors)
//     idx_s<q>    ot_hbm_idx_score_quarter_static 2 engines / 8 key lanes on the quadrant's 4 PC key lines
//   cross-quadrant (fat XQ lanes, registered tree): idx_xq<s> (per stack, joins its 2 quarter lists) and
//     idx_xqr (root) = ot_hbm_idx_xq_node_static, 2 edges each; then the unchanged idx_sel / idx_link and
//     idx_ctl = ot_hbm_idx_rootctl_static (root calendar copy: selector/link fields, TOPK, SW share).
// Equivalent (lockstep, rtl/test/hbm_idx_static/run_quad_lockstep.sh) to ot_hbm_idx_scheduled_static N_Q=2 (OT_IDX_SCORE_CLUSTER) with
// the same key ordinals, scores, selected records and TX flits; timeline: +2 edges (start/issue pins) on every
// event and +6 edges between the scorers and the selector (quarter pins 2 + XQ tree 4): calendar --score-chain 14
// (= the 16-leaf cluster's 8 + 6) instead of 8.
// Only the quarter lists (8 x 37 b + ev = 297 b per quadrant; faults ride a 1-b OR line) and the start/programme broadcast cross quadrants.
module ot_hbm_idx_client_static_quad #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)),
 parameter [3:0] QS=4'b1100,     // stack (KV ordinal slot) of quadrant q
 parameter [3:0] QH=4'b1010)(    // half (PCs 4H..4H+3 of that stack) of quadrant q
 input wire clk_program,clk_program_mem,input wire[3:0]clk_qprog,clk_qprog_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire[3:0]clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[15:0]clk_query_bank,
 input wire[3:0]clk_score,input wire[7:0]clk_engine,clk_meta,clk_tail,
 input wire[31:0]clk_chunk,input wire[1023:0]clk_hslice,input wire[2:0]clk_xq,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire[3:0]clk_pair,input wire clk_topk,input wire rst_n,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,                 // SW read group (quadrant 0 index + TOPK + ARGMAX)
 output wire[3*136-1:0]vm_rq_q,input wire[3*2056-1:0]vm_rr_q,      // quadrants 1..3 index read groups (own VM)
 input wire[RANK_W-1:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[2*342-1:0]keep_bitmap,
 output wire[3:0]key_slot,output wire[31:0]key_index,input wire[2*8792-1:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[4*306-1:0]score_observe,output wire done,fault,
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,output wire share_fault,
 input wire[135:0]argmax_rq,output wire[2055:0]argmax_rr
);
 wire[135:0]index_rq;wire[2055:0]index_rr;
 wire[3:0]qfault;wire[4*297-1:0]list;
 for(genvar q=0;q<4;q=q+1)begin:gq
  localparam integer S=QS[q],H=QH[q];
  wire ws,qs,qe,fs,vf,qf,scf;wire[6:0]qi;wire[4:0]qeh;wire[11:0]nq;
  ot_hbm_idx_qctl_static ctl(.clk_program(clk_qprog[q]),.clk_program_mem(clk_qprog_mem[q]),.rst_n(rst_n),.slot(1'(S)),
   .program_we(program_we),.program_addr(program_addr),.program_data(program_data),.start(start),.length(length),.nkeys(nkeys),
   .weight_slot(ws),.query_slot(qs),.query_index(qi),.query_emit(qe),.query_emit_head(qeh),
   .key_slot(key_slot[q]),.key_index(key_index[q*8+:8]),.nq(nq),.frame_start(fs),.vf(vf),.qf(qf),.scf(scf),.fault(qfault[q]));
  wire[135:0]rq;wire[2055:0]rr;
  if(q==0)begin:gsw assign index_rq=rq;assign rr=index_rr;end
  else begin:gown assign vm_rq_q[(q-1)*136+:136]=rq;assign rr=vm_rr_q[(q-1)*2056+:2056];end
  wire bv;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]bw;
  ot_hbm_idx_vm_query_static operands(.clk(clk_operand[q]),.rst_n(rst_n),.sid(2'd0),.weight_slot(ws),.query_slot(qs),
   .query_index(qi),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(rq),.vm_rr(rr),
   .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),.fault(vf));
  wire qv;wire[7:0]qh;wire[511:0]qc;wire[31:0]qsc;wire[15:0]qw;
  ot_hbm_idx_query_static query(.clk(clk_query[q]),.clk_quant(clk_quant[q]),.clk_quant_delay(clk_quant_delay[q]),.clk_bank(clk_query_bank[q*4+:4]),
   .rst_n(rst_n),.frame_start(fs),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
   .emit_v(qe),.emit_head(qeh),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qsc),.ql_w(qw),.fault(qf));
  wire[170:0]kb;
  for(genvar a=0;a<171;a=a+1)begin:gkb assign kb[a]=keep_bitmap[S*342+2*a+H];end
  wire[305:0]sc;
  ot_hbm_idx_score_quarter_static #(.TP(TP)) scorer(.clk_ctl(clk_score[q]),.clk_engine(clk_engine[q*2+:2]),.clk_meta(clk_meta[q*2+:2]),
   .clk_tail(clk_tail[q*2+:2]),.clk_chunk(clk_chunk[q*8+:8]),.clk_hslice(clk_hslice[q*256+:256]),.rst_n(rst_n),.half(1'(H)),
   .rank(rank),.first_ord(11'(S*342)),.nkeys(nq),.keep_en(keep_en),.keep_bitmap(kb),
   .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qsc),.ql_w(qw),.beat_v(key_slot[q]),.beat_index(key_index[q*8+:8]),
   .key_lines(key_lines[S*8792+H*4396+:4396]),.score(sc),.fault(scf));
  assign score_observe[q*306+:306]=sc;
  // quarter list {ev, lane l = {idx, val, kv}}; lane l of quarter (S,H) = stack lane 8H + l
  for(genvar l=0;l<8;l=l+1)begin:gl assign list[q*297+l*37+:37]={sc[146+l*20+:20],sc[18+l*16+:16],sc[10+l]};end
  assign list[q*297+296]=sc[0];
 end
 // ---------------- registered cross-quadrant tree: stack nodes, then the root node
 wire[2*594-1:0]stk;wire[1187:0]root;
 for(genvar s=0;s<2;s=s+1)begin:gs
  localparam integer QA=(QS[0]==s&&QH[0]==0)?0:(QS[1]==s&&QH[1]==0)?1:(QS[2]==s&&QH[2]==0)?2:3;   // half 0 of stack s
  localparam integer QB=(QS[0]==s&&QH[0]==1)?0:(QS[1]==s&&QH[1]==1)?1:(QS[2]==s&&QH[2]==1)?2:3;   // half 1 of stack s
  ot_hbm_idx_xq_node_static #(.WI(297)) node(.clk(clk_xq[s]),.rst_n(rst_n),.a(list[QA*297+:297]),.b(list[QB*297+:297]),.y(stk[s*594+:594]));
 end
 ot_hbm_idx_xq_node_static #(.WI(594)) rootn(.clk(clk_xq[2]),.rst_n(rst_n),.a(stk[0+:594]),.b(stk[594+:594]),.y(root));
 // selector in_line: group s lanes 0..7 = half 0, 8..15 = half 1 (the stack scorer's lane order); groups 2, 3 absent
 wire[2367:0]sel_in;wire[3:0]tree_ev;
 assign sel_in[2367:1184]='0;
 for(genvar s=0;s<2;s=s+1)begin:gin
  assign sel_in[s*592+:296]=root[s*594+:296];
  assign sel_in[s*592+296+:296]=root[s*594+297+:296];
  assign tree_ev[2*s]=root[s*594+296];assign tree_ev[2*s+1]=root[s*594+297+296];
 end
 wire[3:0]sel_op,link_group;wire[1:0]sel_pass;wire[7:0]sel_addr;wire link_flush,link_emit,link_clear,ingest_v,sf,lf;
 wire[3:0]selected_v;wire[2367:0]selected_line;
 ot_hbm_idx_rootctl_static ctl(.clk_program(clk_program),.clk_program_mem(clk_program_mem),.clk_sel(clk_sel),.clk_topk(clk_topk),
  .clk_pair(clk_pair),.rst_n(rst_n),.program_we(program_we),.program_addr(program_addr),.program_data(program_data),
  .start(start),.length(length),.sel_op(sel_op),.sel_pass(sel_pass),.sel_addr(sel_addr),.link_flush(link_flush),.link_emit(link_emit),
  .link_group(link_group),.link_clear(link_clear),.selected_v(selected_v),.ingest_v(ingest_v),.tree_ev(tree_ev),
  .qfault(qfault),.sf(sf),.lf(lf),.done(done),.fault(fault),
  .topk_go(topk_go),.topk_k(topk_k),.topk_order(topk_order),.topk_n(topk_n),.topk_m(topk_m),
  .topk_a_mirror(topk_a_mirror),.topk_a_base(topk_a_base),.topk_a_str(topk_a_str),.topk_o_mirror(topk_o_mirror),
  .topk_o_base(topk_o_base),.topk_o_str(topk_o_str),.topk_has_r(topk_has_r),.topk_r_base(topk_r_base),.topk_r_str(topk_r_str),
  .cq(cq),.cq_seq(cq_seq),.cr(cr),.topk_busy(topk_busy),.topk_done(topk_done),.topk_fault(topk_fault),
  .index_rq(index_rq),.index_rr(index_rr),.argmax_rq(argmax_rq),.argmax_rr(argmax_rr),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .share_fault(share_fault));
 wire[3:0]unused_ov;wire[2367:0]unused_ol;wire[15:0]threshold;wire[55:0]selected_count;
 ot_hbm_idx_selector_static selector(.clk_ctl(clk_sel),.clk_q(clk_sel_q),.clk_mem(clk_sel_mem),.rst_n(rst_n),.op(sel_op),.pass(sel_pass),
  .addr(sel_addr),.k(10'd512),.in_line(sel_in),.out_v(unused_ov),.out_line(unused_ol),.selected_v(selected_v),.selected_line(selected_line),
  .threshold_observe(threshold),.selected_observe(selected_count),.fault(sf));
 wire[9:0]total;
 ot_hbm_idx_topk_link_static link(.clk(clk_link),.clk_mem(clk_link_mem),.rst_n(rst_n),.clear(link_clear),.ingest_v(ingest_v),
  .selected_line(selected_line),.flush(link_flush),.emit_v(link_emit),.emit_group(link_group),.rank(8'(rank)),.gbase(gbase),
  .tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(total));
endmodule
`default_nettype wire
