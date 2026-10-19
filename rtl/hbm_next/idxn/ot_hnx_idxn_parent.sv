`default_nettype none
// HBM-NEXT-UNITS-IDXN 2026-10-19: N-row IDX.INDEX parent, ONE key stream, rows pipelined at the row II.
// Successor of rtl/hbm_next/idx/ot_hnx_idx_parent_static (which re-read the keys and ran the whole top-512 selection
// per row: II 953). Units and what changed:
//   operands  ot_hnx_idx_vm_query_static (row-strided query / weight bases)            shared, rows in sequence
//   query     ot_hbm_idx_query_static (d4g, UNCHANGED; seen bits clear per row)        shared, rows in sequence
//   scorers   N_Q x ot_hbm_idx_score_static (d4g, UNCHANGED, one query held in the hslices) fed by
//             N_Q x ot_hnx_idxn_keybuf: row 0 = live HBM key lines (captured), rows >= 1 = replay  shared
//   selectors S x ot_hbm_idx_selector_static (d4g, UNCHANGED): row r -> selector r mod S (time-shared: S = 4 covers
//             N = 4 and 6); every selector sees the one score bus, ingests only on its own op 2 slots
//   link      ot_hnx_idxn_link (8 row slots in the existing banks; slot = row mod 8)  shared
// All fields come from ot_hnx_idxn_calendar's per-class routing (collision = fault). No ready/credit anywhere.
// Named wires kb_pre_v / kb_pre_index, link_in_slot / link_out_slot exist so the bench can force the mutants.
module ot_hnx_idxn_parent #(parameter integer N_Q=4,TP=96,S=4,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[N_Q-1:0]clk_score,input wire[4*N_Q-1:0]clk_engine,clk_meta,clk_tail,
 input wire[16*N_Q-1:0]clk_chunk,input wire[512*N_Q-1:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire rst_n,
 input wire[1:0]sid,input wire frame_start,row_start,
 input wire weight_slot,query_slot,input wire[6:0]query_index,input wire[15:0]weight_sector,query_sector,
 input wire[15:0]weight_row_stride,query_row_stride,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire query_emit,input wire[4:0]query_emit_head,
 input wire[RANK_W-1:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[342*N_Q-1:0]keep_bitmap,
 input wire key_v,input wire[7:0]key_index,input wire[4:0]key_row,input wire pre_v,input wire[7:0]pre_index,
 input wire[8792*N_Q-1:0]key_lines,
 input wire[4*S-1:0]sel_op,input wire[2*S-1:0]sel_pass,input wire[8*S-1:0]sel_addr,
 input wire lin_clear,lin_flush,input wire[4:0]lin_row,input wire lout_emit,input wire[3:0]lout_group,input wire[4:0]lout_row,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[610*N_Q-1:0]score_observe,output wire fault
);
 wire bv;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]bw;wire vf,qf,lf;wire[N_Q-1:0]scf,kbf;wire[S-1:0]sf;
 ot_hnx_idx_vm_query_static operands(.clk(clk_operand),.rst_n(rst_n),.sid(sid),.frame_start(frame_start),.weight_slot(weight_slot),.query_slot(query_slot),
 .query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.weight_row_stride(weight_row_stride),.query_row_stride(query_row_stride),.vm_rq(vm_rq),.vm_rr(vm_rr),
 .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),.fault(vf));
 wire qv;wire[7:0]qh;wire[511:0]qc;wire[31:0]qs;wire[15:0]qw;
 ot_hbm_idx_query_static query(.clk(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_query_bank),
 .rst_n(rst_n),.frame_start(row_start),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
 .emit_v(query_emit),.emit_head(query_emit_head),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.fault(qf));
 // key stream: live (row 0) vs replay (rows >= 1)
 wire live_v=key_v&&key_row==5'd0,replay_v=key_v&&key_row!=5'd0;
 wire kb_pre_v=pre_v;wire[7:0]kb_pre_index=pre_index;
 wire[2367:0]sel_in;
 if(N_Q<4)begin:gabsent
  assign sel_in[2367:N_Q*592]='0;
 end
 for(genvar q=0;q<N_Q;q=q+1)begin:gscore
  wire[11:0]nq=(nkeys<=q*2736)?12'd0:((nkeys-q*2736>=2736)?12'd2736:12'(nkeys-q*2736));
  wire[609:0]score;wire[8791:0]klines;
  ot_hnx_idxn_keybuf kb(.clk(clk_score[q]),.rst_n(rst_n),.clear(frame_start),.live_v(live_v),.live_index(key_index),
   .key_in(key_lines[q*8792+:8792]),.pre_v(kb_pre_v),.pre_index(kb_pre_index),.replay_v(replay_v),.replay_index(key_index),
   .key_out(klines),.fault(kbf[q]));
  ot_hbm_idx_score_static #(.TP(TP)) scorer(.clk_ctl(clk_score[q]),.clk_engine(clk_engine[q*4+:4]),.clk_meta(clk_meta[q*4+:4]),
   .clk_tail(clk_tail[q*4+:4]),.clk_chunk(clk_chunk[q*16+:16]),.clk_hslice(clk_hslice[q*512+:512]),.rst_n(rst_n),
   .rank(rank),.first_ord(11'(q*342)),.nkeys(nq),.keep_en(keep_en),.keep_bitmap(keep_bitmap[q*342+:342]),
   .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.beat_v(key_v),.beat_index(key_index),
   .key_lines(klines),.score(score),.fault(scf[q]));
  assign score_observe[q*610+:610]=score;
  for(genvar l=0;l<16;l=l+1)begin:lane
   assign sel_in[q*592+l*37+:37]={score[290+l*20+:20],score[34+l*16+:16],score[18+l]};
  end
 end
 // S time-shared selectors on the one score bus
 wire[4*S-1:0]sv;wire[2368*S-1:0]sl;
 for(genvar s=0;s<S;s=s+1)begin:gsel
  wire[3:0]unused_ov;wire[2367:0]unused_ol;wire[15:0]threshold;wire[55:0]selected_count;
  ot_hbm_idx_selector_static selector(.clk_ctl(clk_sel),.clk_q(clk_sel_q),.clk_mem(clk_sel_mem),.rst_n(rst_n),.op(sel_op[s*4+:4]),
   .pass(sel_pass[s*2+:2]),.addr(sel_addr[s*8+:8]),.k(10'd512),.in_line(sel_in),.out_v(unused_ov),.out_line(unused_ol),
   .selected_v(sv[s*4+:4]),.selected_line(sl[s*2368+:2368]),.threshold_observe(threshold),.selected_observe(selected_count),.fault(sf[s]));
 end
 reg[2367:0]link_line;reg link_ingest;reg sel_coll;integer nsel;
 always @*begin
  link_line=0;link_ingest=0;nsel=0;
  for(integer s=0;s<S;s=s+1)if(|sv[s*4+:4])begin
   nsel=nsel+1;link_line=link_line|sl[s*2368+:2368];link_ingest=link_ingest|(&sv[s*4+:4]);
  end
  sel_coll=nsel>1;
 end
 wire[2:0]link_in_slot=lin_row[2:0],link_out_slot=lout_row[2:0];
 wire[9:0]total;
 ot_hnx_idxn_link link(.clk(clk_link),.clk_mem(clk_link_mem),.rst_n(rst_n),.clear(frame_start),.row_clear(lin_clear),.in_slot(link_in_slot),
  .ingest_v(link_ingest),.selected_line(link_line),.flush(lin_flush),.emit_v(lout_emit),.emit_group(lout_group),.emit_slot(link_out_slot),
  .rank(8'(rank)),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(total));
 reg calendar_fault;
 always @(posedge clk_sel or negedge rst_n)begin
  if(!rst_n)calendar_fault<=0;
  else begin
   for(integer s=0;s<S;s=s+1)if(sel_op[s*4+:4]==4'd2&&score_observe[0]!=1'b1)calendar_fault<=1;
   if(sel_coll)calendar_fault<=1;                      // two selectors delivering to the link on one edge
  end
 end
 assign fault=vf|qf|(|scf)|(|kbf)|(|sf)|lf|calendar_fault;
endmodule
`default_nettype wire
