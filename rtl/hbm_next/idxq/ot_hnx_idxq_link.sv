`default_nettype none
// HBM-NEXT-UNITS IDXQ 2026-10-19: IDXN row-slot link tile for the quad composition (die slot idx_link). The S
// time-shared selectors deliver into ONE link: this tile takes the S selector outputs, merges them (the static
// schedule gives the link ONE delivering selector per edge: OR of one; two on one edge = collision = fault, as in
// ot_hnx_idxn_parent) and feeds the IDXN row-slot link ot_hnx_idxn_link (pin-registered shell, unchanged). The merge is
// the glue the IDXN parent held; in the quad form it lives in the link tile (owner rule: glue into tiles).
module ot_hnx_idxq_link #(parameter integer S=4)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,row_clear,input wire[2:0]in_slot,
 input wire[4*S-1:0]selected_v,input wire[2368*S-1:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[2:0]emit_slot,input wire[7:0]rank,gbase,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
 reg[2367:0]line;reg ingest;reg coll;integer nsel;
 always @*begin
  line=0;ingest=0;nsel=0;
  for(integer s=0;s<S;s=s+1)if(|selected_v[s*4+:4])begin
   nsel=nsel+1;line=line|selected_line[s*2368+:2368];ingest=ingest|(&selected_v[s*4+:4]);
  end
  coll=nsel>1;
 end
 reg coll_fault;
 always @(posedge clk or negedge rst_n)if(!rst_n)coll_fault<=0;else if(coll)coll_fault<=1;
 wire lf;
 ot_hnx_idxn_link link(.clk(clk),.clk_mem(clk_mem),.rst_n(rst_n),.clear(clear),.row_clear(row_clear),.in_slot(in_slot),
  .ingest_v(ingest),.selected_line(line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.emit_slot(emit_slot),
  .rank(rank),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(lf),.selected_count(selected_count));
 assign fault=lf|coll_fault;
endmodule
`default_nettype wire
