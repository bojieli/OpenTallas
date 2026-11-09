// HBM-REFORM-B10 (2026-11-05): ev74_tall slot form of ot_hbm_idx_topk_link_static as ONE core: the part 30 PD=3 ingest and
// store tiles (ot_hbm_idx_topk_tiles.sv) composed as the part 30 lock-step composes their face-shell models
// (results/die_hbm_1105/form_split/p30/run_p30_pd3.sh, topk__comp.sv). The kit face shell of this core gives the +1 in / +1 out
// that each tile shell gave at the plan pins; inside, the SRAM write seam keeps both tile face stages (ingest out, store in).
// The compact tree is registered at subtree sizes 8/32/64 (PD = 3). Same ports as ot_hbm_idx_topk_link_static; in the kit,
// every output is the WRITE_PIPE_STAGES=2 form delayed 3 edges (tx_v / tx / fault / selected_count +3, SS38 price -0.004%).
// The seam stage registers carry no reset (as the face shells they replace). MUT 1-4: bench mutants (as topk__comp.sv).
// HBM-FORM-SPLIT-13-TOPK WPIPE=1: ingest write stage + store PD+1, tx_v/tx +1 edge (outputs +4 vs WRITE_PIPE_STAGES=2;
// fault/selected_count stay +3). MUT 5/6: ingest write-stage mutants; MUT 9: store left at PD=3 (must FAIL).
// HBM-HARD-6-TOPK NQ=1 (11-08): ingest n = fill + count registered one edge early (same ports, same cycles); MUT 10/11 its mutants.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_idx_topk_link_pd3 #(parameter integer MUT = 0, FILL_GROUPS = 0, WPIPE = 0, NQ = 0) (
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
 wire[7:0]c_we;wire[47:0]c_wa;wire[4095:0]c_wd;
 ot_hbm_idx_topk_ingest #(.MUT((MUT==5||MUT==6||MUT==10||MUT==11)?MUT:0),.FILL_GROUPS(FILL_GROUPS),.WPIPE(WPIPE),.NQ(NQ)) u_ing(.clk(clk),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(selected_line),
  .flush(flush),.emit_v(emit_v),.rank(rank),.gbase(gbase),
  .fault(fault),.selected_count(selected_count),.wo_we(c_we),.wo_wa(c_wa),.wo_wd(c_wd));
 // write seam: ingest output stage, then store input stage (the two part 30 tile face stages)
 reg[7:0]o_we,s_we;reg[47:0]o_wa,s_wa;reg[4095:0]o_wd,s_wd;
 always @(posedge clk)begin o_we<=c_we;o_wa<=c_wa;o_wd<=c_wd;s_we<=o_we;s_wa<=o_wa;s_wd<=o_wd;end
 ot_hbm_idx_topk_store #(.MUT(MUT==1?1:0),.WPIPE(MUT==9?0:WPIPE)) u_sto(.clk(clk),.clk_mem(clk_mem),.rst_n(rst_n),.clear(clear),.emit_v(emit_v),
  .emit_group(emit_group),.rank(rank),.gbase(MUT==4?rank:gbase),
  .wi_we(s_we),.wi_wa(MUT==2?{s_wa[41:0],s_wa[47:42]}:s_wa),.wi_wd(MUT==3?{s_wd[3583:0],s_wd[4095:3584]}:s_wd),
  .tx_v(tx_v),.tx(tx));
endmodule
`default_nettype wire
