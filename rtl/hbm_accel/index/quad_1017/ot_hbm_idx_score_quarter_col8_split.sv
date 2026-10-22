// Candidate +23 chunk-seam ages; remaining quarter-level crossings OPEN.
`default_nettype none
// HBM d4g plan (b) IDX QUARTER SCORER (lane HBM-B-RTL2, 2026-10-17). One master, one instance per quadrant
// (idx_s<q>), 8 leaves: half of the IDX-SCORE chained cluster ot_hbm_idx_score_cluster (4 rows x 4 leaves of the closed
// leaf ot_hbm_idx_score_leaf, kit hidx_score_leaf_1017). Quarter `half` of stack scorer slot s owns cluster rows
// (engines) 2*half, 2*half+1 = key lanes 8*half .. 8*half+7 = key lines (HBM service groups / PCs) 4*half .. 4*half+3
// of that stack: the keys are sharded by the quadrant's own PCs. Rows, leaves, W/E glue, tail, meta delays and the W
// fault cause are those rows of ot_hbm_idx_score_cluster verbatim (row index e -> global engine 2*half + e), so the two
// quarters of a stack are bit-identical to the stack cluster.
// Layout: 2 rows x 4 leaves (561.6 um square each) = 1.12 x 2.25 mm leaf array + W glue column + E glue column.
// PINS (owner rule 10-15): every data input lands in a kept pin flop (no reset) and the score leaves a flop: +1 edge
// on the inputs (query and key beats alike: the leaves' relative timeline is unchanged) and +1 on score, on top of the
// cluster's +8 seam chain (compiler --score-chain counts 8 + 2 + XQ tree).
// RESET: rst_n drives only ot_rst_relay (2 sync + 1 relay, release +3 edges) which resets the leaves, E glue and fault.
// STATIC: no ready/credit; tags/ranges/engine agreement are fault checks only. half is a die strap.
// Output score (306 b) = {idx[8x20], val[8x16], kv[8], fl[8], last, ev} (the 610-b stack format restricted to 8 lanes).
module ot_hbm_idx_score_quarter_col8_split #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_ctl,input wire[1:0]clk_engine,clk_meta,clk_tail,
 input wire[7:0]clk_chunk,input wire[255:0]clk_hslice,input wire rst_n,
 input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,          // stack bitmap bit 2*beat+half (this quarter's lanes)
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[4395:0]key_lines,   // stack key lines 4*half .. 4*half+3
 output wire[305:0]score,output wire fault
);
 wire [31:0] cut_rst_n;
 wire [31:0] cut_qv;
 wire [18175:0] cut_q;
 wire [17407:0] cut_key;
 wire [2047:0] cut_hid;
 wire [1023:0] cut_cs;
 wire [31:0] cut_cf;
 wire [127:0] cut_prdy;
 ot_hbm_idx_score_quarter_col8_control #(.TP(TP),.RANK_W(RANK_W)) u_control(.clk_ctl(clk_ctl),.clk_engine(clk_engine),.clk_meta(clk_meta),.clk_tail(clk_tail),.clk_chunk(clk_chunk),.clk_hslice(clk_hslice),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines(key_lines),.score(score),.fault(fault),.cut_rst_n(cut_rst_n),.cut_qv(cut_qv),.cut_q(cut_q),.cut_key(cut_key),.cut_hid(cut_hid),.cut_cs(cut_cs),.cut_cf(cut_cf),.cut_prdy(cut_prdy));
 for(genvar e=0;e<2;e=e+1)begin:ge
  for(genvar c=0;c<4;c=c+1)begin:gc
   for(genvar g=0;g<4;g=g+1)begin:g_col
    localparam integer I=(e*4+c)*4+g;
    wire[3:0]cp;
    for(genvar rid=0;rid<4;rid=rid+1)begin:gp
     assign cp[rid]=clk_hslice[e*128+c*32+g*8+rid*2];
    end
    ot_hidx_col8_sram_face_col u_col(.ctl(clk_chunk[e*4+c]),.cp(cp),.rst_n(cut_rst_n[I]),.qv_b(cut_qv[I]),.q_b(cut_q[I*568+:568]),.key(cut_key[I*544+:544]),.hid(cut_hid[I*64+:64]),.cs_out(cut_cs[I*32+:32]),.cf_out(cut_cf[I]),.prdy(cut_prdy[I*4+:4]));
   end
  end
 end
endmodule
`default_nettype wire
