`default_nettype none
// Source-bound full native functional graph. No physical/CLOSED aliases.
// Distinct scorer arithmetic has 512 leaves per stack. Endpoint landing,
// selector and ordered collection state remain real RTL, pending physical cuts.
// Clock pins are external owned entries; functional adapter uses common phase.
module ot_hbm_idx_parent_cut_native(
 input wire [3:0] clk_score,
 input wire [31:0] clk_line,
 input wire [95:0] clk_line_mem,
 input wire clk_query,clk_quant,clk_quant_delay,
 input wire [3:0] clk_query_bank,
 input wire clk_top,clk_top_ctl,
 input wire [3:0] clk_top_slice,
 input wire [7:0] clk_top_hist,clk_top_pack,
 input wire [1:0] clk_top_search,
 input wire [3:0] clk_score_fifo,
 input wire [11:0] clk_score_mem,clk_top_mem,
 input wire clk_selector,clk_ordered,
 input wire [15:0] clk_engine,clk_meta,clk_tail,
 input wire [63:0] clk_chunk,
 input wire [2047:0] clk_hslice,
 input wire rst_n,
 input wire [35167:0] ik,
 output wire [31:0] ikc,
 input wire [89:0] fs,
 input wire [1047:0] qb,
 output wire qbr,
 input wire [344:0] kin,
 output wire [611:0] to,
 input wire toc,
 output wire [71:0] co,
 input wire coc,
 output wire [1:0] ev,
 output wire co_quarter_last,
 output wire [2439:0] score_observe,
 output wire [15:0] status
);
 wire [2283:0] qo;
 wire [2439:0] si;
 wire [3:0] sc;
 wire [1:0] selector_ev;
 wire [89:0] topk_fs={fs[89],1'b0,fs[87:0]};
 for(genvar s=0;s<4;s=s+1) begin:gstack
  ot_hbm_idx_score_cut_native #(.L(16),.FA(6),.CRED(128),.FWD(0)) scorer(
   .ck(clk_score[s]),.clk_line(clk_line[s*8+:8]),.clk_line_mem(clk_line_mem[s*24+:24]),.rst(rst_n),
   .clk_engine(clk_engine[s*4+:4]),.clk_meta(clk_meta[s*4+:4]),
   .clk_tail(clk_tail[s*4+:4]),.clk_chunk(clk_chunk[s*16+:16]),
   .clk_hslice(clk_hslice[s*512+:512]),
   .ik(ik[s*8792+:8792]),.ikf(8'b0),.ikc(ikc[s*8+:8]),
   .q(qo[s*571+:571]),.qx(),.s(si[s*610+:610]),.sc(sc[s]),.st(status[s*4+:4]));
 end
 ot_hbm_idx_selector_cut_native #(.T(1),.LA(7),.MEMV(1),.READLAT(2),.EXPOSE_QUARTER_LAST(1)) selector(
  .ck(clk_selector),.clk_query(clk_query),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_query_bank(clk_query_bank),
  .clk_top(clk_top),.clk_top_ctl(clk_top_ctl),.clk_top_slice(clk_top_slice),.clk_top_hist(clk_top_hist),.clk_top_pack(clk_top_pack),.clk_top_search(clk_top_search),
  .clk_score_fifo(clk_score_fifo),.clk_score_mem(clk_score_mem),.clk_top_mem(clk_top_mem),.rst(rst_n),.fs(topk_fs),.qb(qb),.qbr(qbr),.kin(kin),
  .qo(qo),.si(si),.sc(sc),.to(to),.toc(toc),.co(),.coc(1'b0),
  .ev(selector_ev),.co_quarter_last());
 ot_hbm_idx_ordered_candidate collector(
  .ck(clk_ordered),.rst(rst_n),.fs(fs),.si(si),.selector_ev(selector_ev),
  .co(co),.coc(coc),.ev(ev),.co_quarter_last(co_quarter_last));
 assign score_observe=si;
endmodule
`default_nettype wire
