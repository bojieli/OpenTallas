`default_nettype none
// Actual microprogram issuer joined to real native INDEX arithmetic and SRAM
// operand ports. Programload is explicit initialization; start executes exactly
// length instructions, never waits for data/credits/ready. key_slot/key_index
// describe the reserved staged-service delivery edge, not a PHY request.
module ot_hbm_idx_scheduled_static(
 input wire clk_program,clk_program_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[3:0]clk_score,input wire[15:0]clk_engine,clk_meta,clk_tail,
 input wire[63:0]clk_chunk,input wire[2047:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire rst_n,
 input wire[1:0]sid,input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire[6:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[1367:0]keep_bitmap,
 output wire key_slot,output wire[7:0]key_index,input wire[35167:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[2439:0]score_observe,output wire done,fault
);
 wire issue_v,calendar_fault,parent_fault;wire[31:0]ins;
 ot_hbm_idx_calendar_static calendar(.clk(clk_program),.clk_mem(clk_program_mem),.rst_n(rst_n),
 .program_we(program_we),.program_addr(program_addr),.program_data(program_data),.start(start),.length(length),
 .issue_v(issue_v),.instruction(ins),.done(done),.fault(calendar_fault));
 assign key_slot=issue_v&&ins[28];assign key_index=ins[27:20];
 ot_hbm_idx_parent_static parent(.clk_operand(clk_operand),.clk_query(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_query_bank(clk_query_bank),
 .clk_score(clk_score),.clk_engine(clk_engine),.clk_meta(clk_meta),.clk_tail(clk_tail),.clk_chunk(clk_chunk),.clk_hslice(clk_hslice),
 .clk_sel(clk_sel),.clk_sel_q(clk_sel_q),.clk_sel_mem(clk_sel_mem),.clk_link(clk_link),.clk_link_mem(clk_link_mem),.rst_n(rst_n),.sid(sid),.frame_start(start),
 .weight_slot(issue_v&&ins[31]),.query_slot(issue_v&&ins[30]),.query_index(ins[26:20]),.weight_sector(weight_sector),.query_sector(query_sector),
 .vm_rq(vm_rq),.vm_rr(vm_rr),.query_emit(issue_v&&ins[29]),.query_emit_head(ins[24:20]),.rank(rank),.gbase(gbase),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),
 .beat_v(key_slot),.beat_index(key_index),.key_lines(key_lines),.sel_op(issue_v?ins[19:16]:4'd0),.sel_pass(ins[15:14]),.sel_addr(ins[13:6]),
 .link_flush(issue_v&&ins[5]),.link_emit(issue_v&&ins[4]),.link_group(ins[3:0]),.tx_v(tx_v),.tx(tx),.score_observe(score_observe),.fault(parent_fault));
 assign fault=calendar_fault|parent_fault;
endmodule
`default_nettype wire
