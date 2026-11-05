// HBM-FORM-SPLIT d44v part 30: plan module ot_hbm_idx_topk_link_static = thin parent glue of the split hard core (wires only).
`default_nettype none
module ot_hbm_idx_topk_link_static__fcore (
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
    ot_hbm_idx_topk__comp u_core (.clk(clk),.clk_mem(clk_mem),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(rank),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(fault),.selected_count(selected_count));
endmodule
module ot_hbm_idx_topk_link_static (
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
    ot_hbm_idx_topk_link_static__fcore u_fcore (.clk(clk),.clk_mem(clk_mem),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),.selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(rank),.gbase(gbase),.tx_v(tx_v),.tx(tx),.fault(fault),.selected_count(selected_count));
endmodule
`default_nettype wire
