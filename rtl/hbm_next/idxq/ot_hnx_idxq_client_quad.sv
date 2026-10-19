`default_nettype none
// HBM-NEXT-UNITS IDXQ 2026-10-19: IDXN (N query rows over ONE key stream) ported into the d4g per-quadrant IDX client
// (fork of rtl/hbm_accel/index/quad_1017/ot_hbm_idx_client_static_quad). SOFT composition (wires and constants only;
// every instance is a die-level instance hb_idx__<name>):
//   per quadrant q (0..3, die straps S = stack of its KV ordinals, H = half = its 4 PCs of that stack):
//     idx_ctl<q>  ot_hnx_idxq_qctl                 IDXN calendar copy: OPR / QEM / KEY (+row) / PRE / row_start
//     idx_op<q>   ot_hnx_idx_vm_query_static       operand reader with the HGI-1R row strides (q0: via the SW share)
//     idx_q<q>    ot_hbm_idx_query_static          d4g query unit (seen bits clear per row)
//     idx_kb<q>   ot_hnx_idxn_keybuf NP=4 (strap pbase 4H) key replay buffer of the quarter's 4 PC key lines (17 macros):
//                                                  row 0 scores (and captures) the live lines, rows >= 1 replay them
//     idx_s<q>    ot_hbm_idx_score_quarter_static  d4g quarter scorer, UNCHANGED (beats of every row)
//   cross-quadrant registered tree idx_xq<s> / idx_xqr (d4g, unchanged), then
//     idx_sel<j>  S x ot_hbm_idx_selector_static (d4g, unchanged): row r -> selector r mod S, all on the tree root bus
//     idx_link    ot_hnx_idxq_link (selector merge + IDXN row-slot link)
//     idx_ctl     ot_hnx_idxq_rootctl (root calendar copy: SEL per selector / LIN / LOUT, done, TOPK, SW share)
// The HBM key-line service is asked ONCE per record: key_slot[q] = row-0 key beats only.
// Equivalent (lockstep, rtl/hbm_next/idxq/tb/tb_hnx_idxq_lockstep.sv) to ot_hnx_idxn_scheduled N_Q=2 TP=192
// (OT_IDX_SCORE_CLUSTER) for N = 1..6 rows: same scores / selected records / TX flits; timeline as the d4g quad
// (key beats +2, scores +4, TX +2 + 6, done +2; programme --score-chain 14 instead of 8).
module ot_hnx_idxq_client_quad #(parameter integer TP=96,K=8,RANK_W=(TP<=1?1:$clog2(TP)),
 parameter [3:0] QS=4'b1100,     // stack (KV ordinal slot) of quadrant q
 parameter [3:0] QH=4'b1010)(    // half (PCs 4H..4H+3 of that stack) of quadrant q
 input wire clk_program,clk_program_mem,input wire[3:0]clk_qprog,clk_qprog_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]row_pitch,
 input wire[15:0]weight_row_stride,query_row_stride,
 input wire[3:0]clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[15:0]clk_query_bank,
 input wire[3:0]clk_kb,clk_score,input wire[7:0]clk_engine,clk_meta,clk_tail,
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
 localparam integer S=4;                 // time-shared selectors (the link tile takes 2 on its W face, 2 on its E face)
 wire[135:0]index_rq;wire[2055:0]index_rr;
 wire[3:0]qfault;wire[4*297-1:0]list;
 for(genvar q=0;q<4;q=q+1)begin:gq
  localparam integer SQ=QS[q],H=QH[q];
  wire ws,qs,qe,fs,rs,kv,pv,vf,qf,scf,kbf;wire[6:0]qi;wire[4:0]qeh,kr;wire[7:0]ki,pi;wire[11:0]nq;
  ot_hnx_idxq_qctl #(.K(K),.S(S)) ctl(.clk_program(clk_qprog[q]),.clk_program_mem(clk_qprog_mem[q]),.rst_n(rst_n),.slot(1'(SQ)),
   .program_we(program_we),.program_addr(program_addr),.program_data(program_data),.start(start),.length(length),
   .n_rows(n_rows),.row_pitch(row_pitch),.nkeys(nkeys),
   .weight_slot(ws),.query_slot(qs),.query_index(qi),.query_emit(qe),.query_emit_head(qeh),
   .key_slot(key_slot[q]),.key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),
   .nq(nq),.frame_start(fs),.row_start(rs),.vf(vf),.qf(qf),.scf(scf),.kbf(kbf),.fault(qfault[q]));
  assign key_index[q*8+:8]=ki;
  wire[135:0]rq;wire[2055:0]rr;
  if(q==0)begin:gsw assign index_rq=rq;assign rr=index_rr;end
  else begin:gown assign vm_rq_q[(q-1)*136+:136]=rq;assign rr=vm_rr_q[(q-1)*2056+:2056];end
  wire bv;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]bw;
  ot_hnx_idx_vm_query_static operands(.clk(clk_operand[q]),.rst_n(rst_n),.sid(2'd0),.frame_start(fs),.weight_slot(ws),.query_slot(qs),
   .query_index(qi),.weight_sector(weight_sector),.query_sector(query_sector),.weight_row_stride(weight_row_stride),
   .query_row_stride(query_row_stride),.vm_rq(rq),.vm_rr(rr),
   .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),.fault(vf));
  wire qv;wire[7:0]qh;wire[511:0]qc;wire[31:0]qsc;wire[15:0]qw;
  ot_hbm_idx_query_static query(.clk(clk_query[q]),.clk_quant(clk_quant[q]),.clk_quant_delay(clk_quant_delay[q]),.clk_bank(clk_query_bank[q*4+:4]),
   .rst_n(rst_n),.frame_start(rs),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
   .emit_v(qe),.emit_head(qeh),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qsc),.ql_w(qw),.fault(qf));
  // key stream: row 0 = the live service lines (captured), rows >= 1 = replay (named wires: bench mutants)
  wire live_v=kv&&kr==5'd0,replay_v=kv&&kr!=5'd0;
  wire[4395:0]klines;
  ot_hnx_idxn_keybuf #(.NP(4),.RS(1)) kbuf(.clk(clk_kb[q]),.rst_n(rst_n),.clear(fs),.pbase(3'(4*H)),.live_v(live_v),.live_index(ki),
   .key_in(key_lines[SQ*8792+H*4396+:4396]),.pre_v(pv),.pre_index(pi),.replay_v(replay_v),.replay_index(ki),
   .key_out(klines),.fault(kbf));
  wire[170:0]kb;
  for(genvar a=0;a<171;a=a+1)begin:gkb assign kb[a]=keep_bitmap[SQ*342+2*a+H];end
  wire[305:0]sc;
  ot_hbm_idx_score_quarter_static #(.TP(TP)) scorer(.clk_ctl(clk_score[q]),.clk_engine(clk_engine[q*2+:2]),.clk_meta(clk_meta[q*2+:2]),
   .clk_tail(clk_tail[q*2+:2]),.clk_chunk(clk_chunk[q*8+:8]),.clk_hslice(clk_hslice[q*256+:256]),.rst_n(rst_n),.half(1'(H)),
   .rank(rank),.first_ord(11'(SQ*342)),.nkeys(nq),.keep_en(keep_en),.keep_bitmap(kb),
   .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qsc),.ql_w(qw),.beat_v(kv),.beat_index(ki),
   .key_lines(klines),.score(sc),.fault(scf));
  assign score_observe[q*306+:306]=sc;
  for(genvar l=0;l<8;l=l+1)begin:gl assign list[q*297+l*37+:37]={sc[146+l*20+:20],sc[18+l*16+:16],sc[10+l]};end
  assign list[q*297+296]=sc[0];
 end
 // ---------------- registered cross-quadrant tree (d4g): stack nodes, then the root node
 wire[2*594-1:0]stk;wire[1187:0]root;
 for(genvar s=0;s<2;s=s+1)begin:gs
  localparam integer QA=(QS[0]==s&&QH[0]==0)?0:(QS[1]==s&&QH[1]==0)?1:(QS[2]==s&&QH[2]==0)?2:3;
  localparam integer QB=(QS[0]==s&&QH[0]==1)?0:(QS[1]==s&&QH[1]==1)?1:(QS[2]==s&&QH[2]==1)?2:3;
  ot_hbm_idx_xq_node_static #(.WI(297)) node(.clk(clk_xq[s]),.rst_n(rst_n),.a(list[QA*297+:297]),.b(list[QB*297+:297]),.y(stk[s*594+:594]));
 end
 ot_hbm_idx_xq_node_static #(.WI(594)) rootn(.clk(clk_xq[2]),.rst_n(rst_n),.a(stk[0+:594]),.b(stk[594+:594]),.y(root));
 wire[2367:0]sel_in;wire[3:0]tree_ev;
 assign sel_in[2367:1184]='0;
 for(genvar s=0;s<2;s=s+1)begin:gin
  assign sel_in[s*592+:296]=root[s*594+:296];
  assign sel_in[s*592+296+:296]=root[s*594+297+:296];
  assign tree_ev[2*s]=root[s*594+296];assign tree_ev[2*s+1]=root[s*594+297+296];
 end
 wire[4*S-1:0]sel_op;wire[2*S-1:0]sel_pass;wire[8*S-1:0]sel_addr;wire lin_clear,lin_flush,lout_emit,link_clear,lf;
 wire[4:0]lin_row,lout_row;wire[3:0]lout_group;wire[S-1:0]sf;
 ot_hnx_idxq_rootctl #(.K(K),.S(S)) ctl(.clk_program(clk_program),.clk_program_mem(clk_program_mem),.clk_sel(clk_sel),.clk_topk(clk_topk),
  .clk_pair(clk_pair),.rst_n(rst_n),.program_we(program_we),.program_addr(program_addr),.program_data(program_data),
  .start(start),.length(length),.n_rows(n_rows),.row_pitch(row_pitch),.sel_op(sel_op),.sel_pass(sel_pass),.sel_addr(sel_addr),
  .lin_clear(lin_clear),.lin_flush(lin_flush),.lin_row(lin_row),.lout_emit(lout_emit),.lout_group(lout_group),.lout_row(lout_row),
  .link_clear(link_clear),.tree_ev(tree_ev),.qfault(qfault),.sf(sf),.lf(lf),.done(done),.fault(fault),
  .topk_go(topk_go),.topk_k(topk_k),.topk_order(topk_order),.topk_n(topk_n),.topk_m(topk_m),
  .topk_a_mirror(topk_a_mirror),.topk_a_base(topk_a_base),.topk_a_str(topk_a_str),.topk_o_mirror(topk_o_mirror),
  .topk_o_base(topk_o_base),.topk_o_str(topk_o_str),.topk_has_r(topk_has_r),.topk_r_base(topk_r_base),.topk_r_str(topk_r_str),
  .cq(cq),.cq_seq(cq_seq),.cr(cr),.topk_busy(topk_busy),.topk_done(topk_done),.topk_fault(topk_fault),
  .index_rq(index_rq),.index_rr(index_rr),.argmax_rq(argmax_rq),.argmax_rr(argmax_rr),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .share_fault(share_fault));
 // ---------------- S time-shared selectors on the tree root bus (d4g master, unchanged)
 wire[4*S-1:0]sv;wire[2368*S-1:0]sl;
 for(genvar j=0;j<S;j=j+1)begin:gsel
  wire[3:0]unused_ov;wire[2367:0]unused_ol;wire[15:0]threshold;wire[55:0]selected_count;
  ot_hbm_idx_selector_static selector(.clk_ctl(clk_sel),.clk_q(clk_sel_q),.clk_mem(clk_sel_mem),.rst_n(rst_n),.op(sel_op[j*4+:4]),
   .pass(sel_pass[j*2+:2]),.addr(sel_addr[j*8+:8]),.k(10'd512),.in_line(sel_in),.out_v(unused_ov),.out_line(unused_ol),
   .selected_v(sv[j*4+:4]),.selected_line(sl[j*2368+:2368]),.threshold_observe(threshold),.selected_observe(selected_count),.fault(sf[j]));
 end
 wire[2:0]link_in_slot=lin_row[2:0],link_out_slot=lout_row[2:0];   // named wires (bench mutant: slots dropped)
 wire[9:0]total;
 ot_hnx_idxq_link link(.clk(clk_link),.clk_mem(clk_link_mem),.rst_n(rst_n),.clear(link_clear),.row_clear(lin_clear),
  .in_slot(link_in_slot),.sel_v_w(sv[0+:8]),.sel_line_w(sl[0+:2*2368]),.sel_v_e(sv[8+:8]),.sel_line_e(sl[2*2368+:2*2368]),.flush(lin_flush),.emit_v(lout_emit),.emit_group(lout_group),
  .emit_slot(link_out_slot),.rank(8'(rank)),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(total));
endmodule
`default_nettype wire
