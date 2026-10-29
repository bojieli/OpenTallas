`default_nettype none
// Opt-in four-slice replay-buffer quarter. The scorer, reset delivery and every
// sampled data/control edge are unchanged. Four active keybuf.gp[p].u_line
// hard children replace the 17 packed SRAMs with 20 line-local SRAMs.
// Select this distinct module explicitly; the packed quarter remains unchanged.
module ot_hnx_idxn_quarter_with_keybuf_sliced #(
 parameter integer TP=192,RANK_W=(TP<=1?1:$clog2(TP)),DELIVERED_RESET=0
)(
 input wire clk,rst_n,half,
 input wire clear,live_v,pre_v,replay_v,
 input wire[7:0]live_index,pre_index,replay_index,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,
 input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[4395:0]key_lines,
 output wire[305:0]score,output wire fault
);
 wire[4395:0]replayed_key_lines;wire keybuf_fault,scorer_fault;
 ot_hnx_idxn_keybuf_sliced_np4 #(.NP(4),.RS(0)) keybuf(.clk(clk),.rst_n(rst_n),.clear(clear),.pbase({half,2'b00}),
  .live_v(live_v),.live_index(live_index),.key_in(key_lines),
  .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
  .key_out(replayed_key_lines),.fault(keybuf_fault));
 ot_hbm_idx_score_quarter_static_h #(.TP(TP),.DELIVERED_RESET(DELIVERED_RESET)) scorer(
  .clk_ctl(clk),.clk_engine({2{clk}}),.clk_meta({2{clk}}),.clk_tail({2{clk}}),
  .clk_chunk({8{clk}}),.clk_hslice({256{clk}}),.rst_n(rst_n),.half(half),
  .rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),
  .ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
  .beat_v(beat_v),.beat_index(beat_index),.key_lines(replayed_key_lines),.score(score),.fault(scorer_fault));
 assign fault=keybuf_fault|scorer_fault;
endmodule
`default_nettype wire
