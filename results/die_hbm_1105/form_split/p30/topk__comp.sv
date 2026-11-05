// HBM-FORM-SPLIT d44v part 30: plan form of the topk composition, same ports as ot_hbm_idx_topk_link_static.
`default_nettype none
module ot_hbm_idx_topk__comp #(parameter integer MUT = 0) (
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output wire[3:0]tx_v,output wire[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
    wire [7:0] we; wire [47:0] wa; wire [4095:0] wd;
    ot_hbm_idx_topk_ingest__fs u_ing (.clk(clk), .rst_n(rst_n), .clear(clear), .ingest_v(ingest_v), .selected_line(selected_line), .flush(flush), .emit_v(emit_v), .rank(rank), .gbase(gbase),
        .fault(fault), .selected_count(selected_count), .wo_we(we), .wo_wa(wa), .wo_wd(wd));
    ot_hbm_idx_topk_store__fs u_sto (.clk(clk), .clk_mem(clk_mem), .rst_n(rst_n), .clear(clear), .emit_v(emit_v), .emit_group(emit_group), .rank(rank), .gbase(MUT == 4 ? rank : gbase),
        .wi_we(we), .wi_wa(MUT == 2 ? {wa[41:0], wa[47:42]} : wa), .wi_wd(MUT == 3 ? {wd[3583:0], wd[4095:3584]} : wd), .tx_v(tx_v), .tx(tx));
endmodule
`default_nettype wire
