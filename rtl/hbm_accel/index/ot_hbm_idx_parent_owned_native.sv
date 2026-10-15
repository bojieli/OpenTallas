`default_nettype none
// Source-bound full native functional graph. No physical/CLOSED aliases.
// Distinct scorer arithmetic has 512 leaves per stack. Endpoint landing,
// selector and ordered collection state remain real RTL, pending physical cuts.
// Clock pins are external owned entries; functional adapter uses common phase.
module ot_hbm_idx_parent_owned_native(
 input wire [3:0] clk_score,
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
  ot_hbm_idx_score_owned_native #(.L(16),.FA(6),.CRED(128),.FWD(0)) scorer(
   .ck(clk_score[s]),.rst(rst_n),
   .clk_engine(clk_engine[s*4+:4]),.clk_meta(clk_meta[s*4+:4]),
   .clk_tail(clk_tail[s*4+:4]),.clk_chunk(clk_chunk[s*16+:16]),
   .clk_hslice(clk_hslice[s*512+:512]),
   .ik(ik[s*8792+:8792]),.ikf(8'b0),.ikc(ikc[s*8+:8]),
   .q(qo[s*571+:571]),.qx(),.s(si[s*610+:610]),.sc(sc[s]),.st(status[s*4+:4]));
 end
 hfd_idx_sel_native_qend selector(
  .ck(clk_selector),.rst(rst_n),.fs(topk_fs),.qb(qb),.qbr(qbr),.kin(kin),
  .qo(qo),.si(si),.sc(sc),.to(to),.toc(toc),.co(),.coc(1'b0),
  .ev(selector_ev),.co_quarter_last());
 ot_hbm_idx_ordered_candidate collector(
  .ck(clk_ordered),.rst(rst_n),.fs(fs),.si(si),.selector_ev(selector_ev),
  .co(co),.coc(coc),.ev(ev),.co_quarter_last(co_quarter_last));
 assign score_observe=si;
endmodule
`default_nettype wire
