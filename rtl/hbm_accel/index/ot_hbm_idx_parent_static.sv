`default_nettype none
// Full arithmetic/operand composition successor. Explicit compiler schedules
// every query load/head emit, key beat, radix pass and collective emission.
// Service supplies actual staged key_lines; its upstream PHY/staging join must
// be bound separately. No credit or ready input exists in this parent.
module ot_hbm_idx_parent_static(
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[3:0]clk_score,input wire[15:0]clk_engine,clk_meta,clk_tail,
 input wire[63:0]clk_chunk,input wire[2047:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire rst_n,
 input wire[1:0]sid,input wire frame_start,
 input wire weight_slot,query_slot,input wire[6:0]query_index,input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire query_emit,input wire[4:0]query_emit_head,
 input wire[6:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[1367:0]keep_bitmap,
 input wire beat_v,input wire[7:0]beat_index,input wire[35167:0]key_lines,
 input wire[3:0]sel_op,input wire[1:0]sel_pass,input wire[7:0]sel_addr,
 input wire link_flush,link_emit,input wire[3:0]link_group,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[2439:0]score_observe,output wire fault
);
 wire bv;wire[4:0]bh;wire[1:0]bn;wire[1023:0]bd;wire[15:0]bw;wire vf,qf,lf,sf;wire[3:0]scf;
 ot_hbm_idx_vm_query_static operands(.clk(clk_operand),.rst_n(rst_n),.sid(sid),.weight_slot(weight_slot),.query_slot(query_slot),
 .query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),
 .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),.fault(vf));
 wire qv;wire[7:0]qh;wire[511:0]qc;wire[31:0]qs;wire[15:0]qw;
 ot_hbm_idx_query_static query(.clk(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_query_bank),
 .rst_n(rst_n),.frame_start(frame_start),.block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(bw),
 .emit_v(query_emit),.emit_head(query_emit_head),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.fault(qf));
 wire[2367:0]sel_in;wire[3:0]selected_v;wire[2367:0]selected_line;
 for(genvar q=0;q<4;q=q+1)begin:gscore
  wire[11:0]nq=(nkeys<=q*2736)?12'd0:((nkeys-q*2736>=2736)?12'd2736:12'(nkeys-q*2736));
  wire[609:0]score;
  ot_hbm_idx_score_static scorer(.clk_ctl(clk_score[q]),.clk_engine(clk_engine[q*4+:4]),.clk_meta(clk_meta[q*4+:4]),
   .clk_tail(clk_tail[q*4+:4]),.clk_chunk(clk_chunk[q*16+:16]),.clk_hslice(clk_hslice[q*512+:512]),.rst_n(rst_n),
   .rank(rank),.first_ord(11'(q*342)),.nkeys(nq),.keep_en(keep_en),.keep_bitmap(keep_bitmap[q*342+:342]),
   .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.beat_v(beat_v),.beat_index(beat_index),
   .key_lines(key_lines[q*8792+:8792]),.score(score),.fault(scf[q]));
  assign score_observe[q*610+:610]=score;
  for(genvar l=0;l<16;l=l+1)begin:lane
   assign sel_in[q*592+l*37+:37]={score[290+l*20+:20],score[34+l*16+:16],score[18+l]};
  end
 end
 wire[3:0]unused_ov;wire[2367:0]unused_ol;wire[15:0]threshold;wire[55:0]selected_count;
 ot_hbm_idx_selector_static selector(.clk_ctl(clk_sel),.clk_q(clk_sel_q),.clk_mem(clk_sel_mem),.rst_n(rst_n),.op(sel_op),.pass(sel_pass),
 .addr(sel_addr),.k(10'd512),.in_line(sel_in),.out_v(unused_ov),.out_line(unused_ol),.selected_v(selected_v),.selected_line(selected_line),
 .threshold_observe(threshold),.selected_observe(selected_count),.fault(sf));
 wire[9:0]total;
 ot_hbm_idx_topk_link_static link(.clk(clk_link),.clk_mem(clk_link_mem),.rst_n(rst_n),.clear(frame_start),.ingest_v(&selected_v),
 .selected_line(selected_line),.flush(link_flush),.emit_v(link_emit),.emit_group(link_group),.rank({1'b0,rank}),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(total));
 reg calendar_fault;
 always @(posedge clk_sel or negedge rst_n)begin
  if(!rst_n)calendar_fault<=0;
  else if(sel_op==2&&score_observe[0]!=1'b1)calendar_fault<=1;
 end
 assign fault=vf|qf|(|scf)|sf|lf|calendar_fault;
endmodule
`default_nettype wire
