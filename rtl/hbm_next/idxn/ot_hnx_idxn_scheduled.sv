`default_nettype none
// HBM-NEXT-UNITS-IDXN 2026-10-19: N-row IDX.INDEX client with ONE key stream (successor of
// rtl/hbm_next/idx/ot_hnx_idx_scheduled_static). Issuer ot_hnx_idxn_calendar (K pipelined row streams over one frame,
// per-class routing, collision = fault) + ot_hnx_idxn_parent (key replay buffers, S time-shared selectors, row-slot
// link). key_slot / key_index (the HBM key-line service request) are asserted for row 0 ONLY: the service delivers
// every key line once per record; rows 1..N-1 replay them on die. n_rows / row_pitch / the two operand row strides
// come from the record's ROWX (N = nm1 + 1; pitch = the compiled row II + rgap).
module ot_hnx_idxn_scheduled #(parameter integer N_Q=4,TP=96,S=4,K=8,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_program,clk_program_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]row_pitch,
 input wire[15:0]weight_row_stride,query_row_stride,
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[N_Q-1:0]clk_score,input wire[4*N_Q-1:0]clk_engine,clk_meta,clk_tail,
 input wire[16*N_Q-1:0]clk_chunk,input wire[512*N_Q-1:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire rst_n,
 input wire[1:0]sid,input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire[RANK_W-1:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[342*N_Q-1:0]keep_bitmap,
 output wire key_slot,output wire[7:0]key_index,input wire[8792*N_Q-1:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[610*N_Q-1:0]score_observe,output wire done,fault
);
 wire calendar_fault,parent_fault,row_start;
 wire ow,oq,qe,kv,pv,lc,lf,le;wire[6:0]oi;wire[4:0]qh,kr,lr,er;wire[7:0]ki,pi;wire[3:0]eg;
 wire[4*S-1:0]sop;wire[2*S-1:0]sps;wire[8*S-1:0]sad;
 ot_hnx_idxn_calendar #(.K(K),.S(S)) calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_n),
  .program_we(program_we),.program_addr(program_addr),.program_data(program_data),.start(start),.length(length),
  .n_rows(n_rows),.pitch(row_pitch),.row_start(row_start),.opr_weight(ow),.opr_query(oq),.opr_index(oi),.qem_v(qe),.qem_head(qh),
  .key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.sel_op(sop),.sel_pass(sps),.sel_addr(sad),
  .lin_clear(lc),.lin_flush(lf),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),.done(done),.fault(calendar_fault));
 assign key_slot=kv&&kr==5'd0;assign key_index=ki;
 ot_hnx_idxn_parent #(.N_Q(N_Q),.TP(TP),.S(S)) parent(.clk_operand(clk_operand),.clk_query(clk_query),.clk_quant(clk_quant),
  .clk_quant_delay(clk_quant_delay),.clk_query_bank(clk_query_bank),.clk_score(clk_score),.clk_engine(clk_engine),.clk_meta(clk_meta),
  .clk_tail(clk_tail),.clk_chunk(clk_chunk),.clk_hslice(clk_hslice),.clk_sel(clk_sel),.clk_sel_q(clk_sel_q),.clk_sel_mem(clk_sel_mem),
  .clk_link(clk_link),.clk_link_mem(clk_link_mem),.rst_n(rst_n),.sid(sid),.frame_start(start),.row_start(row_start),
  .weight_slot(ow),.query_slot(oq),.query_index(oi),.weight_sector(weight_sector),.query_sector(query_sector),
  .weight_row_stride(weight_row_stride),.query_row_stride(query_row_stride),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .query_emit(qe),.query_emit_head(qh),.rank(rank),.gbase(gbase),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),
  .key_v(kv),.key_index(ki),.key_row(kr),.pre_v(pv),.pre_index(pi),.key_lines(key_lines),
  .sel_op(sop),.sel_pass(sps),.sel_addr(sad),.lin_clear(lc),.lin_flush(lf),.lin_row(lr),.lout_emit(le),.lout_group(eg),.lout_row(er),
  .tx_v(tx_v),.tx(tx),.score_observe(score_observe),.fault(parent_fault));
 assign fault=calendar_fault|parent_fault;
endmodule
`default_nettype wire
