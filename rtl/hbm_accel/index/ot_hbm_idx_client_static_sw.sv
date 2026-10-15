`timescale 1ns/1ps
`default_nettype none
// SW-only source specialization: this die has slice ID zero.
// No runtime SID pin exists; synthesis specializes the real implementation.
// New master identity: historical dynamic-SID physical views do not qualify it.
module ot_hbm_idx_client_static_sw(
 input wire clk_program,clk_program_mem,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,
 input wire clk_operand,clk_query,clk_quant,clk_quant_delay,input wire[3:0]clk_query_bank,
 input wire[3:0]clk_score,input wire[15:0]clk_engine,clk_meta,clk_tail,
 input wire[63:0]clk_chunk,input wire[2047:0]clk_hslice,
 input wire clk_sel,input wire[3:0]clk_sel_q,input wire[11:0]clk_sel_mem,
 input wire clk_link,input wire[7:0]clk_link_mem,input wire[3:0]clk_pair,input wire clk_topk,input wire rst_n,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 input wire[6:0]rank,input wire[7:0]gbase,input wire[13:0]nkeys,input wire keep_en,input wire[1367:0]keep_bitmap,
 output wire key_slot,output wire[7:0]key_index,input wire[35167:0]key_lines,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire[2439:0]score_observe,output wire done,fault,
 input wire topk_go,input wire[3:0]topk_k,input wire topk_order,input wire[19:0]topk_n,topk_m,
 input wire topk_a_mirror,input wire[17:0]topk_a_base,topk_a_str,input wire topk_o_mirror,input wire[17:0]topk_o_base,topk_o_str,
 input wire topk_has_r,input wire[17:0]topk_r_base,topk_r_str,
 output wire[337:0]cq,output wire[1:0]cq_seq,input wire[273:0]cr,
 output wire topk_busy,topk_done,topk_fault,output wire share_fault,
 // third owner of the SW IDX read group: the static ARGMAX.LOCAL VM reader (ot_hbm_argmax_static, separate unit)
 input wire[135:0]argmax_rq,output wire[2055:0]argmax_rr
);
 localparam [1:0] SID = 2'd0;
 ot_hbm_idx_client_static implementation(.sid(SID), .*);
endmodule
`default_nettype wire
